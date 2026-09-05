"""Ce que le plugin sérialise, et ce qu'il rend après un aller-retour de cache.

Toute exécution passe par cette sérialisation, avec ou sans cache : ce qui n'y
survit pas n'existe pas pour l'utilisateur, même si le provider l'a produit.
"""

from __future__ import annotations

from ansible_collections.stephrobert.exoscale.plugins.inventory.compute import (
    InventoryModule,
    _plain,
)
from ansible_collections.stephrobert.exoscale.plugins.module_utils.inventory.address import (
    AddressPolicy,
    select_ansible_host,
)
from ansible_collections.stephrobert.exoscale.plugins.module_utils.inventory.models import (
    InventoryHost,
    NetworkAttachment,
)


def _host() -> InventoryHost:
    return InventoryHost(
        id="i-1",
        product="instance",
        name="web01",
        zone="ch-gva-2",
        state="running",
        labels={"env": "prod"},
        public_ipv4=("185.0.0.1",),
        private_ipv4=("10.0.0.5",),
        private_networks=(NetworkAttachment("pn-1", "backend", ipv4=("10.0.0.5",)),),
        manager_type="sks-nodepool",
        manager_id="np-1",
        metadata={"type": "standard.medium"},
        raw={"id": "i-1"},
    )


def test_tout_le_modele_survit_a_laller_retour() -> None:
    rendu = InventoryModule._deserialise(InventoryModule._serialise(_host()))
    assert rendu == _host()


def test_sans_reponse_brute_rien_nest_invente() -> None:
    host = InventoryHost(id="i-1", product="instance")
    assert InventoryModule._deserialise(InventoryModule._serialise(host)).raw is None


def test_ce_quun_cache_ne_sait_pas_ecrire_devient_du_texte() -> None:
    class Opaque:
        def __str__(self) -> str:
            return "objet-opaque"

    assert _plain({"a": Opaque(), "b": [Opaque()], "n": 3}) == {
        "a": "objet-opaque",
        "b": ["objet-opaque"],
        "n": 3,
    }


def test_les_hostvars_portent_de_quoi_enchainer_sur_les_modules() -> None:
    host = _host()
    variables = InventoryModule._host_variables(host, select_ansible_host(host, AddressPolicy()))
    assert variables["exoscale_id"] == "i-1" and variables["exoscale_zone"] == "ch-gva-2"
    assert variables["exoscale_manager_type"] == "sks-nodepool"
    assert variables["exoscale_instance"] == {"type": "standard.medium"}
    assert variables["exoscale_address_source"] == "private_ipv4"
    assert variables["exoscale_raw"] == {"id": "i-1"}
