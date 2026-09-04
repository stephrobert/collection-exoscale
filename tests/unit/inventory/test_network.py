"""L'index des baux, et la jointure sans appel d'API."""

from __future__ import annotations

from ansible_collections.stephrobert.exoscale.plugins.module_utils.inventory.network import (
    Lease,
    PrivateNetworkInfo,
    attach,
    build_index,
    flatten,
)

RESEAUX = (
    PrivateNetworkInfo(id="pn-1", name="backend"),
    PrivateNetworkInfo(id="pn-2", name="monitoring"),
)
BAUX = (
    Lease(private_network_id="pn-1", host_id="i-1", address="10.0.0.5"),
    Lease(private_network_id="pn-2", host_id="i-1", address="10.1.0.5"),
    Lease(private_network_id="pn-1", host_id="i-2", address="10.0.0.6"),
    Lease(private_network_id="pn-1", host_id="", address="10.0.0.99"),
)


def test_lindex_range_les_baux_par_instance_et_ignore_ceux_sans_machine() -> None:
    index = build_index(BAUX, RESEAUX)
    assert index.lease_count == 3
    assert [b.address for b in index.leases_by_host["i-1"]] == ["10.0.0.5", "10.1.0.5"]


def test_la_jointure_garde_le_reseau_et_son_nom() -> None:
    index = build_index(BAUX, RESEAUX)
    rattachements = attach("i-1", ("pn-1", "pn-2"), index)
    assert [(a.private_network_name, a.ipv4) for a in rattachements] == [
        ("backend", ("10.0.0.5",)),
        ("monitoring", ("10.1.0.5",)),
    ]
    assert flatten(rattachements) == (("10.0.0.5", "10.1.0.5"), ())


def test_un_reseau_declare_sans_bail_reste_un_rattachement_sans_adresse() -> None:
    """La machine est sur ce réseau ; elle n'y a pas encore d'adresse."""
    index = build_index((), RESEAUX)
    rattachements = attach("i-9", ("pn-1",), index)
    assert rattachements[0].private_network_id == "pn-1"
    assert rattachements[0].addresses == ()


def test_un_bail_sur_un_reseau_que_la_machine_ne_declare_pas_compte_quand_meme() -> None:
    index = build_index(BAUX, RESEAUX)
    assert [a.private_network_id for a in attach("i-2", (), index)] == ["pn-1"]


def test_une_adresse_ipv6_va_dans_sa_famille_et_perd_son_masque() -> None:
    index = build_index((Lease("pn-1", "i-1", "fd00::5/64"),), RESEAUX)
    rattachement = attach("i-1", ("pn-1",), index)[0]
    assert rattachement.ipv6 == ("fd00::5",) and rattachement.ipv4 == ()
