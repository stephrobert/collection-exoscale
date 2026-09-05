"""Ce que l'artefact d'un run compte comme couvert, et ce qu'il refuse de compter.

Le journal vient d'Ansible, par un plugin de rappel, et pas d'une analyse du
playbook : **joué n'est pas appelé**. Une tâche gardée par un `when` non
satisfait ne touche jamais l'API, et une route que feint décline répond
`feint does not serve` sans rien exercer. Les compter ferait de l'artefact un
compteur de bonnes intentions.
"""

from __future__ import annotations

from typing import Any

import example
import residue


def _journal(*taches: dict[str, Any], **faits: Any) -> dict[str, Any]:
    return {"taches": list(taches), "faits": faits}


def _tache(module: str, verdict: str = "ok", **reste: Any) -> dict[str, Any]:
    return {"module": module, "tache": module, "verdict": verdict, "changed": False, **reste}


def test_un_module_joue_est_compte() -> None:
    resultat = example.artefact(
        _journal(_tache("stephrobert.exoscale.compute_instance_info")), "emulateur", "abc", "aucun"
    )
    assert resultat["modules_joues"] == ["compute_instance_info"]
    assert resultat["modules_appeles_sans_reponse"] == []


def test_une_route_que_feint_decline_est_appelee_mais_pas_jouee() -> None:
    """Un 404 `feint does not serve` n'exerce rien : le compter ferait passer une
    limite de l'émulateur pour une preuve. Le mot de passe répond
    `resource not found`, et c'est la même chose."""
    resultat = example.artefact(
        _journal(
            _tache(
                "stephrobert.exoscale.compute_instance_console_info",
                msg="Client error 404: feint does not serve /v2/console/x",
            ),
            _tache(
                "stephrobert.exoscale.compute_instance_password_info",
                msg="Client error 404: resource not found",
            ),
        ),
        "emulateur",
        "abc",
        "aucun (émulateur)",
    )
    assert resultat["modules_joues"] == []
    assert resultat["modules_appeles_sans_reponse"] == [
        "compute_instance_console_info",
        "compute_instance_password_info",
    ]


def test_une_tache_sautee_nest_pas_une_couverture() -> None:
    """Une tâche que `when` a écartée n'a parlé à personne."""
    resultat = example.artefact(
        _journal(_tache("stephrobert.exoscale.compute_vpc_route_info", verdict="skipped")),
        "emulateur",
        "abc",
        "aucun",
    )
    assert resultat["modules_joues"] == []
    assert resultat["modules_appeles_sans_reponse"] == ["compute_vpc_route_info"]


def test_un_module_joue_une_fois_et_saute_ailleurs_compte_comme_joue() -> None:
    """La question posée est « a-t-il tourné », pas « toutes ses tâches ont-elles tourné »."""
    resultat = example.artefact(
        _journal(
            _tache("stephrobert.exoscale.compute_instance_action", verdict="skipped"),
            _tache("stephrobert.exoscale.compute_instance_action", verdict="changed"),
        ),
        "emulateur",
        "abc",
        "aucun",
    )
    assert resultat["modules_joues"] == ["compute_instance_action"]


def test_les_faits_du_recensement_passent_dans_lartefact() -> None:
    resultat = example.artefact(
        _journal(
            _tache("stephrobert.exoscale.compute_instance_action", verdict="changed"),
            non_emules=["compute_vpc_info"],
            idempotences_prouvees=["compute_instance_action.stop"],
        ),
        "emulateur",
        "abc",
        "aucun (émulateur)",
    )
    assert resultat["routes_non_servies"] == ["compute_vpc_info"]
    assert resultat["idempotence_prouvee"] == ["compute_instance_action.stop"]
    assert resultat["residu"] == "aucun (émulateur)"


# ---- le résidu ---------------------------------------------------------------


def test_une_ressource_apparue_est_un_residu() -> None:
    """Mesuré contre feint : une adresse élastique sans label a survécu à la
    première destruction, et c'est ce différentiel qui l'a dit."""
    avant = {"elastic-ip": {}, "instance": {"i-1": "web01"}}
    apres = {"elastic-ip": {"e-1": "192.0.2.2"}, "instance": {"i-1": "web01"}}
    apparus, disparus = residue.ecarts(avant, apres)
    assert apparus == ["  elastic-ip  192.0.2.2  (e-1)"] and disparus == []


def test_une_ressource_disparue_est_plus_grave_quun_residu() -> None:
    avant = {"instance": {"i-1": "web01", "i-9": "de-quelquun-dautre"}}
    apres = {"instance": {"i-1": "web01"}}
    apparus, disparus = residue.ecarts(avant, apres)
    assert apparus == [] and disparus == ["  instance  de-quelquun-dautre  (i-9)"]


def test_un_compte_inchange_na_ni_residu_ni_disparition() -> None:
    etat = {"instance": {"i-1": "web01"}, "ssh-key": {"cle": "cle"}}
    assert residue.ecarts(etat, dict(etat)) == ([], [])
