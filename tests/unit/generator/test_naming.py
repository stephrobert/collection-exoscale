"""Les noms se traduisent par des règles courtes, lisibles sans exécuter le code."""

from __future__ import annotations

from generator.ansible.models import action_name
from generator.parser.naming import (
    option_name,
    pluralize_phrase,
    singularize,
    singularize_phrase,
    snake_case,
    split_words,
)


def test_le_kebab_se_decoupe_en_mots() -> None:
    assert split_words("start-instance") == ["start", "instance"]
    assert split_words("security_group_rules") == ["security", "group", "rules"]
    assert snake_case("security-group") == "security_group"


def test_une_option_ansible_ne_porte_pas_de_tiret() -> None:
    assert option_name("disk-size") == "disk_size"
    assert option_name("auth_url") == "auth_url"
    assert option_name("id") == "id"


def test_les_sigles_ne_se_depluralisent_pas() -> None:
    assert singularize("dns") == "dns"
    assert singularize("sks") == "sks"
    assert singularize("settings") == "settings"
    assert singularize("rules") == "rule"
    assert singularize("policies") == "policy"


def test_une_expression_se_singularise_mot_a_mot() -> None:
    assert singularize_phrase("security_group_rules") == "security_group_rule"
    assert pluralize_phrase("instance_type") == "instance types"


def test_le_nom_dune_action_retire_les_mots_de_la_ressource() -> None:
    assert action_name("start-instance", "instance") == "start"
    assert action_name("resize-instance-disk", "instance") == "resize_disk"
    assert action_name("attach-instance-to-private-network", "instance") == (
        "attach_to_private_network"
    )
    assert action_name("reset-instance-pool-field", "instance_pool") == "reset_field"
    assert action_name("evict-instance-pool-members", "instance_pool") == "evict_members"
    assert action_name("enable-tpm", "instance") == "enable_tpm"


def test_les_noms_propres_finissant_par_s_restent_entiers() -> None:
    """Mesuré sur les chemins : `dbaas` devenait `dbaa`, `postgres` `postgre`.

    Treize vrais pluriels existent aussi (`rules`, `rotations`), donc la
    singularisation reste, et les noms propres sont déclarés un par un.
    """
    assert singularize("dbaas") == "dbaas"
    assert singularize("postgres") == "postgres"
    assert singularize("prometheus") == "prometheus"
    assert singularize("thanos") == "thanos"
    assert singularize("rotations") == "rotation"
