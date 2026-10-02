"""Policy foundation coverage; approval mutation regressions live in test_policy_contract."""

import pytest
from pydantic import ValidationError

from app.actions.schema import ActionRequest
from app.core.config import FileRootConfig
from app.policy.engine import PolicyDecision, PolicyEngine, PreapprovalRule
from app.policy.approvals import ApprovalRequest, hash_action, verify_action
from app.policy.risk import RiskLevel


def request(tool="process.run", arguments=None, **kwargs):
    return ActionRequest(id="test.action", tool=tool, arguments=arguments or {"argv": ["git", "status"]}, **kwargs)


def rule(**kwargs):
    return dict(id="git-status", executable="git", argv_prefix=["status"], working_roots=["/work"], approval="preapproved", timeout_seconds=30, risk="medium") | kwargs


def test_policy_decision_enum_states():
    assert {e.value for e in PolicyDecision} == {"ALLOW_PREAPPROVED", "ASK_USER", "DENY"}


def test_action_hash_deterministic():
    first = request(arguments={"b": 2, "a": {"z": 1, "y": 2}})
    second = request(arguments={"a": {"y": 2, "z": 1}, "b": 2})
    digest = hash_action(first)
    assert digest == hash_action(second)
    assert len(digest) == 64 and digest == digest.lower()
    assert verify_action(first, digest)
    assert verify_action(first, digest.upper())
    assert not verify_action(first, "0" * 64)
    assert not verify_action(first, "short")


@pytest.mark.parametrize("field,value", [("id", "other"), ("tool", "file.read"), ("arguments", {"argv": ["git", "diff"]}), ("workspace", "/other"), ("request_id", "other"), ("agent_id", "other"), ("reason", "other"), ("risk_hint", "high")])
def test_action_hash_sensitivity(field, value):
    base = request()
    changed = ActionRequest(**(base.model_dump() | {field: value}))
    assert not verify_action(changed, hash_action(base))


def test_approval_frozen_and_snapshot_immutable():
    proposed = request(reason="inspect")
    approval = ApprovalRequest.from_action(proposed, risk_level=RiskLevel.MEDIUM)
    with pytest.raises(ValidationError):
        approval.action_hash = "b" * 64
    proposed.arguments["argv"].append("--short")
    assert not verify_action(proposed, approval.action_hash)
    assert ActionRequest.model_validate_json(approval.action_snapshot).arguments == {"argv": ["git", "status"]}


@pytest.mark.parametrize("field", ["id", "executable", "argv_prefix", "working_roots", "approval", "timeout_seconds", "risk"])
def test_preapproval_requires_explicit_fields(field):
    payload = rule()
    PreapprovalRule(**payload)
    del payload[field]
    with pytest.raises(ValidationError) as exc:
        PreapprovalRule(**payload)
    assert exc.value.errors()[0]["loc"] == (field,)


@pytest.mark.parametrize("field,value", [("working_roots", []), ("timeout_seconds", 0), ("approval", "ask_user"), ("unknown", True)])
def test_preapproval_rejects_invalid_fields(field, value):
    payload = rule()
    PreapprovalRule(**payload)
    with pytest.raises(ValidationError):
        PreapprovalRule(**(payload | {field: value}))


@pytest.mark.parametrize("exe", ["sudo", "/usr/bin/sudo", "su", "doas", "pkexec", "env", "sh", "bash", "dash", "zsh", "fish", "apt", "apt-get", "dpkg", "dnf", "yum", "rpm", "snap", "flatpak", "systemctl", "service"])
def test_privilege_wrappers_require_approval(exe):
    with pytest.raises(ValidationError, match="cannot be preapproved"):
        PreapprovalRule(**rule(executable=exe))
    assert PolicyEngine().evaluate(request(arguments={"argv": [exe, "arg"]})) == PolicyDecision.ASK_USER


@pytest.mark.parametrize("arguments", [{}, {"executable": "git"}, {"argv": None}, {"argv": "git status"}, {"argv": []}, {"argv": [123]}, {"argv": [""]}, {"argv": ["git", 123]}, {"argv": ["git", "\x00"]}])
def test_malformed_argv_denied(arguments):
    proposed = ActionRequest(id="x", tool="process.run", arguments=arguments)
    assert PolicyEngine().evaluate(proposed) == PolicyDecision.DENY


@pytest.mark.parametrize("argv,cwd,want", [
    (["git", "status"], "/work/repo", PolicyDecision.ALLOW_PREAPPROVED),
    (["git", "diff"], "/work/repo", PolicyDecision.ASK_USER),
    (["git", "status"], "/work/../../other", PolicyDecision.ASK_USER),
    (["git", "status"], "/work-elsewhere", PolicyDecision.ASK_USER),
])
def test_structured_preapproval(argv, cwd, want):
    engine = PolicyEngine(preapproved_rules=[rule()])
    assert engine.evaluate(request(arguments={"argv": argv, "cwd": cwd})) == want


def test_workspace_fallback_and_missing_cwd():
    engine = PolicyEngine(preapproved_rules=[rule()])
    assert engine.evaluate(request(workspace="/work")) == PolicyDecision.ALLOW_PREAPPROVED
    assert engine.evaluate(request()) == PolicyDecision.ASK_USER


@pytest.mark.parametrize("tool", ["unknown.tool", "browser.evaluate"])
def test_unknown_tool_denied(tool):
    assert PolicyEngine().evaluate(request(tool)) == PolicyDecision.DENY


@pytest.mark.parametrize("tool,allowed", [("file.read", True), ("file.list", True), ("file.write", False), ("file.delete", False)])
def test_file_operation_permissions(tool, allowed, tmp_path):
    engine = PolicyEngine(allowed_file_roots=[FileRootConfig(path=str(tmp_path), read=True)])
    verdict = engine.evaluate(request(tool, {"path": str(tmp_path / "file")}))
    assert verdict == (PolicyDecision.ASK_USER if allowed else PolicyDecision.DENY)


def test_delete_remains_high_risk_with_permission(tmp_path):
    engine = PolicyEngine(allowed_file_roots=[FileRootConfig(path=str(tmp_path), delete=True)])
    assert engine.evaluate(request("file.delete", {"path": str(tmp_path / "file")}, risk_hint="low")) == PolicyDecision.ASK_USER


@pytest.mark.parametrize("path", ["/etc/passwd", "~/.ssh/id_rsa", "~/.ssh/../.ssh/id_rsa", "~/.gnupg/key", "~/.mozilla/profile", "~/.local/share/keyrings/login", "~/.config/project-h/config.toml", "/custom/file", "/tmp/.env", "/tmp/.env.local"])
def test_sensitive_defaults_cannot_be_overridden(path):
    engine = PolicyEngine(allowed_file_roots=[FileRootConfig(path="/", read=True, write=True, delete=True)], permanently_denied_paths=["/custom"])
    assert engine.evaluate(request("file.read", {"path": path})) == PolicyDecision.DENY


def test_raw_roots_and_malformed_rules_rejected():
    with pytest.raises(ValueError):
        PolicyEngine(allowed_file_roots=["/work"])
    with pytest.raises(ValidationError):
        PolicyEngine(preapproved_rules=[{"tool": "process.run"}])


def test_file_symlink_and_parent_escape(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "link").symlink_to(tmp_path, target_is_directory=True)
    engine = PolicyEngine(allowed_file_roots=[FileRootConfig(path=str(root), read=True)])
    for path in [root / "link" / "outside", root / ".." / "outside"]:
        assert engine.evaluate(request("file.read", {"path": str(path)})) == PolicyDecision.DENY
