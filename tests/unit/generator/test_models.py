"""Le modèle décide tout ce que le template écrit, et refuse ce qu'il ne sait pas."""

from __future__ import annotations

from pathlib import Path

from generator.ansible.models import AnsibleModuleSpec, build_module_specs
from generator.ir.enums import OperationKind
from generator.ir.models import ApiService
from generator.overrides.loader import OverrideSet, load_overrides
from generator.plan import ProductPlan, plan_service

from .conftest import LAB_COLLECTION


def _spec(specs: tuple[AnsibleModuleSpec, ...], name: str) -> AnsibleModuleSpec:
    return next(spec for spec in specs if spec.name == name)


def test_un_module_dinformation_calcule_son_selecteur(gadget_plan: ProductPlan) -> None:
    specs, _ = build_module_specs(gadget_plan, LAB_COLLECTION)
    info = _spec(specs, "gadget_info")
    assert info.kind is OperationKind.INFO
    assert info.selector == "id"
    assert "required" not in info.options["id"], (
        "le sélecteur bascule sur le GET, il n'est pas exigé"
    )
    assert info.options["labels"] == {"type": "dict"}


def test_une_ressource_imbriquee_a_un_selecteur_propre(gadget_plan: ProductPlan) -> None:
    specs, _ = build_module_specs(gadget_plan, LAB_COLLECTION)
    gizmo = _spec(specs, "gadget_gizmo_info")
    assert gizmo.selector == "gizmo_id"
    assert gizmo.options["id"]["required"] is True


def test_un_module_daction_regroupe_les_operations_de_la_ressource(
    gadget_plan: ProductPlan,
) -> None:
    specs, _ = build_module_specs(gadget_plan, LAB_COLLECTION)
    action = _spec(specs, "gadget_action")
    assert action.kind is OperationKind.ACTION
    assert action.selector == "id"
    assert [a.name for a in action.actions] == [
        "reset_field",
        "revert_to_snapshot",
        "scale",
        "start",
    ]
    assert action.options["action"]["choices"] == [a.name for a in action.actions]
    assert action.options["id"]["required"] is True


def test_ce_que_le_contrat_exige_pour_une_action_devient_required_if(
    gadget_plan: ProductPlan,
) -> None:
    specs, _ = build_module_specs(gadget_plan, LAB_COLLECTION)
    action = _spec(specs, "gadget_action")
    assert ("action", "scale", ["gadget_type"]) in action.required_if()
    assert "required" not in action.options["gadget_type"], "exigé par scale seule, pas par start"


def test_un_parametre_de_chemin_enumere_est_une_option_pas_un_selecteur(
    gadget_plan: ProductPlan,
) -> None:
    """`{field}` vaut `labels` ou `user-data` : c'est le nom du champ à remettre à zéro."""
    specs, _ = build_module_specs(gadget_plan, LAB_COLLECTION)
    action = _spec(specs, "gadget_action")
    assert action.options["field"] == {"type": "str", "choices": ["labels", "user-data"]}
    assert ("action", "reset_field", ["field"]) in action.required_if()


def test_une_ressource_dont_la_seule_action_remet_un_champ_a_zero_a_un_selecteur(
    gadget_plan: ProductPlan,
) -> None:
    """Reproduit elastic_ip, load_balancer et private_network du contrat réel.

    Leur seule action Day-2 est `reset-*-field`. Si `{field}` comptait comme
    sélecteur, l'intersection vaudrait `{id, field}` et le module serait
    refusé pour ambiguïté.
    """
    specs, skipped = build_module_specs(gadget_plan, LAB_COLLECTION)
    assert "gadget_widget_action" not in dict(skipped)
    action = _spec(specs, "gadget_widget_action")
    assert action.selector == "id"
    assert [a.name for a in action.actions] == ["reset_field"]


def test_la_classe_manage_est_ecartee_avec_sa_raison(gadget_plan: ProductPlan) -> None:
    _, skipped = build_module_specs(gadget_plan, LAB_COLLECTION)
    raisons = dict(skipped)
    assert "gadget" in raisons
    assert "MANAGE" in raisons["gadget"]


def test_le_binding_garde_le_nom_du_contrat_a_cote_de_loption(
    gadget_plan: ProductPlan,
) -> None:
    specs, _ = build_module_specs(gadget_plan, LAB_COLLECTION)
    action = _spec(specs, "gadget_action")
    scale = next(a for a in action.actions if a.name == "scale")
    assert scale.operation.body_params == {"gadget_type": "gadget-type"}
    assert scale.operation.method == "scale_gadget"
    assert scale.operation.is_async is True


def test_un_parametre_sans_type_ecarte_le_module_avec_sa_raison(
    gadget_plan: ProductPlan,
) -> None:
    _, skipped = build_module_specs(gadget_plan, LAB_COLLECTION)
    raisons = dict(skipped)
    assert "gadget_widget_info" in raisons
    assert "type absent du contrat" in raisons["gadget_widget_info"]


