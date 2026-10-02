"""Tests for PH-040 Central Action Dispatcher, Policy Floored Semantics, and Composites."""

import json
from pathlib import Path
import pytest

from app.actions.registry import ActionRegistry, RegistryAmbiguity
from app.actions.schema import ActionDefinition, ActionPack, ActionRequest, ActionResult
from app.core.config import FileRootConfig
from app.core.dispatcher import ActionDispatcher
from app.executors.base import BaseExecutor
from app.executors.files import FileExecutor
from app.executors.process import ProcessExecutor
from app.executors.xdg import XdgExecutor
from app.policy.approvals import ApprovalRequest
from app.policy.engine import PolicyDecision, PolicyEngine, PreapprovalRule
from app.policy.risk import RiskLevel


class MockExecutor(BaseExecutor):
    """Spy executor to record calls."""

    def __init__(self, return_success=True, return_output="ok", return_error=None):
        self.calls = []
        self.return_success = return_success
        self.return_output = return_output
        self.return_error = return_error

    async def execute(self, action: ActionRequest, context=None) -> ActionResult:
        self.calls.append((action, context))
        return ActionResult(
            success=self.return_success,
            output=self.return_output,
            error=self.return_error,
        )


def write_test_pack(directory: Path, name: str, actions: list[dict]) -> Path:
    pack_data = {
        "pack_id": name,
        "label": name,
        "schema_version": 1,
        "actions": actions,
    }
    file_path = directory / f"{name}.json"
    file_path.write_text(json.dumps(pack_data), encoding="utf-8")
    return file_path


# ---------------------------------------------------------------------------
# POLICY & DISPATCHER TESTS
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_dispatcher_deny_never_calls_executor(tmp_path):
    engine = PolicyEngine()
    reg = ActionRegistry(tmp_path)
    assert reg.reload()
    mock_proc = MockExecutor()

    dispatcher = ActionDispatcher(
        policy_engine=engine,
        registry=reg,
        process_executor=mock_proc,
    )

    # Disallowed action (e.g. unknown tool or blocked command)
    req = ActionRequest(
        id="test.bad",
        tool="unsupported.tool",
        arguments={},
    )
    result = await dispatcher.dispatch_request(req)
    assert not result.success
    assert "denied by policy" in result.error
    assert len(mock_proc.calls) == 0


@pytest.mark.anyio
async def test_dispatcher_ask_user_never_calls_executor(tmp_path):
    engine = PolicyEngine()
    reg = ActionRegistry(tmp_path)
    assert reg.reload()
    mock_proc = MockExecutor()

    dispatcher = ActionDispatcher(
        policy_engine=engine,
        registry=reg,
        process_executor=mock_proc,
    )

    # Process without preapproval rule evaluates to ASK_USER
    req = ActionRequest(
        id="test.proc",
        tool="process.run",
        arguments={"argv": ["ls", "-la"], "cwd": "/tmp"},
    )
    result = await dispatcher.dispatch_request(req)
    assert not result.success
    assert "requires user approval" in result.error
    assert len(mock_proc.calls) == 0


@pytest.mark.anyio
async def test_self_created_approval_request_cannot_authorize_ask_user(tmp_path):
    """CRITICAL RULE: ApprovalRequest is not an authorization grant."""
    engine = PolicyEngine()
    reg = ActionRegistry(tmp_path)
    assert reg.reload()
    mock_proc = MockExecutor()

    dispatcher = ActionDispatcher(
        policy_engine=engine,
        registry=reg,
        process_executor=mock_proc,
    )

    req = ActionRequest(
        id="test.ask",
        tool="process.run",
        arguments={"argv": ["echo", "test"], "cwd": "/tmp"},
    )
    # Construct an ApprovalRequest programmatically
    approval = ApprovalRequest.from_action(req, risk_level=RiskLevel.LOW)
    assert approval.action_id == req.id

    # The existence of this ApprovalRequest must NOT bypass policy or trigger execution
    result = await dispatcher.dispatch_request(req)
    assert not result.success
    assert "requires user approval" in result.error
    assert len(mock_proc.calls) == 0


