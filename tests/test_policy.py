import time
import pytest
from pydantic import ValidationError

from app.actions.schema import ActionRequest
from app.policy.engine import PolicyDecision, PolicyEngine
from app.policy.approvals import ApprovalRequest, hash_action, verify_action


def test_policy_decision_enum_states():
    """Verify PolicyDecision has exactly three distinct states and no implicit fourth."""
    states = [e.value for e in PolicyDecision]
    assert len(states) == 3
    assert "ALLOW_PREAPPROVED" in states
    assert "ASK_USER" in states
    assert "DENY" in states


def test_action_hash_deterministic():
    """Verify hash_action produces consistent SHA-256 lowercase hex regardless of dict key order."""
    req1 = ActionRequest(
        id="act-1",
        tool="process.run",
        arguments={"b_key": 2, "a_key": 1, "nested": {"y": 20, "x": 10}},
        reason="test",
        request_id="req-1",
        workspace="/tmp",
    )
    req2 = ActionRequest(
        id="act-1",
        tool="process.run",
        arguments={"a_key": 1, "nested": {"x": 10, "y": 20}, "b_key": 2},
        reason="test",
        request_id="req-1",
        workspace="/tmp",
    )

    digest1 = hash_action(req1)
    digest2 = hash_action(req2)
    assert digest1 == digest2
    assert len(digest1) == 64
    assert digest1.lower() == digest1
    assert verify_action(req1, digest1) is True


def test_action_hash_sensitivity():
    """Verify changing any security-relevant field changes the SHA-256 digest."""
    base = ActionRequest(
        id="act-1",
        tool="process.run",
        arguments={"argv": ["git", "status"]},
        reason="check git",
        request_id="req-1",
        workspace="/home/user/project",
        agent_id="agent-1",
    )
    base_digest = hash_action(base)

    # Tool change
    diff_tool = base.model_copy(update={"tool": "process.exec"})
    assert hash_action(diff_tool) != base_digest
    assert verify_action(diff_tool, base_digest) is False

    # Arguments change
    diff_args = base.model_copy(update={"arguments": {"argv": ["git", "diff"]}})
    assert hash_action(diff_args) != base_digest

    # Workspace change
    diff_workspace = base.model_copy(update={"workspace": "/etc"})
    assert hash_action(diff_workspace) != base_digest

    # Request ID change
    diff_req = base.model_copy(update={"request_id": "req-2"})
    assert hash_action(diff_req) != base_digest

    # Agent ID change
    diff_agent = base.model_copy(update={"agent_id": "agent-2"})
    assert hash_action(diff_agent) != base_digest


def test_approval_request_strict_and_frozen():
    """Verify ApprovalRequest rejects extra fields and attribute reassignments."""
    now = time.time()
    req = ApprovalRequest(
        action_hash="a" * 64,
        action_id="act-1",
        tool="process.run",
        created_at=now,
        expires_at=now + 60.0,
        reason="testing",
        request_id="req-1",
    )

    with pytest.raises(ValidationError):
        # frozen=True prevents reassignment
        req.action_hash = "b" * 64  # type: ignore

    with pytest.raises(ValidationError):
        # extra="forbid" rejects unknown field
        ApprovalRequest(
            action_hash="a" * 64,
            action_id="act-1",
            tool="process.run",
            created_at=now,
            expires_at=now + 60.0,
            unauthorized_extra="bypass",
        )


def test_approval_request_digest_validation():
    """Verify ApprovalRequest validates SHA-256 hex format."""
    now = time.time()
    # Invalid length
    with pytest.raises(ValidationError):
        ApprovalRequest(
            action_hash="short_hash",
            action_id="act-1",
            tool="process.run",
            created_at=now,
            expires_at=now + 60.0,
        )

    # Invalid non-hex characters
    with pytest.raises(ValidationError):
        ApprovalRequest(
            action_hash="g" * 64,
            action_id="act-1",
            tool="process.run",
            created_at=now,
            expires_at=now + 60.0,
        )

    # Invalid expiry (expires_at <= created_at)
    with pytest.raises(ValidationError):
        ApprovalRequest(
            action_hash="a" * 64,
            action_id="act-1",
            tool="process.run",
            created_at=now,
            expires_at=now - 1.0,
        )


def test_policy_sudo_requires_ask_user():
    """Privileged / sudo command must resolve to ASK_USER (never ALLOW_PREAPPROVED, not DENY)."""
    engine = PolicyEngine()

    sudo_apt = ActionRequest(
        id="act-1",
        tool="process.run",
        arguments={"argv": ["sudo", "apt", "update"]},
        reason="install security updates",
        request_id="req-1",
    )
    decision = engine.evaluate(sudo_apt)
    assert decision == PolicyDecision.ASK_USER
    assert decision != PolicyDecision.ALLOW_PREAPPROVED
    assert decision != PolicyDecision.DENY

    sudo_systemctl = ActionRequest(
        id="act-2",
        tool="process.run",
        arguments={"argv": ["sudo", "systemctl", "restart", "nginx"]},
        reason="restart webserver",
        request_id="req-2",
    )
    assert engine.evaluate(sudo_systemctl) == PolicyDecision.ASK_USER


