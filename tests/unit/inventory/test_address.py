"""Le choix de `ansible_host`, et l'explication de ce choix."""

from __future__ import annotations

from ansible_collections.stephrobert.exoscale.plugins.module_utils.inventory.address import (
    AddressPolicy,
    select_ansible_host,
)
from ansible_collections.stephrobert.exoscale.plugins.module_utils.inventory.models import (
    InventoryHost,
    NetworkAttachment,
)


def _host(**champs: object) -> InventoryHost:
    return InventoryHost(id="i-1", product="instance", **champs)  # type: ignore[arg-type]


def test_lordre_des_familles_decide() -> None:
    host = _host(public_ipv4=("185.0.0.1",), private_ipv4=("10.0.0.5",))
    assert select_ansible_host(host, AddressPolicy()).address == "10.0.0.5"
    publique = AddressPolicy(priority=("public_ipv4", "private_ipv4"))
    assert select_ansible_host(host, publique).address == "185.0.0.1"


def test_la_selection_dit_dou_vient_ladresse() -> None:
    host = _host(
        private_ipv4=("10.0.0.5",),
        private_networks=(
            NetworkAttachment(
                private_network_id="pn-1", private_network_name="backend", ipv4=("10.0.0.5",)
            ),
        ),
    )
    choix = select_ansible_host(host, AddressPolicy())
    assert (choix.source, choix.private_network) == ("private_ipv4", "backend")
    assert "backend" in choix.explain("web01")


def test_un_reseau_nomme_restreint_le_choix() -> None:
    host = _host(
        private_ipv4=("10.0.0.5", "10.1.0.5"),
        private_networks=(
            NetworkAttachment(
                private_network_id="pn-1", private_network_name="backend", ipv4=("10.0.0.5",)
            ),
            NetworkAttachment(
                private_network_id="pn-2", private_network_name="monitoring", ipv4=("10.1.0.5",)
            ),
        ),
    )
    choix = select_ansible_host(host, AddressPolicy(private_network="monitoring"))
    assert choix.address == "10.1.0.5"
    assert select_ansible_host(host, AddressPolicy(private_network="pn-1")).address == "10.0.0.5"


def test_un_reseau_absent_est_dit_pas_devine() -> None:
    host = _host(public_ipv4=("185.0.0.1",))
    choix = select_ansible_host(host, AddressPolicy(private_network="backend"))
    assert not choix.found
    assert "backend" in choix.source


def test_aucune_adresse_est_un_resultat_pas_une_erreur() -> None:
    choix = select_ansible_host(_host(), AddressPolicy())
    assert not choix.found
    assert choix.considered == ("private_ipv4", "public_ipv4", "private_ipv6", "public_ipv6")


def test_une_famille_inconnue_est_ignoree_par_la_politique() -> None:
    assert AddressPolicy(priority=("public_ipv4", "mars")).families() == ("public_ipv4",)
