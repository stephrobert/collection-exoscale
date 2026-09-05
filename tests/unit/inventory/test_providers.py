"""Le provider Instance traduit sans deviner, et le cœur ne connaît aucun produit.

Trois preuves ici, et les deux dernières sont structurelles :

* la normalisation d'une instance telle que le contrat la décrit ;
* les champs que le provider lit existent dans le schéma `instance` du
  contrat versionné, lus dans le code par AST plutôt que recopiés à côté ;
* aucune couche du cœur ne nomme un produit dans son code.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

import pytest

from ansible_collections.stephrobert.exoscale.plugins.module_utils.inventory import (
    address,
    filtering,
    groups,
    hostname,
)
from ansible_collections.stephrobert.exoscale.plugins.module_utils.inventory.errors import (
    AuthenticationFailed,
)
from ansible_collections.stephrobert.exoscale.plugins.module_utils.inventory.network import (
    Lease,
    PrivateNetworkInfo,
    build_index,
)
from ansible_collections.stephrobert.exoscale.plugins.module_utils.inventory.providers import (
    instance,
)
from ansible_collections.stephrobert.exoscale.plugins.module_utils.inventory.providers.base import (
    EXOSCALE_ZONES,
    DiscoveryContext,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRAT = REPO_ROOT / "specs" / "exoscale" / "exoscale.v2.json"
INVENTAIRE = (
    REPO_ROOT
    / "ansible_collections"
    / "stephrobert"
    / "exoscale"
    / "plugins"
    / "module_utils"
    / "inventory"
)


def _instance(**extra: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "i-1",
        "name": "web01",
        "state": "running",
        "labels": {"env": "prod"},
        "public-ip": "185.0.0.1",
        "ipv6-address": "2001:db8::1",
        "private-networks": [{"id": "pn-1"}],
        "instance-type": {"id": "t-1", "family": "standard", "size": "medium"},
        "template": {"id": "tpl-1", "name": "Ubuntu 24.04"},
        "manager": {"type": "instance-pool", "id": "pool-1"},
        "created-at": "2026-09-04T10:00:00Z",
    }
    base.update(extra)
    return base


UNE_ZONE = DiscoveryContext(zones=("ch-gva-2",))


def test_instance_normalise_ce_que_lapi_rend() -> None:
    host = instance.normalize(_instance(), "ch-gva-2", UNE_ZONE)
    assert (host.id, host.product, host.name, host.zone, host.state) == (
        "i-1",
        "instance",
        "web01",
        "ch-gva-2",
        "running",
    )
    assert host.public_ipv4 == ("185.0.0.1",) and host.public_ipv6 == ("2001:db8::1",)
    assert dict(host.labels) == {"env": "prod"} and host.tags == ("env=prod",)
    assert (host.manager_type, host.manager_id) == ("instance-pool", "pool-1")
    assert host.metadata["type"] == "standard.medium"
    assert host.metadata["template"] == "Ubuntu 24.04"
    assert host.raw is None


def test_instance_joint_ses_reseaux_par_les_baux() -> None:
    index = build_index(
        (Lease("pn-1", "i-1", "10.0.0.5"),), (PrivateNetworkInfo(id="pn-1", name="backend"),)
    )
    contexte = DiscoveryContext(zones=("ch-gva-2",), network={"ch-gva-2": index})
    host = instance.normalize(_instance(), "ch-gva-2", contexte)
    assert host.private_ipv4 == ("10.0.0.5",)
    assert host.private_networks[0].private_network_name == "backend"


def test_une_instance_sans_adresse_publique_reste_un_host() -> None:
    host = instance.normalize(
        _instance(**{"public-ip": None, "ipv6-address": None}), "ch-gva-2", UNE_ZONE
    )
    assert host.public_ipv4 == () and host.public_ipv6 == ()


def test_la_reponse_brute_nest_gardee_que_si_on_la_demande() -> None:
    contexte = DiscoveryContext(zones=("ch-gva-2",), include_raw=True)
    assert instance.normalize(_instance(), "ch-gva-2", contexte).raw == _instance()


class _Client:
    def __init__(
        self, zone: str, reponses: dict[str, Any], erreur: Exception | None = None
    ) -> None:
        self.zone = zone
        self.reponses = reponses
        self.erreur = erreur
        self.appels: list[dict[str, Any]] = []

    def list_instances(self, **kwargs: Any) -> dict[str, Any]:
        self.appels.append(kwargs)
        if self.erreur is not None:
            raise self.erreur
        return {"instances": self.reponses.get(self.zone, [])}


def test_instance_interroge_une_zone_par_client_et_trie_par_identifiant() -> None:
    clients: dict[str, _Client] = {}
    reponses = {
        "ch-gva-2": [_instance(id="i-2"), _instance(id="i-1")],
        "de-fra-1": [_instance(id="i-3")],
    }

    def fabrique(zone: str) -> _Client:
        return clients.setdefault(zone, _Client(zone, reponses))

    provider = instance.InstanceProvider(fabrique)
    resultat = provider.discover(DiscoveryContext(zones=("ch-gva-2", "de-fra-1")))
    assert [h.id for h in resultat.hosts] == ["i-1", "i-2", "i-3"]
    assert [h.zone for h in resultat.hosts] == ["ch-gva-2", "ch-gva-2", "de-fra-1"]
    assert resultat.api_calls == 2


def test_instance_interroge_les_huit_zones_par_defaut() -> None:
    zones: list[str] = []
    provider = instance.InstanceProvider(lambda zone: zones.append(zone) or _Client(zone, {}))
    provider.discover(DiscoveryContext())
    assert tuple(zones) == EXOSCALE_ZONES


def test_instance_passe_le_filtre_de_label_que_lapi_sait_appliquer() -> None:
    client = _Client("ch-gva-2", {})
    instance.InstanceProvider(lambda zone: client).discover(
        DiscoveryContext(zones=("ch-gva-2",), api_labels={"env": "prod"})
    )
    assert client.appels == [{"labels": {"env": "prod"}}]


def test_un_refus_dauthentification_est_fatal() -> None:
    class ExoscaleAPIAuthException(Exception):
        pass

    client = _Client("ch-gva-2", {}, erreur=ExoscaleAPIAuthException("forbidden"))
    with pytest.raises(AuthenticationFailed):
        instance.InstanceProvider(lambda zone: client).discover(
            DiscoveryContext(zones=("ch-gva-2",))
        )


def test_une_panne_dune_zone_est_une_erreur_pas_un_silence() -> None:
    client = _Client("ch-gva-2", {}, erreur=ConnectionError("boom"))
    resultat = instance.InstanceProvider(lambda zone: client).discover(
        DiscoveryContext(zones=("ch-gva-2",))
    )
    assert resultat.hosts == () and len(resultat.errors) == 1


# ---- les preuves structurelles ---------------------------------------------


def test_les_zones_du_provider_sont_celles_du_contrat() -> None:
    """Une zone ajoutée en amont fait rougir la CI plutôt que manquer en silence."""
    document = json.loads(CONTRAT.read_text(encoding="utf-8"))
    assert tuple(document["servers"][0]["variables"]["zone"]["enum"]) == EXOSCALE_ZONES


def _cles_lues(chemin: Path) -> set[str]:
    """Les chaînes en kebab-case que le provider passe à `.get` ou lit par index."""
    arbre = ast.parse(chemin.read_text(encoding="utf-8"))
    cles: set[str] = set()
    for noeud in ast.walk(arbre):
        if (
            isinstance(noeud, ast.Call)
            and isinstance(noeud.func, ast.Attribute)
            and noeud.func.attr == "get"
        ):
            for argument in noeud.args[:1]:
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                    cles.add(argument.value)
        if (
            isinstance(noeud, ast.Subscript)
            and isinstance(noeud.slice, ast.Constant)
            and isinstance(noeud.slice.value, str)
        ):
            cles.add(noeud.slice.value)
    return {
        cle
        for cle in cles
        if "-" in cle or cle in ("id", "name", "state", "labels", "template", "manager")
    }


def test_les_champs_que_le_provider_lit_existent_dans_le_contrat() -> None:
    """Lu dans le code par AST plutôt que recopié à côté : un champ renommé en
    amont rendrait `None`, et l'inventaire un parc muet."""
    document = json.loads(CONTRAT.read_text(encoding="utf-8"))
    schemas = document["components"]["schemas"]
    connus = set(schemas["instance"]["properties"])
    connus |= set(schemas["instance-type"]["properties"])
    connus |= set(schemas["manager"]["properties"]) if "manager" in schemas else {"id", "type"}
    connus |= {"id", "name"}
    lues = _cles_lues(INVENTAIRE / "providers" / "instance.py")
    lues.update(cle for _, cle in instance.METADATA_FIELDS)
    inconnues = sorted(lues - connus)
    assert inconnues == [], f"le provider lit des champs absents du contrat : {inconnues}"


