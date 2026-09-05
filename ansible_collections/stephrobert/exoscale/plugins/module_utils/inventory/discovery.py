# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""L'orchestration : construire les index, lancer les providers, agréger.

C'est la seule couche qui importe le SDK. Les providers reçoivent une fabrique
de clients, la jointure reçoit des enregistrements normalisés, et le plugin
reçoit un résultat. Chacune se teste donc sans les autres.

**Un client par zone.** L'hôte de l'API porte la zone
(`api-{zone}.exoscale.com`) : il n'existe pas d'appel qui parle de tout le
compte, et un client construit avec `url=` (un émulateur) ne parle qu'à une
zone. La fabrique rend le même client pour chaque zone dans ce cas, et c'est
dit.

L'index réseau est construit **une fois par zone**, avant les providers, et
partagé par tous. Il coûte une liste par zone plus une lecture par réseau :
c'est le contrat qui l'impose, les baux ne sont que sur le réseau.
"""

from __future__ import annotations

import traceback
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .errors import AuthenticationFailed, PermissionDenied, ProductUnavailable, classify
from .models import ProviderResult
from .network import Lease, NetworkIndex, PrivateNetworkInfo, build_index
from .providers.base import ClientFactory, DiscoveryContext
from .providers.instance import InstanceProvider

try:
    from exoscale.api.v2 import Client

    SDK_IMPORT_ERROR: str | None = None
    HAS_SDK = True
except ImportError:
    SDK_IMPORT_ERROR = traceback.format_exc()
    HAS_SDK = False

#: Les providers de hosts que cette version connaît. `products: all` désigne
#: cette table, et non toutes les APIs Exoscale existantes.
HOST_PROVIDERS: tuple[str, ...] = ("instance",)


@dataclass
class DiscoveryReport:
    """Ce que la découverte a fait, pour le mode debug et le rapport d'échec."""

    api_calls: int = 0
    providers: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    leases: int = 0

    def lines(self) -> list[str]:
        resume = ", ".join(f"{nom}={compte}" for nom, compte in sorted(self.providers.items()))
        return [
            f"appels d'API : {self.api_calls}",
            f"baux de réseaux privés indexés : {self.leases}",
            f"hosts par provider : {resume or 'aucun'}",
            *(f"avertissement : {texte}" for texte in self.warnings),
            *(f"erreur : {texte}" for texte in self.errors),
        ]


def client_factory(api_key: str, api_secret: str, api_url: str | None = None) -> ClientFactory:
    """Une fabrique de clients, un par zone, ou un seul quand l'URL est imposée.

    `EXOSCALE_API_URL` reste honoré de bout en bout : avec une URL, toutes les
    zones parlent au même hôte, ce qui est ce qu'un émulateur attend.
    """
    if not HAS_SDK:
        raise ImportError(SDK_IMPORT_ERROR or "le SDK exoscale n'est pas installé")
    clients: dict[str, Any] = {}

    def for_zone(zone: str) -> Any:
        if zone not in clients:
            if api_url:
                clients[zone] = Client(api_key, api_secret, url=api_url)
            else:
                clients[zone] = Client(api_key, api_secret, zone=zone)
        return clients[zone]

    return for_zone