@pytest.mark.anyio
async def test_preapproved_definition_still_requires_policy_engine_allow(tmp_path):
    # Definition says approval="preapproved"
    write_test_pack(
        tmp_path,
        "core",
        [
            {
                "id": "app.run",
                "phrases": ["run app"],
                "executor": "process",
                "arguments": {"argv": ["python3", "-c", "print(1)"], "cwd": str(tmp_path)},
                "approval": "preapproved",
                "risk": "medium",
            }
        ],
    )
    reg = ActionRegistry(tmp_path)
    assert reg.reload()

    # But PolicyEngine has NO preapproval rule for python3
    engine = PolicyEngine(preapproved_rules=[])
    mock_proc = MockExecutor()
    dispatcher = ActionDispatcher(policy_engine=engine, registry=reg, process_executor=mock_proc)

    match = reg.resolve("run app")
    assert match is not None
    result = await dispatcher.dispatch_match(match)
    # Must NOT execute because PolicyEngine returned ASK_USER
    assert not result.success
    assert "requires user approval" in result.error
    assert len(mock_proc.calls) == 0


@pytest.mark.anyio
async def test_definition_deny_overrides_policy_allow(tmp_path):
    # Definition says approval="deny"
    write_test_pack(
        tmp_path,
        "core",
        [
            {
                "id": "app.git",
                "phrases": ["git status"],
                "executor": "process",
                "arguments": {"argv": ["git", "status"], "cwd": str(tmp_path)},
                "approval": "deny",  # Strict deny in definition
                "risk": "low",
            }
        ],
    )
    reg = ActionRegistry(tmp_path)
    assert reg.reload()

    # PolicyEngine has preapproval rule that would otherwise allow git status
    rule = PreapprovalRule(
        id="git-rule",
        executable="git",
        argv_prefix=("status",),
        working_roots=(str(tmp_path),),
        approval="preapproved",
        timeout_seconds=10,
        risk="low",
        network_allowed=True,
    )
    engine = PolicyEngine(preapproved_rules=[rule])
    mock_proc = MockExecutor()
    dispatcher = ActionDispatcher(policy_engine=engine, registry=reg, process_executor=mock_proc)

    match = reg.resolve("git status")
    assert match is not None
    result = await dispatcher.dispatch_match(match)
    # Definition deny must strictly override policy engine allow
    assert not result.success
    assert "denied by policy" in result.error
    assert len(mock_proc.calls) == 0


@pytest.mark.anyio
async def test_always_ask_overrides_policy_allow(tmp_path):
    # Definition says approval="always_ask"
    write_test_pack(
        tmp_path,
        "core",
        [
            {
                "id": "app.git",
                "phrases": ["git status"],
                "executor": "process",
                "arguments": {"argv": ["git", "status"], "cwd": str(tmp_path)},
                "approval": "always_ask",
                "risk": "low",
            }
        ],
    )
    reg = ActionRegistry(tmp_path)
    assert reg.reload()

    rule = PreapprovalRule(
        id="git-rule",
        executable="git",
        argv_prefix=("status",),
        working_roots=(str(tmp_path),),
        approval="preapproved",
        timeout_seconds=10,
        risk="low",
        network_allowed=True,
    )
    engine = PolicyEngine(preapproved_rules=[rule])
    mock_proc = MockExecutor()
    dispatcher = ActionDispatcher(policy_engine=engine, registry=reg, process_executor=mock_proc)

    match = reg.resolve("git status")
    assert match is not None
    result = await dispatcher.dispatch_match(match)
    # always_ask must prevent automatic execution
    assert not result.success
    assert "requires user approval" in result.error
    assert len(mock_proc.calls) == 0


@pytest.mark.anyio
async def test_high_or_critical_risk_never_silently_executes(tmp_path):
    # Action evaluated as HIGH risk (e.g. file delete or privilege executable)
    engine = PolicyEngine()
    reg = ActionRegistry(tmp_path)
    assert reg.reload()
    mock_proc = MockExecutor()
    dispatcher = ActionDispatcher(policy_engine=engine, registry=reg, process_executor=mock_proc)

    req = ActionRequest(
        id="test.danger",
        tool="process.run",
        arguments={"argv": ["sudo", "reboot"], "cwd": "/tmp"},
    )
    result = await dispatcher.dispatch_request(req)
    assert not result.success
    assert "requires user approval" in result.error
    assert len(mock_proc.calls) == 0


