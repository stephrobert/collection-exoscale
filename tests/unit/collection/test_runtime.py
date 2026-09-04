"""Le runtime envoie le nom du contrat, attend l'opération, et ne ment pas sur `changed`."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ansible_collections.stephrobert.exoscale.plugins.module_utils import (  # noqa: E402
    exoscale as runtime,
)


class _Module:
    def __init__(self, params: dict[str, object], check_mode: bool = False) -> None:
        self.params = params
        self.check_mode = check_mode
        self.exited: dict[str, object] | None = None
        self.failed: dict[str, object] | None = None

    def exit_json(self, **kwargs: object) -> None:
        self.exited = kwargs
        raise SystemExit(0)

    def fail_json(self, **kwargs: object) -> None:
        self.failed = kwargs
        raise SystemExit(1)


class _Client:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.waited: list[str] = []

    def start_instance(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("start_instance", kwargs))
        return {"id": "op-1", "state": "pending"}

    def revert_instance_to_snapshot(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("revert_instance_to_snapshot", kwargs))
        return {"id": "op-2", "state": "pending"}

    def list_instances(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("list_instances", kwargs))
        return {"instances": [{"id": "a"}, {"id": "b"}]}

    def wait(self, operation_id: str, max_wait_time: int | None = None) -> dict[str, object]:
        self.waited.append(operation_id)
        return {"id": operation_id, "state": "success"}


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> _Client:
    fake = _Client()
    monkeypatch.setattr(runtime, "build_client", lambda module: fake)
    return fake


def _action_spec() -> runtime.ActionModule:
    start = runtime.Operation(
        id="start-instance",
        method="start_instance",
        path_params={"id": "id"},
        body_params={"rescue_profile": "rescue-profile"},
        is_async=True,
    )
    revert = runtime.Operation(
        id="revert-instance-to-snapshot",
        method="revert_instance_to_snapshot",
        path_params={"id": "instance-id"},
        body_params={"snapshot_id": "id"},
        is_async=True,
    )
    return runtime.ActionModule(
        resource="instance",
        selector="id",
        actions=(runtime.Action("start", start), runtime.Action("revert_to_snapshot", revert)),
    )


def test_le_runtime_envoie_le_nom_du_contrat_et_non_celui_de_loption(client: _Client) -> None:
    """`id` de l'option part en `instance_id` au SDK, `snapshot_id` part en `id`."""
    module = _Module(
        {"action": "revert_to_snapshot", "id": "inst", "snapshot_id": "snap", "wait": True}
    )
    with pytest.raises(SystemExit):
        runtime.run_action_module(module, _action_spec())
    assert client.calls == [("revert_instance_to_snapshot", {"instance_id": "inst", "id": "snap"})]


def test_une_action_attend_la_fin_de_loperation(client: _Client) -> None:
    module = _Module({"action": "start", "id": "inst", "rescue_profile": None, "wait": True})
    with pytest.raises(SystemExit):
        runtime.run_action_module(module, _action_spec())
    assert client.waited == ["op-1"]
    assert module.exited is not None
    assert module.exited["changed"] is True
    assert module.exited["operation"] == {"id": "op-1", "state": "success"}


def test_sans_attente_le_retour_dit_que_loperation_est_en_attente(client: _Client) -> None:
    module = _Module({"action": "start", "id": "inst", "wait": False})
    with pytest.raises(SystemExit):
        runtime.run_action_module(module, _action_spec())
    assert client.waited == []
    assert module.exited is not None
    assert module.exited["operation"] == {"id": "op-1", "state": "pending"}


def test_le_check_mode_nappelle_pas_lapi(client: _Client) -> None:
    module = _Module({"action": "start", "id": "inst", "wait": True}, check_mode=True)
    with pytest.raises(SystemExit):
        runtime.run_action_module(module, _action_spec())
    assert client.calls == []
    assert module.exited is not None and module.exited["changed"] is True


def test_une_liste_rend_le_champ_utile_sous_le_nom_pluriel(client: _Client) -> None:
    spec = runtime.InfoModule(
        resource="instance",
        list_operation=runtime.Operation(
            id="list-instances",
            method="list_instances",
            path_params={},
            payload_field="instances",
            is_list=True,
        ),
        selector="id",
    )
    module = _Module({"id": None})
    with pytest.raises(SystemExit):
        runtime.run_info_module(module, spec)
    assert module.exited == {"changed": False, "instances": [{"id": "a"}, {"id": "b"}]}


def test_une_methode_absente_du_sdk_echoue_en_le_nommant(client: _Client) -> None:
    spec = runtime.InfoModule(
        resource="thing",
        list_operation=runtime.Operation(
            id="list-things", method="list_things", path_params={}, is_list=True
        ),
    )
    module = _Module({})
    with pytest.raises(SystemExit):
        runtime.run_info_module(module, spec)
    assert module.failed is not None
    assert module.failed["sdk_method"] == "list_things"
