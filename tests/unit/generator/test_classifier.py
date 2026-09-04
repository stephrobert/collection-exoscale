"""La classification tranche, et ce qu'elle ne tranche pas se voit."""

from __future__ import annotations

from generator.classifier.rules import classify, verb_of
from generator.ir.enums import GenerationMode, HTTPMethod, OperationKind
from generator.ir.models import ApiOperation, ApiService
from generator.plan import ProductPlan


def _operation(operation_id: str, method: HTTPMethod, path: str = "/thing/{id}") -> ApiOperation:
    return ApiOperation(
        id=operation_id,
        product="x",
        version="v2",
        resource="thing",
        http_method=method,
        path=path,
    )


def test_le_verbe_est_le_premier_mot_de_loperation_id() -> None:
    assert verb_of(_operation("start-instance", HTTPMethod.PUT)) == "start"
    assert verb_of(_operation("re-encrypt", HTTPMethod.POST)) == "re"


def test_get_et_list_sont_de_linformation(gadget_plan: ProductPlan) -> None:
    par_operation = {plan.operation.id: plan.kind for plan in gadget_plan.operations}
    assert par_operation["get-gadget"] is OperationKind.INFO
    assert par_operation["list-gadgets"] is OperationKind.INFO


def test_reveal_est_une_lecture_sensible(gadget_plan: ProductPlan) -> None:
    decision = next(p for p in gadget_plan.operations if p.operation.id == "reveal-gadget-password")
    assert decision.kind is OperationKind.INFO
    assert "sensible" in decision.classification.reason


def test_une_lecture_portee_par_post_reste_de_linformation(gadget_plan: ProductPlan) -> None:
    """`get-dbaas-service-logs` et `get-impact-estimate` sont des POST qui n'écrivent rien."""
    decision = next(p for p in gadget_plan.operations if p.operation.id == "get-usage-report")
    assert decision.kind is OperationKind.INFO
    assert "POST" in decision.classification.reason


def test_create_et_delete_relevent_du_cycle_de_vie(gadget_plan: ProductPlan) -> None:
    par_operation = {plan.operation.id: plan.kind for plan in gadget_plan.operations}
    assert par_operation["create-gadget"] is OperationKind.LIFECYCLE
    assert par_operation["delete-gadget"] is OperationKind.LIFECYCLE


def test_update_est_une_gestion_detat(gadget_plan: ProductPlan) -> None:
    par_operation = {plan.operation.id: plan.kind for plan in gadget_plan.operations}
    assert par_operation["update-gadget"] is OperationKind.MANAGE


def test_un_put_qui_porte_un_verbe_daction_est_une_action(gadget_plan: ProductPlan) -> None:
    """La règle de Scaleway (PUT = MANAGE) laissait 52 actions d'Exoscale en UNKNOWN."""
    par_operation = {plan.operation.id: plan.kind for plan in gadget_plan.operations}
    assert par_operation["start-gadget"] is OperationKind.ACTION
    assert par_operation["scale-gadget"] is OperationKind.ACTION
    assert par_operation["start-gadget-maintenance"] is OperationKind.ACTION


def test_un_delete_sur_un_champ_ne_supprime_pas_la_ressource(gadget_plan: ProductPlan) -> None:
    """`reset-*-field` remet un champ à sa valeur par défaut : le contrat le dit."""
    decision = next(p for p in gadget_plan.operations if p.operation.id == "reset-gadget-field")
    assert decision.kind is OperationKind.ACTION
    assert "champ" in decision.classification.reason


def test_un_post_hors_creation_est_une_action(gadget_plan: ProductPlan) -> None:
    par_operation = {plan.operation.id: plan.kind for plan in gadget_plan.operations}
    assert par_operation["revert-gadget-to-snapshot"] is OperationKind.ACTION


def test_update_porte_par_post_reste_une_gestion_detat() -> None:
    decision = classify(_operation("update-reverse-dns-instance", HTTPMethod.POST))
    assert decision.kind is OperationKind.MANAGE
    assert "POST" in decision.reason


def test_une_methode_sans_regle_est_declaree_inconnue() -> None:
    """Un PATCH sans verbe d'écriture, un GET ou un DELETE à verbe étranger ne se rangent pas."""
    assert classify(_operation("replace-thing", HTTPMethod.PATCH)).kind is OperationKind.UNKNOWN
    assert classify(_operation("compute-thing", HTTPMethod.GET)).kind is OperationKind.UNKNOWN
    assert classify(_operation("purge-thing", HTTPMethod.DELETE)).kind is OperationKind.UNKNOWN
    decision = classify(_operation("purge-thing", HTTPMethod.DELETE))
    assert "purge" in decision.reason


def test_la_classification_automatique_se_declare_comme_telle() -> None:
    decision = classify(_operation("get-thing", HTTPMethod.GET))
    assert decision.mode is GenerationMode.AUTO
    assert decision.reason


def test_aucune_operation_ne_disparait_du_plan(
    gadget_plan: ProductPlan, gadget_service: ApiService
) -> None:
    assert len(gadget_plan.operations) == len(gadget_service.operations)
    assert {plan.operation.id for plan in gadget_plan.operations} == {
        operation.id for operation in gadget_service.operations
    }
