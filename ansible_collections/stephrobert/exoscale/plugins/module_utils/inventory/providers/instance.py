# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Le provider Instance.

Il traduit ce que `list-instances` rend en `InventoryHost`, et rien d'autre.
Il ne connaît ni Ansible, ni le cache, ni les groupes, et il n'importe pas le
SDK : il reçoit une fabrique de clients, ce qui permet de le tester avec des
réponses figées.

**Ce qu'il lit, il le lit dans le contrat.** Les clés ci-dessous sont celles
du schéma `instance` du contrat versionné, en kebab-case, et un test les y
confronte : un champ renommé en amont fait rougir la CI plutôt que rendre un
parc muet. Le SDK rend des dictionnaires, pas des objets, donc tout se lit
par `.get`.
"""

from __future__ import annotations

from typing import Any

from ..errors import AuthenticationFailed, ProductUnavailable, classify
from ..models import InventoryHost, ProviderResult
from ..network import attach, flatten
from .base import EXOSCALE_ZONES, ClientFactory, DiscoveryContext

#: Mesurées sur le contrat.
ZONES: tuple[str, ...] = EXOSCALE_ZONES

#: Ce qui n'appartient qu'à Instance, exposé sous son propre préfixe plutôt
#: que versé dans l'espace global des hostvars. Chaque entrée : le nom de la
#: variable, et la clé du contrat qui la porte.
METADATA_FIELDS: tuple[tuple[str, str], ...] = (
    ("type", "instance-type"),
    ("template", "template"),
    ("ssh_key", "ssh-key"),
    ("disk_size", "disk-size"),
    ("created_at", "created-at"),
    ("mac_address", "mac-address"),
)


def _reference(value: Any) -> str | None:
    """Une référence du contrat (`{id, name}`) rendue par son nom, sinon son id."""
    if not isinstance(value, dict):
        return None
    return value.get("name") or value.get("id") or None


def _type_name(value: Any) -> str | None:
    """`instance-type` rend `{family, size}` : `standard.medium` est le nom qu'un
    opérateur reconnaît, et le contrat ne porte pas de champ `name`."""
    if not isinstance(value, dict):
        return None
    family, size = value.get("family"), value.get("size")
    if family and size:
        return f"{family}.{size}"
    return value.get("id") or None


def normalize(instance: dict[str, Any], zone: str, context: DiscoveryContext) -> InventoryHost:
    """Traduit une instance en modèle normalisé."""
    network_ids = tuple(
        str(reseau["id"])
        for reseau in instance.get("private-networks") or ()
        if isinstance(reseau, dict) and reseau.get("id")
    )
    index = (context.network or {}).get(zone)
    rattachements = attach(str(instance["id"]), network_ids, index) if index is not None else ()
    prive_v4, prive_v6 = flatten(rattachements)

    manager = instance.get("manager") or {}
    metadata: dict[str, Any] = {}
    for variable, cle in METADATA_FIELDS:
        valeur = instance.get(cle)
        if valeur is None:
            continue
        if cle == "instance-type":
            metadata[variable] = _type_name(valeur)
        elif isinstance(valeur, dict):
            metadata[variable] = _reference(valeur)
        else:
            metadata[variable] = valeur

    return InventoryHost(
        id=str(instance["id"]),
        product="instance",
        name=instance.get("name") or None,
        zone=zone,
        state=instance.get("state") or None,
        labels=dict(instance.get("labels") or {}),
        public_ipv4=tuple(str(ip) for ip in (instance.get("public-ip"),) if ip),
        public_ipv6=tuple(str(ip) for ip in (instance.get("ipv6-address"),) if ip),
        private_ipv4=prive_v4,
        private_ipv6=prive_v6,
        private_networks=rattachements,
        manager_type=manager.get("type") if isinstance(manager, dict) else None,
        manager_id=manager.get("id") if isinstance(manager, dict) else None,
        metadata=metadata,
        raw=instance if context.include_raw else None,
    )


class InstanceProvider:
    """Découvre les instances des zones demandées."""

    name = "instance"

    #: Instance porte `private-networks`, que les baux complètent.
    joins_private_networks = True

    def __init__(self, client_for: ClientFactory) -> None:
        self._client_for = client_for

    def discover(self, context: DiscoveryContext) -> ProviderResult:
        """Une liste par zone. Un client par zone, parce que l'hôte de l'API
        porte la zone : il n'existe pas d'appel qui liste tout le compte."""
        hosts: list[InventoryHost] = []
        avertissements: list[str] = []
        erreurs: list[str] = []
        appels = 0

        for zone in context.scoped_zones(ZONES):
            client = self._client_for(zone)
            kwargs: dict[str, Any] = {}
            if context.api_labels:
                kwargs["labels"] = dict(context.api_labels)
            try:
                appels += 1
                reponse = client.list_instances(**kwargs)
            except Exception as erreur:
                categorie = classify(erreur)
                if categorie is AuthenticationFailed:
                    # Fatal partout : aucune zone ne peut aboutir. Continuer
                    # produirait un inventaire vide qui se présente comme complet.
                    raise AuthenticationFailed(str(erreur)) from erreur
                if categorie is ProductUnavailable:
                    avertissements.append(f"{self.name} n'est pas servi dans {zone}")
                else:
                    erreurs.append(f"{categorie.__name__} : {self.name} {zone} : {erreur}")
                continue

            trouves = reponse.get("instances") if isinstance(reponse, dict) else reponse
            hosts.extend(normalize(instance, zone, context) for instance in trouves or ())

        # Trié par identifiant : l'ordre décide de la désambiguïsation des noms,
        # donc il doit être le même d'une exécution à l'autre.
        return ProviderResult(
            hosts=tuple(sorted(hosts, key=lambda h: h.id)),
            warnings=tuple(avertissements),
            errors=tuple(erreurs),
            api_calls=appels,
        )
