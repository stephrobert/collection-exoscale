"""Le nom d'hôte, et surtout ce qui se passe quand deux machines le partagent.

La collision est le défaut le plus coûteux d'un inventaire : la seconde
machine écrase la première, sans message. Ces tests exigent que la collision
soit résolue **et** dite.
"""

from __future__ import annotations

from ansible_collections.stephrobert.exoscale.plugins.module_utils.inventory.hostname import (
    assign_hostnames,
    is_known_source,
    pick_hostname,
    resolve_source,
)
from ansible_collections.stephrobert.exoscale.plugins.module_utils.inventory.models import (
    InventoryHost,
)


def _host(id_: str, **champs: object) -> InventoryHost:
    return InventoryHost(id=id_, product="instance", **champs)  # type: ignore[arg-type]


def test_la_premiere_source_disponible_gagne() -> None:
    assert pick_hostname(_host("i-1", name="web01"), ("name", "id")) == ("web01", "name")


def test_une_source_vide_est_sautee_pas_retenue() -> None:
    """Un nom vide n'est pas un nom : sinon l'inventaire contient une clé ''."""
    assert pick_hostname(_host("i-1", name=""), ("name", "id")) == ("i-1", "id")


def test_un_label_peut_nommer_la_machine() -> None:
    host = _host("i-1", labels={"env": "prod", "role": "web"})
    assert resolve_source(host, "label:role") == "web"
    assert resolve_source(host, "label:absent") is None
    assert resolve_source(_host("i-2", labels={"role": ""}), "label:role") is None


def test_une_source_inconnue_ne_lit_rien() -> None:
    """Sans la table des sources, une faute de frappe donnait un inventaire vide."""
    assert not is_known_source("nom")
    assert not is_known_source("label:")
    assert is_known_source("label:role") and is_known_source("private_ipv4")
    assert resolve_source(_host("i-1", name="web01"), "nom") is None


def test_deux_machines_du_meme_nom_ne_secrasent_pas() -> None:
    hosts = (
        _host("i-1", name="web01", zone="ch-gva-2"),
        _host("i-2", name="web01", zone="de-fra-1"),
    )
    attribues, avertissements = assign_hostnames(hosts, ("name",))
    assert [nom for _, nom in attribues] == ["web01", "web01_de-fra-1"]
    assert len(avertissements) == 1 and "déjà pris" in avertissements[0]


def test_la_meme_zone_desambiguise_par_lidentifiant() -> None:
    hosts = (
        _host("i-1", name="web01", zone="ch-gva-2"),
        _host("i-2", name="web01", zone="ch-gva-2"),
    )
    attribues, _ = assign_hostnames(hosts, ("name",))
    assert [nom for _, nom in attribues] == ["web01", "web01_ch-gva-2"]
    trois = (*hosts, _host("i-3", name="web01", zone="ch-gva-2"))
    attribues, _ = assign_hostnames(trois, ("name",))
    assert [nom for _, nom in attribues][-1] == "web01_i-3"


def test_une_machine_sans_nom_est_ecartee_et_dite() -> None:
    attribues, avertissements = assign_hostnames((_host("i-1"),), ("name",))
    assert attribues == ()
    assert "écartée" in avertissements[0]
