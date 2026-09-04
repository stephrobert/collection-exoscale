"""Fixtures partagées des tests du générateur."""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.ansible.collection import Collection
from generator.ir.models import ApiService
from generator.overrides.loader import load_overrides
from generator.parser.openapi import parse_document
from generator.plan import ProductPlan, build_plan, plan_service
from generator.source.base import VendoredSpecSource

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES = REPO_ROOT / "tests" / "fixtures"
GADGET_SPECS = FIXTURES / "gadget" / "input"
GADGET_OVERRIDES = FIXTURES / "gadget" / "overrides"
EXOSCALE_SPECS = REPO_ROOT / "specs" / "exoscale"

#: Identité figée pour les tests de rendu : ils mesurent le renderer, pas le
#: namespace du jour.
LAB_COLLECTION = Collection(
    namespace="lab",
    name="gadget",
    version="9.9.9",
    path=FIXTURES / "gadget" / "ansible_collections" / "lab" / "gadget",
    authors=("Contrat de laboratoire (@lab)",),
)


@pytest.fixture(scope="session")
def gadget_service() -> ApiService:
    """IR du contrat de laboratoire, indépendant des évolutions de l'API Exoscale."""
    return parse_document(VendoredSpecSource(root=GADGET_SPECS).load("gadget", "v2"))


@pytest.fixture()
def gadget_plan(gadget_service: ApiService) -> ProductPlan:
    """Le plan du laboratoire, avec ses overrides de renommage."""
    return plan_service(gadget_service, load_overrides("gadget", root=GADGET_OVERRIDES))


@pytest.fixture(scope="session")
def compute_service() -> ApiService:
    """IR du produit compute réel, tel qu'il est versionné dans `specs/`."""
    return parse_document(VendoredSpecSource(root=EXOSCALE_SPECS).load("compute", "v2"))


@pytest.fixture(scope="session")
def compute_plan() -> ProductPlan:
    return build_plan("compute", "v2", spec_root=EXOSCALE_SPECS)