def build_network_index(
    client_for: ClientFactory,
    zones: tuple[str, ...],
    report: DiscoveryReport | None = None,
) -> dict[str, NetworkIndex]:
    """Liste les réseaux privés de chaque zone, lit leurs baux, puis indexe.

    Une zone qui refuse l'accès aux réseaux n'est pas une panne : c'est un
    enrichissement qui n'aura pas lieu, et le rapport le dit. Un jeton sans
    droit sur les réseaux peut parfaitement construire un inventaire de
    machines publiques.
    """
    index: dict[str, NetworkIndex] = {}

    def collecte(label: str, zone: str, appel: Any) -> Any | None:
        if report is not None:
            report.api_calls += 1
        try:
            return appel()
        except Exception as erreur:
            categorie = classify(erreur)
            if categorie is AuthenticationFailed:
                raise AuthenticationFailed(str(erreur)) from erreur
            if report is None:
                return None
            if categorie in (ProductUnavailable, PermissionDenied):
                report.warnings.append(
                    f"enrichissement réseau indisponible dans {zone} ({label}) : "
                    f"{categorie.__name__}"
                )
            else:
                report.errors.append(f"{categorie.__name__} sur {label} dans {zone} : {erreur}")
            return None

    for zone in zones:
        client = client_for(zone)
        reseaux: list[PrivateNetworkInfo] = []
        baux: list[Lease] = []

        reponse = collecte("private-networks", zone, client.list_private_networks)
        trouves = reponse.get("private-networks") if isinstance(reponse, dict) else reponse
        for reseau in trouves or ():
            if not isinstance(reseau, dict) or not reseau.get("id"):
                continue
            reseau_id = str(reseau["id"])
            reseaux.append(PrivateNetworkInfo(id=reseau_id, name=reseau.get("name")))
            # Les baux ne sont pas promis dans la liste : `leases` est readOnly
            # sur le schéma, et seule la lecture unitaire les porte à coup sûr.
            detail = reseau if reseau.get("leases") else None
            if detail is None:
                detail = collecte(
                    "private-network",
                    zone,
                    lambda rid=reseau_id: client.get_private_network(id=rid),
                )
            for bail in (detail or {}).get("leases") or ():
                if not isinstance(bail, dict):
                    continue
                baux.append(
                    Lease(
                        private_network_id=reseau_id,
                        host_id=str(bail.get("instance-id") or ""),
                        address=str(bail.get("ip") or ""),
                    )
                )

        index[zone] = build_index(tuple(baux), tuple(reseaux))
        if report is not None:
            report.leases += index[zone].lease_count
    return index


def providers_for(client_for: ClientFactory, products: tuple[str, ...]) -> tuple[Any, ...]:
    """Instancie les providers demandés, et refuse un produit inconnu.

    Ajouter un produit, c'est ajouter une ligne ici et un fichier de provider.
    Aucune autre couche ne connaît le nom d'un produit.
    """
    inconnus = sorted(set(products) - set(HOST_PROVIDERS))
    if inconnus:
        raise ValueError(f"produit(s) inconnu(s) : {inconnus}. Connus : {list(HOST_PROVIDERS)}")
    fabriques = {"instance": lambda: InstanceProvider(client_for)}
    return tuple(fabriques[nom]() for nom in products)


#: Ce que chaque provider déclare de lui-même, lu une fois pour éviter de les
#: instancier avant d'avoir un client.
CAPACITES: Mapping[str, bool] = {"instance": InstanceProvider.joins_private_networks}


def needs_network_index(products: tuple[str, ...]) -> bool:
    """Faut-il payer l'index réseau pour les produits demandés ?

    La question est posée aux providers : le cœur ne connaît aucun produit,
    et trancher ici ramènerait la connaissance qu'on vient d'en sortir.
    """
    return any(CAPACITES.get(nom, False) for nom in products)


def discover(
    client_for: ClientFactory,
    context: DiscoveryContext,
    products: tuple[str, ...],
    strict: bool = True,
) -> tuple[ProviderResult, DiscoveryReport]:
    """Lance les providers et agrège leurs résultats.

    En mode strict, l'échec d'un provider fait échouer l'inventaire. Sinon il
    devient un avertissement, et le rapport nomme le provider fautif. Dans les
    deux cas, l'échec est **dit**.
    """
    resultat = ProviderResult()
    report = DiscoveryReport()

    for provider in providers_for(client_for, products):
        try:
            partiel = provider.discover(context)
        except AuthenticationFailed:
            raise
        except Exception as erreur:
            message = f"{provider.name} : {erreur}"
            if strict:
                raise
            report.errors.append(message)
            continue

        resultat = resultat.merge(partiel)
        report.api_calls += partiel.api_calls
        report.providers[provider.name] = len(partiel.hosts)
        report.warnings.extend(partiel.warnings)
        report.errors.extend(partiel.errors)

    return resultat, report