@pytest.mark.anyio
async def test_forged_action_request_registered_id_provides_no_extra_privilege(tmp_path):
    write_test_pack(
        tmp_path,
        "core",
        [
            {
                "id": "app.safe",
                "phrases": ["run safe"],
                "executor": "process",
                "arguments": {"argv": ["echo", "safe"], "cwd": str(tmp_path)},
                "approval": "preapproved",
                "risk": "low",
            }
        ],
    )
    reg = ActionRegistry(tmp_path)
    assert reg.reload()

    # Preapproval rule only allows echo safe
    rule = PreapprovalRule(
        id="echo-safe",
        executable="echo",
        argv_prefix=("safe",),
        working_roots=(str(tmp_path),),
        approval="preapproved",
        timeout_seconds=5,
        risk="low",
        network_allowed=True,
    )
    engine = PolicyEngine(preapproved_rules=[rule])
    mock_proc = MockExecutor()
    dispatcher = ActionDispatcher(policy_engine=engine, registry=reg, process_executor=mock_proc)

    # Attacker crafts an ActionRequest with id="app.safe" but dangerous arguments
    forged_req = ActionRequest(
        id="app.safe",
        tool="process.run",
        arguments={"argv": ["rm", "-rf", "/"], "cwd": "/"},
    )
    result = await dispatcher.dispatch_request(forged_req)
    assert not result.success
    assert len(mock_proc.calls) == 0


# ---------------------------------------------------------------------------
# REGISTRY & FRESHNESS TESTS
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_stale_registry_match_rejected(tmp_path):
    write_test_pack(
        tmp_path,
        "core",
        [
            {
                "id": "app.echo",
                "phrases": ["say {msg}"],
                "executor": "process",
                "arguments": {"argv": ["echo", "{msg}"], "cwd": str(tmp_path)},
                "approval": "preapproved",
                "risk": "low",
            }
        ],
    )
    reg = ActionRegistry(tmp_path)
    assert reg.reload()
    assert reg.snapshot_version == 1

    # Match obtained under snapshot version 1
    match = reg.resolve("say hello")
    assert match is not None
    assert match.snapshot_version == 1

    # Reload changes snapshot_version to 2
    assert reg.reload()
    assert reg.snapshot_version == 2

    engine = PolicyEngine()
    dispatcher = ActionDispatcher(policy_engine=engine, registry=reg)

    # Dispatching stale match from snapshot version 1 must be rejected
    result = await dispatcher.dispatch_match(match)
    assert not result.success
    assert "Stale RegistryMatch rejected" in result.error


# ---------------------------------------------------------------------------
# COMPOSITE ACTION TESTS
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_composite_every_child_passes_policy_and_stops_on_failure(tmp_path):
    # Pack with two steps: child1 (allowed), child2 (disallowed)
    write_test_pack(
        tmp_path,
        "core",
        [
            {
                "id": "app.step1",
                "phrases": ["step one"],
                "executor": "process",
                "arguments": {"argv": ["echo", "step1"], "cwd": str(tmp_path)},
                "approval": "preapproved",
                "risk": "low",
            },
            {
                "id": "app.step2",
                "phrases": ["step two"],
                "executor": "process",
                "arguments": {"argv": ["ls", "/root"], "cwd": str(tmp_path)},
                "approval": "preapproved",
                "risk": "low",
            },
            {
                "id": "app.composite",
                "phrases": ["run workflow"],
                "executor": "composite",
                "arguments": {"steps": ["app.step1", "app.step2"]},
                "approval": "preapproved",
                "risk": "low",
            },
        ],
    )
    reg = ActionRegistry(tmp_path)
    assert reg.reload()

    # Preapproval rule ONLY allows echo step1
    rule1 = PreapprovalRule(
        id="echo-step1",
        executable="echo",
        argv_prefix=("step1",),
        working_roots=(str(tmp_path),),
        approval="preapproved",
        timeout_seconds=5,
        risk="low",
        network_allowed=True,
    )
    engine = PolicyEngine(preapproved_rules=[rule1])
    mock_proc = MockExecutor()
    dispatcher = ActionDispatcher(policy_engine=engine, registry=reg, process_executor=mock_proc)

    match = reg.resolve("run workflow")
    assert match is not None
    result = await dispatcher.dispatch_match(match)
    # Composite must stop at step2 because step2 requires approval (no rule for ls)
    assert not result.success
    assert "Composite stopped at step 'app.step2'" in result.error
    # Only step1 was executed
    assert len(mock_proc.calls) == 1
    assert mock_proc.calls[0][0].id == "app.step1"


