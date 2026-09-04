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


def test_une_action_synchrone_rend_sa_reponse_sous_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """`enable-kms-key` répond `success-response`, pas une opération : la ranger
    sous `operation` ferait chercher un `state` qui n'existe pas."""

    class _SyncClient(_Client):
        def enable_kms_key(self, **kwargs: object) -> dict[str, object]:
            self.calls.append(("enable_kms_key", kwargs))
            return {"success": True}

    fake = _SyncClient()
    monkeypatch.setattr(runtime, "build_client", lambda module: fake)
    spec = runtime.ActionModule(
        resource="kms_key",
        selector="id",
        actions=(
            runtime.Action(
                "enable",
                runtime.Operation(
                    id="enable-kms-key",
                    method="enable_kms_key",
                    path_params={"id": "id"},
                    is_async=False,
                ),
            ),
        ),
    )
    module = _Module({"action": "enable", "id": "key-1"})
    with pytest.raises(SystemExit):
        runtime.run_action_module(module, spec)
    assert fake.waited == []
    assert module.exited == {"changed": True, "result": {"success": True}}


class _StatefulClient(_Client):
    """Un client dont l'instance change d'état à chaque lecture, dans l'ordre donné."""

    def __init__(self, states: list[str]) -> None:
        super().__init__()
        self.states = list(states)
        self.reads = 0

    def get_instance(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("get_instance", kwargs))
        self.reads += 1
        state = self.states.pop(0) if len(self.states) > 1 else self.states[0]
        return {"id": kwargs.get("id"), "state": state}

    def reboot_instance(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("reboot_instance", kwargs))
        return {"id": "op-3", "state": "pending"}


def _stateful_spec() -> runtime.ActionModule:
    read = runtime.Operation(id="get-instance", method="get_instance", path_params={"id": "id"})
    start = runtime.Operation(
        id="start-instance", method="start_instance", path_params={"id": "id"}, is_async=True
    )
    reboot = runtime.Operation(
        id="reboot-instance", method="reboot_instance", path_params={"id": "id"}, is_async=True
    )
    return runtime.ActionModule(
        resource="instance",
        selector="id",
        actions=(
            runtime.Action("start", start, expected_state="running"),
            runtime.Action("reboot", reboot, expected_state="running", always=True),
        ),
        state_field="state",
        read_operation=read,
    )


@pytest.fixture(autouse=True)
def _sans_attente(monkeypatch: pytest.MonkeyPatch) -> None:
    """Attendre pour de vrai ne prouve rien : la pause est neutralisée."""
    monkeypatch.setattr(runtime, "_sleep", lambda seconds: None)


def test_une_action_dont_letat_est_deja_atteint_ne_change_rien(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`start` sur une machine qui tourne n'a rien à faire, et le dit par `changed=False`."""
    fake = _StatefulClient(["running"])
    monkeypatch.setattr(runtime, "build_client", lambda module: fake)
    module = _Module({"action": "start", "id": "inst", "wait": True})
    with pytest.raises(SystemExit):
        runtime.run_action_module(module, _stateful_spec())
    assert [nom for nom, _ in fake.calls] == ["get_instance"]
    assert module.exited is not None
    assert module.exited["changed"] is False and module.exited["state"] == "running"


def test_apres_success_le_module_attend_letat_attendu(monkeypatch: pytest.MonkeyPatch) -> None:
    """`success` sur l'opération précède l'état : la machine est relue jusqu'à `running`."""
    fake = _StatefulClient(["stopped", "starting", "starting", "running"])
    monkeypatch.setattr(runtime, "build_client", lambda module: fake)
    module = _Module({"action": "start", "id": "inst", "wait": True, "wait_timeout": 30})
    with pytest.raises(SystemExit):
        runtime.run_action_module(module, _stateful_spec())
    assert fake.waited == ["op-1"]
    assert module.exited is not None
    assert module.exited["changed"] is True and module.exited["state"] == "running"
    assert fake.reads == 4


def test_une_action_always_agit_meme_si_letat_est_atteint(monkeypatch: pytest.MonkeyPatch) -> None:
    """`reboot` vise `running`, qui est aussi l'état de départ : il agit quand même."""
    fake = _StatefulClient(["running"])
    monkeypatch.setattr(runtime, "build_client", lambda module: fake)
    module = _Module({"action": "reboot", "id": "inst", "wait": True})
    with pytest.raises(SystemExit):
        runtime.run_action_module(module, _stateful_spec())
    assert ("reboot_instance", {"id": "inst"}) in fake.calls
    assert module.exited is not None and module.exited["changed"] is True


def test_un_etat_jamais_atteint_echoue_en_disant_changed(monkeypatch: pytest.MonkeyPatch) -> None:
    """L'action a été acceptée : un échec après coup doit dire que la machine a bougé."""
    fake = _StatefulClient(["stopped", "starting"])
    monkeypatch.setattr(runtime, "build_client", lambda module: fake)
    horloge = iter([0.0, 0.0, 1.0, 100.0, 200.0, 300.0])
    monkeypatch.setattr(runtime.time, "monotonic", lambda: next(horloge))
    module = _Module({"action": "start", "id": "inst", "wait": True, "wait_timeout": 5})
    with pytest.raises(SystemExit):
        runtime.run_action_module(module, _stateful_spec())
    assert module.failed is not None
    assert module.failed["changed"] is True and module.failed["state"] == "starting"
    assert "expected 'running'" in module.failed["msg"]


def test_un_echec_de_lattente_de_loperation_dit_changed(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Casse(_Client):
        def wait(self, operation_id: str, max_wait_time: int | None = None) -> dict[str, object]:
            raise runtime.ExoscaleAPIException("Operation error: failure, disk full")

    monkeypatch.setattr(runtime, "build_client", lambda module: _Casse())
    module = _Module({"action": "start", "id": "inst", "wait": True})
    with pytest.raises(SystemExit):
        runtime.run_action_module(module, _action_spec())
    assert module.failed is not None
    assert module.failed["changed"] is True and "disk full" in module.failed["msg"]


def test_sans_attente_letat_nest_pas_lu(monkeypatch: pytest.MonkeyPatch) -> None:
    """`wait: false` rend l'opération acceptée, et ne lit rien : rien à vérifier."""
    fake = _StatefulClient(["running"])
    monkeypatch.setattr(runtime, "build_client", lambda module: fake)
    module = _Module({"action": "start", "id": "inst", "wait": False})
    with pytest.raises(SystemExit):
        runtime.run_action_module(module, _stateful_spec())
    assert fake.reads == 0
    assert module.exited is not None and module.exited["operation"] == {
        "id": "op-1",
        "state": "pending",
    }