def test_policy_file_outside_allowed_root_denied():
    """Targeting files outside configured roots must resolve to DENY."""
    engine = PolicyEngine(allowed_file_roots=["~/Projects", "/tmp/project_h"])

    outside_action = ActionRequest(
        id="act-3",
        tool="file.read",
        arguments={"path": "/etc/shadow"},
        reason="read credentials",
        request_id="req-3",
    )
    assert engine.evaluate(outside_action) == PolicyDecision.DENY

    outside_home = ActionRequest(
        id="act-4",
        tool="file.write",
        arguments={"path": "~/.ssh/authorized_keys", "content": "key"},
        reason="modify ssh keys",
        request_id="req-4",
    )
    assert engine.evaluate(outside_home) == PolicyDecision.DENY


def test_policy_high_risk_never_preapproved():
    """High-risk action must never be ALLOW_PREAPPROVED in V1."""
    rules = [
        {
            "id": "danger-delete",
            "tool": "file.delete",
            "working_roots": ["~/Projects"],
            "risk": "high",
            "approval": "preapproved",  # Config incorrectly marked preapproved
        }
    ]
    engine = PolicyEngine(allowed_file_roots=["~/Projects"], preapproved_rules=rules)

    high_risk_action = ActionRequest(
        id="act-5",
        tool="file.delete",
        arguments={"path": "~/Projects/repo/old.py"},
        reason="delete file",
        risk_hint="high",
        request_id="req-5",
    )
    decision = engine.evaluate(high_risk_action)
    assert decision != PolicyDecision.ALLOW_PREAPPROVED
    assert decision == PolicyDecision.ASK_USER


def test_policy_structured_preapproval_allow():
    """Preapproval succeeds only when structured rules match."""
    rules = [
        {
            "id": "git-status",
            "tool": "process.run",
            "executable": "git",
            "argv_prefix": ["status"],
            "working_roots": ["~/Projects"],
            "risk": "low",
        }
    ]
    engine = PolicyEngine(allowed_file_roots=["~/Projects"], preapproved_rules=rules)

    matching_action = ActionRequest(
        id="act-6",
        tool="process.run",
        arguments={"argv": ["git", "status"], "cwd": "~/Projects/my_repo"},
        reason="check status",
        workspace="~/Projects/my_repo",
        request_id="req-6",
    )
    assert engine.evaluate(matching_action) == PolicyDecision.ALLOW_PREAPPROVED

    # Non-matching arguments cannot preapprove -> ASK_USER
    non_matching = ActionRequest(
        id="act-7",
        tool="process.run",
        arguments={"argv": ["git", "push", "--force"], "cwd": "~/Projects/my_repo"},
        reason="force push",
        workspace="~/Projects/my_repo",
        request_id="req-7",
    )
    assert engine.evaluate(non_matching) == PolicyDecision.ASK_USER


def test_policy_unknown_tool_fails_closed():
    """Unknown or unsupported tools fail closed (DENY)."""
    engine = PolicyEngine()
    unknown_action = ActionRequest(
        id="act-8",
        tool="unknown.unsupported.tool",
        arguments={"param": "value"},
        reason="unknown",
        request_id="req-8",
    )
    assert engine.evaluate(unknown_action) == PolicyDecision.DENY

import math

def test_A_preapproval_rule_validation():
    """A. PreapprovalRule model validation."""
    from app.policy.engine import PreapprovalRule
    
    # Should forbid extra fields
    with pytest.raises(ValidationError):
        PreapprovalRule(tool="process.run", extra_field="bad")

def test_B_trusted_risk_classification():
    """B. Trusted Risk Classification: PolicyEngine must prevent privileged categories from being preapproved."""
    rules = [
        {"tool": "process.run", "executable": "apt", "argv_prefix": ["install"], "risk": "low"}
    ]
    # The rules above should either fail to parse or be ignored.
    # We will test the evaluation side.
    engine = PolicyEngine(preapproved_rules=rules)
    
    req_apt = ActionRequest(id="1", tool="process.run", arguments={"argv": ["apt", "install", "nmap"]})
    assert engine.evaluate(req_apt) == PolicyDecision.ASK_USER
    
    req_systemctl = ActionRequest(id="2", tool="process.run", arguments={"argv": ["systemctl", "restart"]})
    assert engine.evaluate(req_systemctl) == PolicyDecision.ASK_USER

