"""La source découpe un document unique par tag, et ne perd rien en chemin."""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.source.base import (
    ProductNotFoundError,
    VendoredSpecSource,
    census,
    read_products,
    split_product,
    tag_roots,
)

from .conftest import GADGET_SPECS


def test_lindex_designe_des_tags_et_non_des_fichiers() -> None:
    entrees = read_products(GADGET_SPECS)
    assert [(e.tag, e.product, e.version) for e in entrees] == [("gadget", "gadget", "v2")]


def test_un_tag_remonte_a_sa_racine() -> None:
    document = VendoredSpecSource(root=GADGET_SPECS).load_document("v2")
    racines = tag_roots(document)
    assert racines["gizmo"] == "gadget"
    assert racines["widget"] == "gadget"
    assert racines["gadget"] == "gadget"


def test_le_decoupage_garde_toute_la_famille_du_tag() -> None:
    document = VendoredSpecSource(root=GADGET_SPECS).load_document("v2")
    cut, famille = split_product(document, "gadget")
    identifiants = {
        op["operationId"]
        for item in cut["paths"].values()
        for op in item.values()
        if isinstance(op, dict)
    }
    assert famille == ("gadget", "gizmo", "widget")
    assert {"list-gadgets", "list-gadget-gizmos", "get-widget"} <= identifiants
    assert "list-others" not in identifiants, "un autre produit ne doit pas entrer"
    assert "get-orphan" not in identifiants, "une opération sans tag n'appartient à personne"


def test_un_tag_inconnu_est_refuse() -> None:
    document = VendoredSpecSource(root=GADGET_SPECS).load_document("v2")
    with pytest.raises(ProductNotFoundError):
        split_product(document, "nexiste-pas")


def test_le_recensement_compte_chaque_operation_une_fois() -> None:
    """Ce que l'index n'indexe pas n'est pas perdu : il est compté ici."""
    document = VendoredSpecSource(root=GADGET_SPECS).load_document("v2")
    recensement = census(document)
    assert recensement.by_root["gadget"] == 17
    assert recensement.by_root["other"] == 1
    assert recensement.by_root["stray"] == 1
    assert recensement.undeclared_tags == ("stray",)
    assert recensement.untagged == ("get-orphan",)
    assert recensement.total == 20


def test_un_produit_absent_de_lindex_est_refuse() -> None:
    with pytest.raises(ProductNotFoundError):
        VendoredSpecSource(root=GADGET_SPECS).load("other", "v2")


def test_un_contrat_absent_dit_comment_le_telecharger(tmp_path: Path) -> None:
    (tmp_path / "products.txt").write_text("gadget v2\n", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="sync:api"):
        VendoredSpecSource(root=tmp_path).load("gadget", "v2")
