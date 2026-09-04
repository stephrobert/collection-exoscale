"""Ce que le renderer tient de lui-même, indépendamment du contrat.

`ansible-test sanity` refuse une ligne de plus de 160 caractères (pep8 E501),
mesuré sur les cinq versions d'ansible-core de la matrice : l'en-tête de
`compute_instance_action`, onze opérations sur une ligne, en faisait 240.
"""

from __future__ import annotations

from generator.renderer.modules import HEADER_WIDTH, operation_header

#: La limite qu'`ansible-test sanity` applique aux modules.
PEP8_LIMIT = 160


def test_len_tete_des_operations_se_replie_sous_la_limite_de_sanity() -> None:
    identifiants = tuple(f"very-long-operation-identifier-number-{i}" for i in range(30))
    lignes = operation_header(identifiants)
    assert len(lignes) > 1
    assert all(len(ligne) <= HEADER_WIDTH for ligne in lignes)
    assert all(len(ligne) <= PEP8_LIMIT for ligne in lignes)


def test_len_tete_commence_par_le_libelle_et_garde_chaque_operation_entiere() -> None:
    identifiants = tuple(f"revert-instance-to-snapshot-{i}" for i in range(12))
    lignes = operation_header(identifiants)
    assert lignes[0].startswith("# Opérations : ")
    assert all(ligne.startswith("#") for ligne in lignes)
    reconstitue = " ".join(ligne.lstrip("# ").replace("Opérations : ", "") for ligne in lignes)
    for identifiant in identifiants:
        assert identifiant in reconstitue


def test_une_seule_operation_tient_sur_une_ligne() -> None:
    assert operation_header(("get-instance",)) == ["# Opérations : get-instance"]
