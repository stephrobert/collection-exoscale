"""Le plancher du fournisseur Terraform, et ce que le lanceur refuse d'appliquer.

Sous 0.71.0, le fournisseur d'Exoscale n'honorait `EXOSCALE_API_ENDPOINT` que
pour un de ses deux clients, et un `apply` se scindait entre l'émulateur et un
compte payant (feint#525, exoscale/terraform-provider-exoscale#573). La stack
épingle une version exacte ; ces tests portent sur la seconde barrière, celle
qui tient quand quelqu'un abaisse l'épingle.
"""

from __future__ import annotations

from typing import Any

import example
import pytest


def test_un_provider_sous_le_plancher_est_sous_le_plancher() -> None:
    assert example.sous_le_plancher("0.70.0")
    assert example.sous_le_plancher("0.69.3")


def test_un_provider_au_plancher_ou_au_dessus_peut_appliquer() -> None:
    assert not example.sous_le_plancher("0.71.0")
    assert not example.sous_le_plancher("0.72.1")
    assert not example.sous_le_plancher("1.0.0")


def test_une_version_illisible_est_sous_le_plancher() -> None:
    """Ce lanceur s'apprête à créer des ressources : ce qu'il ne sait pas lire
    ne l'y autorise pas."""
    assert example.sous_le_plancher("")
    assert example.sous_le_plancher("0.71.0-rc1")
    assert example.sous_le_plancher("inconnue")


def test_exiger_le_plancher_refuse_un_fournisseur_sous_le_plancher(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """La garde que la mutation `plancher-provider` neutralise."""
    monkeypatch.setattr(example, "provider_resolu", lambda env: "0.70.0")
    with pytest.raises(example.ExempleError, match=r"sous le plancher 0\.71\.0"):
        example.exiger_le_plancher({})


def test_exiger_le_plancher_rend_la_version_quand_elle_convient(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(example, "provider_resolu", lambda env: "0.71.0")
    assert example.exiger_le_plancher({}) == "0.71.0"


def test_le_fournisseur_se_lit_par_la_fin_de_sa_cle(monkeypatch: pytest.MonkeyPatch) -> None:
    """`registry.terraform.io` pour Terraform, `registry.opentofu.org` pour
    OpenTofu : la clé change d'hôte, pas de fin."""

    class Resultat:
        returncode = 0
        stderr = ""
        stdout = (
            '{"provider_selections": {"registry.opentofu.org/exoscale/exoscale": "0.71.0",'
            ' "registry.opentofu.org/hashicorp/null": "3.2.0"}}'
        )

    monkeypatch.setattr(example, "binaire", lambda nom: nom)
    monkeypatch.setattr(example, "lancer", lambda *a, **k: Resultat())
    assert example.provider_resolu({}) == "0.71.0"


def test_aucun_fournisseur_resolu_est_une_erreur(monkeypatch: pytest.MonkeyPatch) -> None:
    """Une stack qui ne déclare plus le fournisseur n'est pas une stack sûre par défaut."""

    class Resultat:
        returncode = 0
        stderr = ""
        stdout = '{"provider_selections": {}}'

    monkeypatch.setattr(example, "binaire", lambda nom: nom)
    monkeypatch.setattr(example, "lancer", lambda *a, **k: Resultat())
    with pytest.raises(example.ExempleError, match="aucun fournisseur exoscale"):
        example.provider_resolu({})


def test_les_sorties_terraform_perdent_leur_enveloppe() -> None:
    brut: dict[str, Any] = {
        "prefixe": {"value": "exo-1", "type": "string", "sensitive": False},
        "attendu": {"value": {"total": 6}, "type": ["object", {}], "sensitive": False},
    }
    assert example.sorties_terraform(brut) == {"prefixe": "exo-1", "attendu": {"total": 6}}


def test_lartefact_nomme_son_outillage() -> None:
    """Un artefact qui ne dit pas avec quel feint ni quel fournisseur il a été
    produit ne se relit pas."""
    resultat = example.artefact(
        {"taches": [], "faits": {}},
        "emulateur",
        "abc",
        "aucun (émulateur)",
        {"terraform": "Terraform v1.15.4", "feint": "v0.12.2-dev", "provider_exoscale": "0.71.0"},
    )
    assert resultat["outillage"] == {
        "feint": "v0.12.2-dev",
        "provider_exoscale": "0.71.0",
        "terraform": "Terraform v1.15.4",
    }
    assert example.artefact({"taches": []}, "emulateur", "abc", "aucun")["outillage"] == {}
