"""Le plan compte ce qu'il compte, et ne maquille pas la mesure."""

from __future__ import annotations

from generator.ir.enums import OperationKind
from generator.ir.models import ApiService
from generator.overrides.loader import OverrideSet
from generator.plan import ProductPlan, plan_service


def test_une_couverture_sans_operation_day2_est_indefinie() -> None:
    """Un ratio sans dénominateur n'est pas zéro : il n'existe pas."""
    vide = plan_service(ApiService(name="vide", version="v2"), OverrideSet(source=None))
    assert vide.coverage() is None
    assert vide.built_coverage(("un_module",)) is None


def test_classee_nest_pas_portee_par_un_module(gadget_plan: ProductPlan) -> None:
    assert gadget_plan.coverage() is not None
    assert gadget_plan.built_coverage(()) == 0.0
    assert gadget_plan.built_coverage(()) != gadget_plan.coverage()


def test_le_denominateur_exclut_le_cycle_de_vie_et_lecarte(gadget_plan: ProductPlan) -> None:
    day2 = {plan.kind for plan in gadget_plan.day2}
    assert OperationKind.LIFECYCLE not in day2
    assert OperationKind.IGNORE not in day2


def test_chaque_classe_est_comptee_meme_a_zero(gadget_plan: ProductPlan) -> None:
    comptes = gadget_plan.count_by_kind()
    assert set(comptes) == set(OperationKind)
    assert comptes[OperationKind.UNKNOWN] == 0


def test_les_operations_asynchrones_sont_comptees(gadget_plan: ProductPlan) -> None:
    asynchrones = {plan.operation.id for plan in gadget_plan.asynchronous}
    assert "start-gadget" in asynchrones
    assert "get-gadget" not in asynchrones


def test_un_module_regroupe_ses_operations(gadget_plan: ProductPlan) -> None:
    modules = gadget_plan.modules()
    assert {plan.operation.id for plan in modules["gadget_info"]} >= {
        "get-gadget",
        "list-gadgets",
    }
    assert {plan.operation.id for plan in modules["gadget_action"]} >= {
        "start-gadget",
        "scale-gadget",
        "reset-gadget-field",
    }
