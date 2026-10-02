import json
import pytest
from pydantic import ValidationError

from app.core.events import CommandRequest
from app.actions.schema import ActionRequest, ActionResult, ActionDefinition, ActionPack
from app.core.state import AppState


def test_command_request_valid():
    cmd = CommandRequest(text="open vscode", source="voice", metadata={"channel": "mic"})
    assert cmd.text == "open vscode"
    assert cmd.source == "voice"
    assert cmd.metadata["channel"] == "mic"


def test_command_request_unknown_field_rejected():
    with pytest.raises(ValidationError):
        CommandRequest(text="test", source="dashboard", extra_field="forbidden")


def test_command_request_invalid_source_rejected():
    with pytest.raises(ValidationError):
        CommandRequest(text="test", source="telepathy")


def test_command_request_missing_required_rejected():
    with pytest.raises(ValidationError):
        CommandRequest(source="dashboard")


def test_action_request_valid():
    act = ActionRequest(
        id="act-1",
        tool="process.run",
        arguments={"argv": ["ls", "-la"]},
        reason="inspect directory",
        request_id="req-123",
        workspace="/home/user/project",
    )
    assert act.id == "act-1"
    assert act.tool == "process.run"
    assert act.arguments == {"argv": ["ls", "-la"]}
    assert act.reason == "inspect directory"
    assert act.request_id == "req-123"


def test_action_request_unknown_field_rejected():
    with pytest.raises(ValidationError):
        ActionRequest(
            id="act-1",
            tool="process.run",
            arguments={},
            reason="test",
            request_id="req-1",
            unauthorized_key="bypass",
        )


def test_action_request_missing_required_rejected():
    with pytest.raises(ValidationError):
        ActionRequest(id="act-1")


def test_action_request_canonical_serialization():
    # Two requests with identical content but different dict insertion order
    args1 = {"z_param": 1, "a_param": "hello", "nested": {"b": 2, "a": 1}}
    args2 = {"a_param": "hello", "nested": {"a": 1, "b": 2}, "z_param": 1}

    req1 = ActionRequest(
        id="act-1",
        tool="browser.open",
        arguments=args1,
        reason="search docs",
        request_id="req-1",
    )
    req2 = ActionRequest(
        id="act-1",
        tool="browser.open",
        arguments=args2,
        reason="search docs",
        request_id="req-1",
    )

    canonical1 = req1.to_canonical_json()
    canonical2 = req2.to_canonical_json()
    assert canonical1 == canonical2

    # Must be valid compact JSON without extra whitespace
    parsed = json.loads(canonical1)
    assert parsed["id"] == "act-1"
    assert parsed["tool"] == "browser.open"
    assert " " not in canonical1.split(":")[1]  # separators should be (',', ':')

    # Byte output matches UTF-8
    assert req1.to_canonical_bytes() == canonical1.encode("utf-8")


def test_action_result_valid():
    res_success = ActionResult(success=True, output="All tests passed")
    assert res_success.success is True
    assert res_success.output == "All tests passed"
    assert res_success.error is None

    res_fail = ActionResult(success=False, output="", error="Command failed with code 1")
    assert res_fail.success is False
    assert res_fail.error == "Command failed with code 1"


def test_action_result_unknown_field_rejected():
    with pytest.raises(ValidationError):
        ActionResult(success=True, unexpected="forbidden")


def test_app_state_interface():
    state = AppState()
    initial_dict = state.get_state()
    assert isinstance(initial_dict, dict)
    assert "status" in initial_dict

    state.update("status", "EXECUTING")
    assert state.get_state()["status"] == "EXECUTING"


def test_action_pack_schema_valid():
    pack_data = {
        "schema_version": 1,
        "pack_id": "core",
        "label": "Core actions",
        "actions": [
            {
                "id": "app.open_vscode",
                "enabled": True,
                "phrases": ["open vscode", "vs code kholo"],
                "executor": "process",
                "arguments": {"argv": ["code"]},
                "approval": "preapproved",
                "risk": "low",
                "timeout_seconds": 10,
            }
        ],
    }
    pack = ActionPack.model_validate(pack_data)
    assert pack.pack_id == "core"
    assert len(pack.actions) == 1
    assert pack.actions[0].id == "app.open_vscode"
    assert pack.actions[0].executor == "process"


def test_action_pack_unknown_field_rejected():
    pack_data = {
        "schema_version": 1,
        "pack_id": "core",
        "label": "Core actions",
        "unknown_pack_field": True,
        "actions": [],
    }
    with pytest.raises(ValidationError):
        ActionPack.model_validate(pack_data)


def test_action_definition_invalid_executor_rejected():
    action_data = {
        "id": "app.invalid",
        "executor": "arbitrary_eval",
        "arguments": {},
    }
    with pytest.raises(ValidationError):
        ActionDefinition.model_validate(action_data)
def test_ISSUE_J_app_state_mutability():
    from app.core.state import AppState
    from pydantic import ValidationError
    import pytest

    state = AppState()
    assert state.status == "DISABLED"

    state.status = "IDLE"
    assert state.status == "IDLE"

    with pytest.raises(ValidationError):
        state.status = "HACKED"
    
    with pytest.raises(ValidationError):
        state.update("status", "INVALID")
def test_ISSUE_L_canonical_json_types():
    from app.actions.schema import ActionRequest, ActionResult
    from pydantic import ValidationError
    import pytest
    import math

    with pytest.raises(ValidationError):
        ActionRequest(id="1", tool="test", arguments={"data": b"bytes"})
    
    with pytest.raises(ValidationError):
        ActionRequest(id="1", tool="test", arguments={"data": math.nan})
    
    with pytest.raises(ValidationError):
        ActionRequest(id="1", tool="test", arguments={"data": math.inf})
    
    with pytest.raises(ValidationError):
        ActionRequest(id="1", tool="test", arguments={"data": {"nested": set([1,2])}})    
    # Valid
    ActionRequest(id="1", tool="test", arguments={"data": {"nested": [1, 2, 3.14, "str", True, None]}})