def test_un_override_type_rend_le_module_possible(
    gadget_service: ApiService, tmp_path: Path
) -> None:
    (tmp_path / "gadget.yml").write_text(
        """
operations:
  gadget.v2.Widget.get-widget:
    parameters:
      name:
        type: string
        reason: un nom est une chaîne, le contrat ne le dit pas
""",
        encoding="utf-8",
    )
    plan = plan_service(gadget_service, load_overrides("gadget", root=tmp_path))
    specs, _ = build_module_specs(plan, LAB_COLLECTION)
    widget = _spec(specs, "gadget_widget_info")
    assert widget.options["name"] == {"type": "str"}


def test_un_selecteur_qui_change_de_nom_se_renomme_par_override(
    gadget_service: ApiService, gadget_plan: ProductPlan
) -> None:
    """`{gadget-id}` là où les autres disent `{id}` : sans override, pas de sélecteur commun."""
    plan_sans = plan_service(gadget_service, OverrideSet(source=None))
    _, skipped = build_module_specs(plan_sans, LAB_COLLECTION)
    assert "gadget_action" in dict(skipped)

    specs, _ = build_module_specs(gadget_plan, LAB_COLLECTION)
    action = _spec(specs, "gadget_action")
    revert = next(a for a in action.actions if a.name == "revert_to_snapshot")
    assert revert.operation.path_params == {"id": "gadget-id"}
    assert revert.operation.body_params == {"snapshot_id": "id"}
    assert ("action", "revert_to_snapshot", ["snapshot_id"]) in action.required_if()


def test_un_module_qui_attend_declare_le_fragment_wait(gadget_plan: ProductPlan) -> None:
    specs, _ = build_module_specs(gadget_plan, LAB_COLLECTION)
    action = _spec(specs, "gadget_action")
    info = _spec(specs, "gadget_info")
    assert action.doc_fragments() == ["lab.gadget.exoscale", "lab.gadget.exoscale.wait"]
    assert info.doc_fragments() == ["lab.gadget.exoscale"]


def test_une_lecture_de_secret_le_dit_dans_sa_documentation(gadget_plan: ProductPlan) -> None:
    specs, _ = build_module_specs(gadget_plan, LAB_COLLECTION)
    password = _spec(specs, "gadget_password_info")
    assert password.sensitive_return is True
    assert any("secret" in note for note in password.documentation()["notes"])


def test_une_lecture_sans_liste_na_pas_de_selecteur_et_exige_ses_identifiants(
    gadget_plan: ProductPlan,
) -> None:
    """`get-organization` n'a aucun identifiant, `get-load-balancer-service` en a deux.

    Sans liste, rien ne bascule : la lecture est inconditionnelle et ses
    identifiants sont tous obligatoires. Exiger un sélecteur unique écartait
    ces lectures que le runtime sait exécuter.
    """
    specs, _ = build_module_specs(gadget_plan, LAB_COLLECTION)
    quota = _spec(specs, "gadget_quota_info")
    assert quota.selector is None
    assert quota.get_operation is not None and quota.list_operation is None
    password = _spec(specs, "gadget_password_info")
    assert password.selector is None
    assert password.options["id"]["required"] is True
    assert password.return_documentation()["gadget_password"]["returned"] == "always"


def test_une_liste_nommee_list_que_le_parser_ne_voit_pas_comme_liste_est_refusee(
    gadget_service: ApiService,
) -> None:
    """Une `list-*` rendue comme une lecture unitaire ferait passer une liste
    pour un objet, en silence : c'est une forme de réponse à mesurer, pas un module."""
    from dataclasses import replace

    from generator.ir.models import ApiResponse

    operations = tuple(
        replace(op, response=ApiResponse(schema="widget", payload_schema="widget"))
        if op.id == "list-widgets"
        else op
        for op in gadget_service.operations
        # Sans `get-widget`, dont le `{name}` sans type écarte déjà le module
        # pour une autre raison : la garde doit être la seule cause du refus.
        if op.id != "get-widget"
    )
    service = replace(gadget_service, operations=operations)
    plan = plan_service(service, OverrideSet(source=None))
    _, skipped = build_module_specs(plan, LAB_COLLECTION)
    raisons = dict(skipped)
    assert "gadget_widget_info" in raisons
    assert "list-widgets" in raisons["gadget_widget_info"]


def test_des_actions_a_deux_identifiants_communs_les_exigent_tous_les_deux(
    gadget_plan: ProductPlan,
) -> None:
    """`scale-sks-nodepool` porte `{id}` et `{sks-nodepool-id}` ; exiger un seul
    sélecteur écartait neuf modules d'action que le runtime sait exécuter."""
    specs, _ = build_module_specs(gadget_plan, LAB_COLLECTION)
    gizmo = _spec(specs, "gadget_gizmo_action")
    assert gizmo.selector is None
    assert gizmo.options["id"]["required"] is True
    assert gizmo.options["gizmo_id"]["required"] is True
    assert gizmo.actions[0].required == ()


def test_une_action_sur_un_singleton_na_ni_selecteur_ni_identifiant(
    gadget_plan: ProductPlan,
) -> None:
    """`reset-iam-organization-policy` agit sur une ressource sans identifiant."""
    specs, _ = build_module_specs(gadget_plan, LAB_COLLECTION)
    quota = _spec(specs, "gadget_quota_action")
    assert quota.selector is None
    assert [name for name, entry in quota.options.items() if entry.get("required")] == ["action"]