@pytest.mark.anyio
async def test_composite_disabled_child_blocked_at_runtime(tmp_path):
    write_test_pack(
        tmp_path,
        "core",
        [
            {
                "id": "app.step1",
                "phrases": ["step one"],
                "executor": "process",
                "arguments": {"argv": ["echo", "step1"], "cwd": str(tmp_path)},
                "approval": "preapproved",
                "risk": "low",
            },
            {
                "id": "app.comp",
                "phrases": ["run comp"],
                "executor": "composite",
                "arguments": {"steps": ["app.step1"]},
                "approval": "preapproved",
                "risk": "low",
            },
        ],
    )
    reg = ActionRegistry(tmp_path)
    assert reg.reload()

    # Simulate disabling step1 dynamically after snapshot
    reg._active_snapshot.actions["app.step1"] = ActionDefinition(
        id="app.step1",
        enabled=False,
        phrases=["step one"],
        executor="process",
        arguments={"argv": ["echo", "step1"], "cwd": str(tmp_path)},
        approval="preapproved",
        risk="low",
    )

    engine = PolicyEngine()
    dispatcher = ActionDispatcher(policy_engine=engine, registry=reg)
    match = reg.resolve("run comp")
    assert match is not None
    result = await dispatcher.dispatch_match(match)
    assert not result.success
    assert "is disabled" in result.error


# ---------------------------------------------------------------------------
# BROWSER STUB TESTS
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_browser_unavailable_bridge_fails_closed(tmp_path):
    engine = PolicyEngine()
    reg = ActionRegistry(tmp_path)
    assert reg.reload()

    # Dispatcher without browser bridge
    dispatcher = ActionDispatcher(policy_engine=engine, registry=reg, browser_bridge=None)

    req = ActionRequest(
        id="test.browser",
        tool="browser.open",
        arguments={"url": "https://google.com"},
    )
    # Policy for browser.open defaults to ASK_USER (so policy denies or requires approval)
    result = await dispatcher.dispatch_request(req)
    assert not result.success


# ---------------------------------------------------------------------------
# AUDIT EMISSION TESTS
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_audit_emission_metadata_only(tmp_path):
    events = []
    def audit_sink(event):
        events.append(event)

    rule = PreapprovalRule(
        id="echo-audit",
        executable="echo",
        argv_prefix=(),
        working_roots=(str(tmp_path),),
        approval="preapproved",
        timeout_seconds=5,
        risk="low",
        network_allowed=True,
    )
    engine = PolicyEngine(preapproved_rules=[rule])
    reg = ActionRegistry(tmp_path)
    assert reg.reload()
    mock_proc = MockExecutor()

    dispatcher = ActionDispatcher(
        policy_engine=engine,
        registry=reg,
        process_executor=mock_proc,
        audit_sink=audit_sink,
    )

    req = ActionRequest(
        id="test.audit",
        tool="process.run",
        arguments={"argv": ["echo", "hello"], "cwd": str(tmp_path)},
        request_id="req-123",
        agent_id="test-agent",
    )
    res = await dispatcher.dispatch_request(req)
    assert res.success

    assert len(events) == 1
    ev = events[0]
    assert ev["request_id"] == "req-123"
    assert ev["actor"] == "test-agent"
    assert ev["tool"] == "process.run"
    assert ev["policy_decision"] == PolicyDecision.ALLOW_PREAPPROVED.value
    assert ev["target"] == "echo"
    assert ev["result_code"] == 0
    assert "timestamp" in ev
    assert "duration" in ev
    # Verify no file contents or arbitrary inputs logged
    assert "arguments" not in ev
    assert "output" not in ev
