"""Le filtrage local, sur les labels et les états, et ce qui part à l'API."""

from __future__ import annotations

from ansible_collections.stephrobert.exoscale.plugins.module_utils.inventory.filtering import (
    Filters,
    keep,
)

LABELS = {"env": "prod", "role": "web"}


def test_any_garde_une_machine_qui_porte_un_des_labels() -> None:
    garde, _ = keep(LABELS, "running", Filters(labels={"env": "prod", "tier": "db"}))
    assert garde


def test_all_exige_tous_les_labels_et_nomme_les_manquants() -> None:
    garde, raison = keep(
        LABELS, "running", Filters(labels={"env": "prod", "tier": "db"}, labels_match="all")
    )
    assert not garde and "tier" in raison


def test_une_valeur_vide_veut_dire_la_cle_existe() -> None:
    assert keep(LABELS, None, Filters(labels={"role": ""}))[0]
    assert not keep({"env": "prod"}, None, Filters(labels={"role": ""}))[0]


def test_une_valeur_differente_ne_correspond_pas() -> None:
    garde, raison = keep(LABELS, None, Filters(labels={"env": "staging"}))
    assert not garde and "env" in raison


def test_letat_filtre_et_exclut() -> None:
    assert not keep(LABELS, "stopped", Filters(states=("running",)))[0]
    assert not keep(LABELS, "stopped", Filters(exclude_states=("stopped",)))[0]
    assert keep(LABELS, "running", Filters(states=("running",)))[0]


def test_une_exclusion_par_label_lemporte_sur_tout() -> None:
    garde, raison = keep(
        LABELS, "running", Filters(labels={"env": "prod"}, exclude_labels={"role": "web"})
    )
    assert not garde and "exclue" in raison