#: Les couches que l'ajout d'un produit ne doit pas toucher.
COEUR = (
    "models.py",
    "address.py",
    "groups.py",
    "hostname.py",
    "network.py",
    "filtering.py",
    "errors.py",
    "config.py",
    "providers/base.py",
)

PORTEURS_DE_DOCSTRING = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def _code_sans_prose(chemin: Path) -> str:
    """Le code seul : ni commentaire, ni docstring, mais toutes les chaînes.

    La prose nomme les produits pour expliquer ses décisions, et c'est très
    bien. Ce qui est interdit, c'est qu'une **instruction** les nomme.
    """
    arbre = ast.parse(chemin.read_text(encoding="utf-8"))
    for noeud in ast.walk(arbre):
        if not isinstance(noeud, PORTEURS_DE_DOCSTRING):
            continue
        corps = noeud.body
        if (
            corps
            and isinstance(corps[0], ast.Expr)
            and isinstance(corps[0].value, ast.Constant)
            and isinstance(corps[0].value.value, str)
        ):
            noeud.body = corps[1:] or [ast.Pass()]
    return ast.unparse(ast.fix_missing_locations(arbre))


@pytest.mark.parametrize("fichier", COEUR)
def test_aucune_couche_du_coeur_ne_nomme_un_produit(fichier: str) -> None:
    """Si cette assertion tombe un jour, c'est qu'un produit a fuité hors de son
    provider, et que le suivant coûtera une modification du cœur."""
    code = _code_sans_prose(INVENTAIRE / fichier)
    for produit in ("instance", "sks", "nodepool", "instance_pool", "dbaas"):
        assert re.search(rf"\b{produit}\b", code) is None, f"{fichier} nomme '{produit}'"


def test_le_meme_pipeline_traite_un_host_sans_cas_particulier() -> None:
    """Filtrage, nom d'hôte, groupes et adresse : aucune couche ne demande le produit."""
    host = instance.normalize(_instance(), "ch-gva-2", UNE_ZONE)
    garde, _ = filtering.keep(host.labels, host.state, filtering.Filters(labels={"env": "prod"}))
    attribues, _ = hostname.assign_hostnames((host,), ("name", "id"))
    noms = groups.group_names(host, ("product", "zone"))
    choix = address.select_ansible_host(host, address.AddressPolicy())
    assert garde and attribues[0][1] == "web01" and "exo_product_instance" in noms and choix.found
