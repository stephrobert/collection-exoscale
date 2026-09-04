"""Un override est une affirmation : il doit désigner quelque chose, et se justifier."""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.ir.enums import ApiType, GenerationMode, OperationKind
from generator.ir.models import ApiService
from generator.overrides.loader import OverrideError, load_overrides
from generator.plan import plan_service


def _write(root: Path, contenu: str) -> Path:
    path = root / "gadget.yml"
    path.write_text(contenu, encoding="utf-8")
    return path


def test_un_produit_sans_fichier_donne_un_ensemble_vide(tmp_path: Path) -> None:
    overrides = load_overrides("gadget", root=tmp_path)
    assert overrides.operations == {}
    assert overrides.source is None


def test_un_override_change_la_classification(tmp_path: Path, gadget_service: ApiService) -> None:
    _write(
        tmp_path,
        """
operations:
  gadget.v2.Gadget.start-gadget:
    generation: ignore
    reason: un test
""",
    )
    plan = plan_service(gadget_service, load_overrides("gadget", root=tmp_path))
    start = next(item for item in plan.operations if item.operation.id == "start-gadget")
    assert start.kind is OperationKind.IGNORE
    assert start.mode is GenerationMode.OVERRIDE
    assert start.module is None


def test_un_override_renomme_la_ressource(tmp_path: Path, gadget_service: ApiService) -> None:
    _write(
        tmp_path,
        """
operations:
  gadget.v2.Gadget.reveal-gadget-password:
    resource: gadget_password
""",
    )
    plan = plan_service(gadget_service, load_overrides("gadget", root=tmp_path))
    reveal = next(item for item in plan.operations if item.operation.id == "reveal-gadget-password")
    assert reveal.resource == "gadget_password"
    assert reveal.module == "gadget_gadget_password_info"


def test_un_champ_inconnu_est_refuse(tmp_path: Path) -> None:
    """Une faute de frappe produirait sinon un override silencieusement inerte."""
    _write(
        tmp_path,
        """
operations:
  gadget.v2.Gadget.get-gadget:
    generatoin: ignore
    reason: faute de frappe volontaire
""",
    )
    with pytest.raises(OverrideError, match="champs inconnus"):
        load_overrides("gadget", root=tmp_path)


def test_une_classification_sans_raison_est_refusee(tmp_path: Path) -> None:
    _write(
        tmp_path,
        """
operations:
  gadget.v2.Gadget.get-gadget:
    generation: ignore
""",
    )
    with pytest.raises(OverrideError, match="sans `reason`"):
        load_overrides("gadget", root=tmp_path)


def test_un_renommage_doption_sans_raison_est_refuse(tmp_path: Path) -> None:
    _write(
        tmp_path,
        """
operations:
  gadget.v2.Gadget.revert-gadget-to-snapshot:
    parameters:
      gadget-id:
        option: id
""",
    )
    with pytest.raises(OverrideError, match="sans `reason`"):
        load_overrides("gadget", root=tmp_path)


def test_un_type_inconnu_est_refuse(tmp_path: Path) -> None:
    _write(
        tmp_path,
        """
operations:
  gadget.v2.Widget.get-widget:
    parameters:
      name:
        type: chaine
        reason: le contrat ne dit pas le type
""",
    )
    with pytest.raises(OverrideError, match="type="):
        load_overrides("gadget", root=tmp_path)


def test_un_type_pose_par_override_est_lu(tmp_path: Path) -> None:
    _write(
        tmp_path,
        """
operations:
  gadget.v2.Widget.get-widget:
    parameters:
      name:
        type: string
        reason: le contrat ne dit pas le type, et un nom est une chaîne
""",
    )
    overrides = load_overrides("gadget", root=tmp_path)
    declaration = overrides.get("gadget.v2.Widget.get-widget")
    assert declaration is not None
    assert declaration.parameters["name"].type is ApiType.STRING


def test_un_override_orphelin_est_signale(tmp_path: Path, gadget_service: ApiService) -> None:
    _write(
        tmp_path,
        """
operations:
  gadget.v2.Gadget.get-gadget-disparu:
    generation: ignore
    reason: cette opération n'existe plus
""",
    )
    plan = plan_service(gadget_service, load_overrides("gadget", root=tmp_path))
    assert plan.orphan_overrides == ("gadget.v2.Gadget.get-gadget-disparu",)