def test_C_privilege_bypass_forms():
    """C. Sudo / Privilege Bypass Forms."""
    rules = [
        {"tool": "process.run", "executable": "env", "risk": "low"},
        {"tool": "process.run", "executable": "pkexec", "risk": "low"},
        {"tool": "process.run", "executable": "su", "risk": "low"},
        {"tool": "process.run", "executable": "doas", "risk": "low"}
    ]
    engine = PolicyEngine(preapproved_rules=rules)
    req_env_sudo = ActionRequest(id="1", tool="process.run", arguments={"argv": ["env", "sudo", "rm", "-rf", "/"]})
    assert engine.evaluate(req_env_sudo) == PolicyDecision.ASK_USER

    req_pkexec = ActionRequest(id="2", tool="process.run", arguments={"argv": ["pkexec", "bash"]})
    assert engine.evaluate(req_pkexec) == PolicyDecision.ASK_USER

    req_su = ActionRequest(id="3", tool="process.run", arguments={"argv": ["su", "-"]})
    assert engine.evaluate(req_su) == PolicyDecision.ASK_USER

    req_doas = ActionRequest(id="4", tool="process.run", arguments={"argv": ["doas", "apt"]})
    assert engine.evaluate(req_doas) == PolicyDecision.ASK_USER

def test_D_path_normalization():
    """D. Path Normalization: block .. traversals."""
    engine = PolicyEngine(allowed_file_roots=["/allowed/root"])
    
    req_traversal = ActionRequest(id="1", tool="file.read", arguments={"path": "/allowed/root/../../etc/passwd"})
    assert engine.evaluate(req_traversal) == PolicyDecision.DENY

def test_E_working_directory_preapproval():
    """E. Working Directory Preapproval: enforce containment against working_roots."""
    rules = [
        {"tool": "process.run", "executable": "ls", "working_roots": ["/allowed/root"]}
    ]
    engine = PolicyEngine(preapproved_rules=rules)
    
    req_bad_cwd = ActionRequest(
        id="1", tool="process.run", 
        arguments={"argv": ["ls"], "cwd": "/allowed/root/../../etc"}
    )
    assert engine.evaluate(req_bad_cwd) == PolicyDecision.ASK_USER

def test_F_file_root_operation_permissions():
    """F. File Root Operation Permissions: independently enforce read/write/delete booleans."""
    from app.core.config import FileRootConfig
    
    roots = [FileRootConfig(path="/safe", read=True, write=False, delete=False)]
    # We pass allowed_file_roots directly to PolicyEngine or modify PolicyEngine to accept FileRootConfig
    # For now, let's assume PolicyEngine accepts FileRootConfig objects directly.
    engine = PolicyEngine(allowed_file_roots=roots)
    
    req_write = ActionRequest(id="1", tool="file.write", arguments={"path": "/safe/file.txt", "content": "hello"})
    assert engine.evaluate(req_write) == PolicyDecision.DENY
    
    req_delete = ActionRequest(id="2", tool="file.delete", arguments={"path": "/safe/file.txt"})
    assert engine.evaluate(req_delete) == PolicyDecision.DENY

def test_G_approval_display_hash_binding():
    """G. Approval Display/Hash Binding: implement from_action."""
    req = ActionRequest(id="1", tool="process.run", arguments={"argv": ["ls"]}, reason="test")
    # Should be created via from_action
    approval = ApprovalRequest.from_action(req, expires_in=60.0)
    assert approval.action_hash == hash_action(req)
    assert approval.tool == req.tool
    assert approval.action_id == req.id

def test_H_hash_verification():
    """H. Hash Verification: securely compare digests."""
    req = ActionRequest(id="1", tool="process.run", arguments={"argv": ["ls"]})
    digest = hash_action(req)
    
    # Using verify_action which should use hmac.compare_digest
    assert verify_action(req, digest) is True
    assert verify_action(req, "a" * 64) is False

def test_I_timestamp_validation():
    """I. Timestamp Validation: Reject NaN, inf, -inf."""
    with pytest.raises(ValidationError):
        ApprovalRequest(
            action_hash="a" * 64, action_id="1", tool="process.run",
            created_at=math.nan, expires_at=time.time() + 60
        )
    with pytest.raises(ValidationError):
        ApprovalRequest(
            action_hash="a" * 64, action_id="1", tool="process.run",
            created_at=time.time(), expires_at=math.inf
        )

def test_J_action_argument_canonicalization():
    """J. Action Argument Canonicalization: Reject NaN, Infinity."""
    # JSON doesn't strictly support NaN/Infinity in strict mode without allow_nan=False
    req = ActionRequest(id="1", tool="process.run", arguments={"value": math.nan})
    with pytest.raises(ValueError):
        req.to_canonical_json()

def test_K_security_defaults():
    """K. Security Defaults: Enforce permanently denied paths."""
    engine = PolicyEngine(allowed_file_roots=["/"])
    req = ActionRequest(id="1", tool="file.read", arguments={"path": "~/.ssh/../.ssh/id_rsa"})
    assert engine.evaluate(req) == PolicyDecision.DENY
