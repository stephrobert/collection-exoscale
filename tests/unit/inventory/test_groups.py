"""Les groupes natifs, et l'assainissement de leurs noms."""

from __future__ import annotations

from ansible_collections.stephrobert.exoscale.plugins.module_utils.inventory.groups import (
    group_names,
    sanitize_group_name,
)
from ansible_collections.stephrobert.exoscale.plugins.module_utils.inventory.models import (
    InventoryHost,
    NetworkAttachment,
)


def test_un_nom_de_groupe_reste_lisible_et_valide() -> None:
    assert sanitize_group_name("pré-prod") == "pre_prod"
    assert sanitize_group_name("production/web") == "production_web"
    assert sanitize_group_name("2024") == "_2024"
    assert sanitize_group_name("///") == "inconnu"


def test_chaque_axe_donne_ses_groupes() -> None:
    host = InventoryHost(
        id="i-1",
        product="instance",
        zone="ch-gva-2",
        state="running",
        labels={"env": "prod", "role": "web"},
        private_networks=(
            NetworkAttachment(private_network_id="pn-1", private_network_name="backend"),
        ),
        manager_type="instance-pool",
        manager_id="pool-1",
        metadata={"type": "standard.medium"},
    )
    noms = group_names(
        host, ("product", "zone", "state", "labels", "private_network", "manager", "type")
    )
    assert noms == (
        "exo_label_env_prod",
        "exo_label_role_web",
        "exo_manager_instance_pool",
        "exo_manager_pool_1",
        "exo_private_network_backend",
        "exo_product_instance",
        "exo_state_running",
        "exo_type_standard_medium",
        "exo_zone_ch_gva_2",
    )


def test_un_axe_sans_valeur_ne_cree_pas_de_groupe_vide() -> None:
    host = InventoryHost(id="i-1", product="instance")
    assert group_names(host, ("zone", "state", "labels", "manager", "type")) == ()
