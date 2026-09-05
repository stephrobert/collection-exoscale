"""L'orchestration : l'index des baux par zone, et ce qu'un échec devient."""

from __future__ import annotations

from typing import Any

import pytest

from ansible_collections.stephrobert.exoscale.plugins.module_utils.inventory import discovery
from ansible_collections.stephrobert.exoscale.plugins.module_utils.inventory.errors import (
    AuthenticationFailed,
)
from ansible_collections.stephrobert.exoscale.plugins.module_utils.inventory.providers.base import (
    DiscoveryContext,
)


class _Client:
    def __init__(self, zone: str, reseaux: list[dict[str, Any]], details: dict[str, Any]) -> None:
        self.zone = zone
        self.reseaux = reseaux
        self.details = details
        self.lectures: list[str] = []

    def list_private_networks(self) -> dict[str, Any]:
        return {"private-networks": self.reseaux}

    def get_private_network(self, id: str) -> dict[str, Any]:
        self.lectures.append(id)
        return self.details[id]

    def list_instances(self, **kwargs: Any) -> dict[str, Any]:
        return {"instances": [{"id": "i-1", "name": "web01", "private-networks": [{"id": "pn-1"}]}]}


def _fabrique(client: _Client) -> Any:
    return lambda zone: client


def test_lindex_lit_les_baux_de_chaque_reseau_une_fois() -> None:
    client = _Client(
        "ch-gva-2",
        reseaux=[{"id": "pn-1", "name": "backend"}],
        details={"pn-1": {"id": "pn-1", "leases": [{"instance-id": "i-1", "ip": "10.0.0.5"}]}},
    )
    report = discovery.DiscoveryReport()
    index = discovery.build_network_index(_fabrique(client), ("ch-gva-2",), report)
    assert client.lectures == ["pn-1"]
    assert index["ch-gva-2"].lease_count == 1
    assert report.api_calls == 2 and report.leases == 1


def test_une_liste_qui_porte_deja_les_baux_evite_la_lecture() -> None:
    client = _Client(
        "ch-gva-2",
        reseaux=[
            {"id": "pn-1", "name": "backend", "leases": [{"instance-id": "i-1", "ip": "10.0.0.5"}]}
        ],
        details={},
    )
    index = discovery.build_network_index(_fabrique(client), ("ch-gva-2",))
    assert client.lectures == [] and index["ch-gva-2"].lease_count == 1


def test_un_droit_refuse_sur_les_reseaux_est_un_avertissement_pas_une_panne() -> None:
    class ExoscaleAPIClientException(Exception):
        def __init__(self) -> None:
            super().__init__("forbidden")
            from types import SimpleNamespace

            self.response = SimpleNamespace(status_code=403)

    class _Refus(_Client):
        def list_private_networks(self) -> dict[str, Any]:
            raise ExoscaleAPIClientException()

    report = discovery.DiscoveryReport()
    index = discovery.build_network_index(
        _fabrique(_Refus("ch-gva-2", [], {})), ("ch-gva-2",), report
    )
    assert index["ch-gva-2"].lease_count == 0
    assert report.errors == [] and "PermissionDenied" in report.warnings[0]


def test_un_refus_dauthentification_sur_les_reseaux_est_fatal() -> None:
    class ExoscaleAPIAuthException(Exception):
        pass

    class _Refus(_Client):
        def list_private_networks(self) -> dict[str, Any]:
            raise ExoscaleAPIAuthException("forbidden")

    with pytest.raises(AuthenticationFailed):
        discovery.build_network_index(_fabrique(_Refus("ch-gva-2", [], {})), ("ch-gva-2",))


def test_la_decouverte_joint_les_baux_aux_machines() -> None:
    client = _Client(
        "ch-gva-2",
        reseaux=[{"id": "pn-1", "name": "backend"}],
        details={"pn-1": {"id": "pn-1", "leases": [{"instance-id": "i-1", "ip": "10.0.0.5"}]}},
    )
    index = discovery.build_network_index(_fabrique(client), ("ch-gva-2",))
    resultat, report = discovery.discover(
        _fabrique(client), DiscoveryContext(zones=("ch-gva-2",), network=index), ("instance",)
    )
    assert resultat.hosts[0].private_ipv4 == ("10.0.0.5",)
    assert report.providers == {"instance": 1}


def test_un_produit_inconnu_est_refuse() -> None:
    with pytest.raises(ValueError, match="mars"):
        discovery.providers_for(lambda zone: None, ("mars",))


def test_lindex_nest_paye_que_pour_les_produits_qui_joignent() -> None:
    assert discovery.needs_network_index(("instance",))
    assert not discovery.needs_network_index(())


def test_la_fabrique_rend_un_client_par_zone_ou_un_seul_avec_une_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`EXOSCALE_API_URL` reste honoré : toutes les zones parlent au même hôte."""
    construits: list[dict[str, Any]] = []

    class _Faux:
        def __init__(
            self, key: str, secret: str, zone: str | None = None, url: str | None = None
        ) -> None:
            construits.append({"zone": zone, "url": url})

    monkeypatch.setattr(discovery, "Client", _Faux)
    monkeypatch.setattr(discovery, "HAS_SDK", True)
    par_zone = discovery.client_factory("k", "s")
    par_zone("ch-gva-2")
    par_zone("ch-gva-2")
    par_zone("de-fra-1")
    assert [c["zone"] for c in construits] == ["ch-gva-2", "de-fra-1"]

    construits.clear()
    emulateur = discovery.client_factory("k", "s", "http://127.0.0.1:4599")
    emulateur("ch-gva-2")
    emulateur("de-fra-1")
    assert [c["url"] for c in construits] == ["http://127.0.0.1:4599", "http://127.0.0.1:4599"]
