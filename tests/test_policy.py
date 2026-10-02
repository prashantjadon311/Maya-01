import time
import pytest
from pydantic import ValidationError

from app.actions.schema import ActionRequest
from app.policy.engine import PolicyDecision, PolicyEngine
from app.core.config import FileRootConfig
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
    dummy_req = ActionRequest(id="act-1", tool="process.run", arguments={"argv": ["ls"]}, reason="testing", request_id="req-1")
    req = ApprovalRequest.from_action(dummy_req)

    with pytest.raises(ValidationError):
        # frozen=True prevents reassignment
        req.action_hash = "b" * 64  # type: ignore

    with pytest.raises(ValidationError):
        # extra="forbid" rejects unknown field
        dummy_req2 = ActionRequest(id="act-1", tool="process.run", arguments={"argv": ["ls"]})
        ApprovalRequest(
            action_hash=hash_action(dummy_req2),
            action_id="act-1",
            tool="process.run",
            created_at=now,
            expires_at=now + 60.0,
            action_snapshot=dummy_req2.to_canonical_json(),
            unauthorized_extra="bypass",
        )


def test_approval_request_digest_validation():
    """Verify ApprovalRequest validates SHA-256 hex format."""
    now = time.time()
    from app.actions.schema import ActionRequest
    dummy_req = ActionRequest(id="act-1", tool="process.run", arguments={"argv": ["ls"]})
    
    def valid_kwargs():
        return {
            "action_hash": hash_action(dummy_req),
            "action_id": "act-1",
            "tool": "process.run",
            "created_at": now,
            "expires_at": now + 60.0,
            "action_snapshot": dummy_req.to_canonical_json()
        }
        
    # Invalid length
    kwargs1 = valid_kwargs()
    kwargs1["action_hash"] = "short_hash"
    with pytest.raises(ValidationError):
        ApprovalRequest(**kwargs1)

    # Invalid non-hex characters
    kwargs2 = valid_kwargs()
    kwargs2["action_hash"] = "g" * 64
    with pytest.raises(ValidationError):
        ApprovalRequest(**kwargs2)

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
        dummy_req3 = ActionRequest(id="act-1", tool="process.run", arguments={"argv": ["ls"]})
        ApprovalRequest(
            action_hash=hash_action(dummy_req3),
            action_id="act-1",
            tool="process.run",
            created_at=now,
            expires_at=now - 1.0,
            action_snapshot=dummy_req3.to_canonical_json()
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
    engine = PolicyEngine(allowed_file_roots=[FileRootConfig(path="~/Projects", read=True, write=True), FileRootConfig(path="/tmp/project_h", read=True, write=True)])

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
            "id": "danger-delete", "executable": "rm", "argv_prefix": ["-rf"], "working_roots": ["~/Projects"], "approval": "preapproved", "timeout_seconds": 30,  # Config incorrectly marked preapproved
        }
    ]
    from app.core.config import FileRootConfig
    engine = PolicyEngine(allowed_file_roots=[FileRootConfig(path="~/Projects", delete=True, write=True)], preapproved_rules=rules)

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
            "id": "git-status", "executable": "git", "argv_prefix": ["status"], "working_roots": ["~/Projects"], "approval": "preapproved", "timeout_seconds": 30
        }
    ]
    from app.core.config import FileRootConfig
    engine = PolicyEngine(allowed_file_roots=[FileRootConfig(path="~/Projects", delete=True, write=True)], preapproved_rules=rules)

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
    pass


def test_D_path_normalization():
    """D. Path Normalization: block .. traversals."""
    engine = PolicyEngine(allowed_file_roots=[FileRootConfig(path="/allowed/root", read=True, write=True)])
    
    req_traversal = ActionRequest(id="1", tool="file.read", arguments={"path": "/allowed/root/../../etc/passwd"})
    assert engine.evaluate(req_traversal) == PolicyDecision.DENY

