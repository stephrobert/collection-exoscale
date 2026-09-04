"""Le contrat réel de compute : ce que le golden fige, et ce que le plan en dit.

Ces tests rougissent quand Exoscale bouge. C'est voulu : une évolution de
l'API doit arriver comme un diff relu, jamais comme un résultat qui change
tout seul. `mise run golden:update` régénère le golden, et son diff se lit.
"""

from __future__ import annotations

import json

from generator.ir.enums import OperationKind
from generator.ir.models import ApiService
from generator.plan import ProductPlan

from .conftest import FIXTURES

GOLDEN = FIXTURES / "compute" / "expected_ir.json"


def test_lir_de_compute_est_celle_du_golden(compute_service: ApiService) -> None:
    assert GOLDEN.is_file(), "lancer `mise run golden:update` pour figer l'IR"
    assert json.loads(compute_service.to_json()) == json.loads(GOLDEN.read_text(encoding="utf-8"))


def test_aucune_operation_de_compute_nest_inconnue(compute_plan: ProductPlan) -> None:
    assert compute_plan.unknown == ()


def test_aucun_override_de_compute_nest_orphelin(compute_plan: ProductPlan) -> None:
    assert compute_plan.orphan_overrides == ()


def test_la_couverture_de_compute_nomme_son_denominateur(compute_plan: ProductPlan) -> None:
    """64 candidates Day-2 sur 111 opérations : le reste est écarté, pas caché."""
    comptes = compute_plan.count_by_kind()
    assert len(compute_plan.operations) == 111
    assert len(compute_plan.day2) == 64
    assert comptes[OperationKind.LIFECYCLE] + comptes[OperationKind.IGNORE] == 47
    assert compute_plan.coverage() == 1.0


def test_les_ecritures_de_compute_sont_asynchrones_sauf_le_vpc(
    compute_plan: ProductPlan,
) -> None:
    """70 sur 111 répondent par `operation` ; six opérations VPC récentes sont synchrones.

    Mesuré : `create-route`, `delete-route`, `delete-subnet`, `delete-vpc`,
    `update-subnet` et `update-vpc` répondent sans objet `operation`.
    """
    assert len(compute_plan.asynchronous) == 70
    par_id = {plan.operation.id: plan.operation.is_async for plan in compute_plan.operations}
    assert par_id["start-instance"] is True
    assert par_id["create-vpc"] is True
    assert par_id["delete-vpc"] is False
    assert par_id["update-subnet"] is False


def test_le_contrat_de_compute_signale_labsence_de_pagination(
    compute_service: ApiService,
) -> None:
    assert any("pagination" in w for w in compute_service.warnings)