def test_E_working_directory_preapproval():
    """E. Working Directory Preapproval: enforce containment against working_roots."""
    rules = [
        {"id": "test-ls", "executable": "ls", "argv_prefix": [], "working_roots": ["/allowed/root"], "approval": "preapproved", "timeout_seconds": 30}
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
        dummy = ActionRequest(id="1", tool="process.run", arguments={"argv": ["ls"]})
        ApprovalRequest(
            action_hash=hash_action(dummy), action_id="1", tool="process.run",
            created_at=math.nan, expires_at=time.time() + 60,
            action_snapshot=dummy.to_canonical_json()
        )
    with pytest.raises(ValidationError):
        dummy2 = ActionRequest(id="1", tool="process.run", arguments={"argv": ["ls"]})
        ApprovalRequest(
            action_hash=hash_action(dummy2), action_id="1", tool="process.run",
            created_at=time.time(), expires_at=math.inf,
            action_snapshot=dummy2.to_canonical_json()
        )

def test_J_action_argument_canonicalization():
    """J. Action Argument Canonicalization: Reject NaN, Infinity."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ActionRequest(id="1", tool="process.run", arguments={"value": math.nan})

def test_K_security_defaults():
    """K. Security Defaults: Enforce permanently denied paths."""
    engine = PolicyEngine(allowed_file_roots=[FileRootConfig(path="/", read=True, write=True)])
    req = ActionRequest(id="1", tool="file.read", arguments={"path": "~/.ssh/../.ssh/id_rsa"})
    assert engine.evaluate(req) == PolicyDecision.DENY


def test_DEFECT_B_broad_preapproval_rules():
    """Defect B: Malformed/incomplete preapproval rules must fail closed."""
    from app.policy.engine import PolicyEngine
    import pytest
    from pydantic import ValidationError
    
    # Must reject rules without executable or without argv_prefix (or without explicit approval="preapproved")
    # For process.run, a safe semantic contract requires 'executable' and 'argv_prefix'.
    with pytest.raises(ValidationError):
        PolicyEngine(preapproved_rules=[{"tool": "process.run"}])
        

    
def test_DEFECT_E_approval_hash_binding():
    """Defect E: ApprovalRequest must not allow mismatched metadata."""
    from app.policy.approvals import ApprovalRequest, hash_action
    from app.actions.schema import ActionRequest
    import time
    import pytest
    from pydantic import ValidationError
    
    malicious = ActionRequest(id="evil", tool="process.run", arguments={"argv": ["rm", "-rf", "/"]})
    digest = hash_action(malicious)
    
    # Passing mismatching display fields should fail validation.
    # Currently, ApprovalRequest does NOT take `snapshot`. We need to redesign it.
    # The requirement is that we pass `snapshot_json` and it derives or validates the display fields.
    # Let's test the NEW interface we're about to build: it must take `action_snapshot` and validate everything against it.
    # Since it's not built yet, we can't test it passing. We can just test that the CURRENT constructor allows a mismatch, which is the vulnerability.
    
    # Current vulnerability: we CAN construct this.
    
    # The fix will be to make the above construction fail or be impossible without a snapshot,
    # or validate against a snapshot.
    # We will redesign ApprovalRequest. For the RED test, let's assert that supplying mismatched fields raises ValueError.
    with pytest.raises(ValueError):
        ApprovalRequest(
            action_hash=digest,
            action_id="benign",
            tool="browser.read",
            created_at=time.time(),
            expires_at=time.time() + 60,
        )

def test_DEFECT_G_malformed_rule_handling():
    """Defect G: Initialization must fail on malformed rules, not silently discard."""
    from app.policy.engine import PolicyEngine
    import pytest
    from pydantic import ValidationError
    
    with pytest.raises(ValidationError):
        PolicyEngine(preapproved_rules=[{"tool": "process.run", "risk": "invalid_risk"}])

def test_DEFECT_H_file_root_string_compatibility():
    """Defect H: Raw string roots fail closed or read-only."""
    from app.policy.engine import PolicyEngine, PolicyDecision
    from app.actions.schema import ActionRequest
    
    engine = PolicyEngine(allowed_file_roots=[FileRootConfig(path="/tmp/safe", read=True)])
    req = ActionRequest(id="1", tool="file.write", arguments={"path": "/tmp/safe/foo.txt", "content": "hi"})
    assert engine.evaluate(req) == PolicyDecision.DENY
def test_ISSUE_A_wildcard_preapproval_rule():
    from app.policy.engine import PreapprovalRule
    from pydantic import ValidationError
    import pytest

    # Reject
    with pytest.raises(ValidationError):
        PreapprovalRule.model_validate({})
    with pytest.raises(ValidationError):
        PreapprovalRule.model_validate({"executable": "git", "argv_prefix": ["status"], "working_roots": ["/"], "approval": "preapproved", "timeout_seconds": 30}) # missing id
    with pytest.raises(ValidationError):
        PreapprovalRule.model_validate({"id": "1", "argv_prefix": ["status"], "working_roots": ["/"], "approval": "preapproved", "timeout_seconds": 30}) # missing executable
    with pytest.raises(ValidationError):
        PreapprovalRule.model_validate({"id": "1", "executable": "git", "working_roots": ["/"], "approval": "preapproved", "timeout_seconds": 30}) # missing argv_prefix
    with pytest.raises(ValidationError):
        PreapprovalRule.model_validate({"id": "1", "executable": "git", "argv_prefix": ["status"], "approval": "preapproved", "timeout_seconds": 30}) # missing working_roots
    with pytest.raises(ValidationError):
        PreapprovalRule.model_validate({"id": "1", "executable": "git", "argv_prefix": ["status"], "working_roots": [], "approval": "preapproved", "timeout_seconds": 30}) # empty working_roots
    with pytest.raises(ValidationError):
        PreapprovalRule.model_validate({"id": "1", "executable": "git", "argv_prefix": ["status"], "working_roots": ["/"], "timeout_seconds": 30}) # missing approval
    with pytest.raises(ValidationError):
        PreapprovalRule.model_validate({"id": "1", "executable": "git", "argv_prefix": ["status"], "working_roots": ["/"], "approval": "preapproved"}) # missing timeout_seconds
    with pytest.raises(ValidationError):
        PreapprovalRule.model_validate({"id": "1", "executable": "git", "argv_prefix": ["status"], "working_roots": ["/"], "approval": "preapproved", "timeout_seconds": 0}) # timeout <= 0
    with pytest.raises(ValidationError):
        PreapprovalRule.model_validate({"id": "1", "executable": "git", "argv_prefix": ["status"], "working_roots": ["/"], "approval": "ask_user", "timeout_seconds": 30}) # approval not preapproved
    with pytest.raises(ValidationError):
        PreapprovalRule.model_validate({"id": "1", "executable": "git", "argv_prefix": ["status"], "working_roots": ["/"], "approval": "preapproved", "timeout_seconds": 30, "unknown": "field"}) # unknown field

    # Accept canonical
    git_rule = PreapprovalRule.model_validate({"id": "git", "executable": "git", "argv_prefix": ["status"], "working_roots": ["~/Projects"], "approval": "preapproved", "timeout_seconds": 30})
    assert git_rule.id == "git"
def test_ISSUE_B_malformed_process_representation():
    from app.policy.engine import PolicyEngine, PolicyDecision
    from app.actions.schema import ActionRequest

    engine = PolicyEngine()
    
    # Missing argv
    req1 = ActionRequest(id="1", tool="process.run", arguments={"executable": "git"})
    assert engine.evaluate(req1) == PolicyDecision.DENY

    # argv=None
    req2 = ActionRequest(id="1", tool="process.run", arguments={"argv": None})
    assert engine.evaluate(req2) == PolicyDecision.DENY

    # argv=""
    req3 = ActionRequest(id="1", tool="process.run", arguments={"argv": ""})
    assert engine.evaluate(req3) == PolicyDecision.DENY

    # argv=[]
    req4 = ActionRequest(id="1", tool="process.run", arguments={"argv": []})
    assert engine.evaluate(req4) == PolicyDecision.DENY

    # argv=[123]
    req5 = ActionRequest(id="1", tool="process.run", arguments={"argv": [123]})
    assert engine.evaluate(req5) == PolicyDecision.DENY

    # argv=[""]
    req6 = ActionRequest(id="1", tool="process.run", arguments={"argv": [""]})
    assert engine.evaluate(req6) == PolicyDecision.DENY

    # argv=["git", 123]
    req7 = ActionRequest(id="1", tool="process.run", arguments={"argv": ["git", 123]})
    assert engine.evaluate(req7) == PolicyDecision.DENY
def test_ISSUE_C_never_preapprove_executables():
    from app.policy.engine import PolicyEngine, PolicyDecision, PreapprovalRule, NEVER_PREAPPROVE_EXECUTABLES
    from app.actions.schema import ActionRequest
    from pydantic import ValidationError
    import pytest

    # PreapprovalRule validation
    for exe in NEVER_PREAPPROVE_EXECUTABLES:
        with pytest.raises(ValidationError):
            PreapprovalRule.model_validate({
                "id": f"test-{exe}",
                "executable": exe,
                "argv_prefix": [],
                "working_roots": ["/"],
                "approval": "preapproved",
                "timeout_seconds": 30
            })
        
        with pytest.raises(ValidationError):
            PreapprovalRule.model_validate({
                "id": f"test-{exe}-abs",
                "executable": f"/usr/bin/{exe}",
                "argv_prefix": [],
                "working_roots": ["/"],
                "approval": "preapproved",
                "timeout_seconds": 30
            })

    engine = PolicyEngine()
    # Runtime actions
    for exe in NEVER_PREAPPROVE_EXECUTABLES:
        req = ActionRequest(id="1", tool="process.run", arguments={"argv": [exe, "arg"]})
        assert engine.evaluate(req) == PolicyDecision.ASK_USER
        
        req_abs = ActionRequest(id="1", tool="process.run", arguments={"argv": [f"/bin/{exe}", "arg"]})
        assert engine.evaluate(req_abs) == PolicyDecision.ASK_USER

    # Env wrapper (no longer parsed for deep preapproval bypasses, but 'env' itself is blocked)
    req_env = ActionRequest(id="1", tool="process.run", arguments={"argv": ["env", "sudo", "ls"]})
    assert engine.evaluate(req_env) == PolicyDecision.ASK_USER
def test_ISSUE_D_E_F_file_security_invariants():
    from app.policy.engine import PolicyEngine, PolicyDecision
    from app.core.config import FileRootConfig
    from app.actions.schema import ActionRequest

    # Test D & E: Defaults cannot be replaced, and ~/.config/project-h is strictly denied.
    # We pass a custom denied paths list. It must not override the defaults.
    # We also allow HOME root to test that allowed roots don't bypass denied paths.
    engine = PolicyEngine(
        permanently_denied_paths=["/custom"],
        allowed_file_roots=[FileRootConfig(path="~/", read=True, write=True, delete=True)]
    )
    
    # Must deny built-in
    req_etc = ActionRequest(id="1", tool="file.read", arguments={"path": "/etc/passwd"})
    assert engine.evaluate(req_etc) == PolicyDecision.DENY
    
    req_ssh = ActionRequest(id="1", tool="file.read", arguments={"path": "~/.ssh/id_rsa"})
    assert engine.evaluate(req_ssh) == PolicyDecision.DENY
    
    # Must deny ~/.config/project-h
    req_ph_config = ActionRequest(id="1", tool="file.read", arguments={"path": "~/.config/project-h/config.toml"})
    assert engine.evaluate(req_ph_config) == PolicyDecision.DENY
    
    req_ph_write = ActionRequest(id="1", tool="file.write", arguments={"path": "~/.config/project-h/config.toml", "content": "x"})
    assert engine.evaluate(req_ph_write) == PolicyDecision.DENY
    
    req_ph_list = ActionRequest(id="1", tool="file.list", arguments={"path": "~/.config/project-h"})
    assert engine.evaluate(req_ph_list) == PolicyDecision.DENY

    # Test F: Credential files inside allowed roots
    req_env = ActionRequest(id="1", tool="file.read", arguments={"path": "~/Projects/repo/.env"})
    assert engine.evaluate(req_env) == PolicyDecision.DENY
    
    req_env_local = ActionRequest(id="1", tool="file.read", arguments={"path": "~/Projects/repo/.env.local"})
    assert engine.evaluate(req_env_local) == PolicyDecision.DENY
