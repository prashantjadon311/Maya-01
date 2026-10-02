"""Security regressions derived from the product contract."""

import math

import pytest
from pydantic import ValidationError

from app.actions.schema import ActionRequest
from app.core.config import FileRootConfig
from app.policy.engine import PolicyDecision, PolicyEngine, PreapprovalRule
from app.policy.approvals import ApprovalRequest, hash_action, verify_action


def rule_data(**overrides):
    return dict(id="git-status", executable="git", argv_prefix=["status"],
                working_roots=["/work"], approval="preapproved", timeout_seconds=30,
                risk="medium") | overrides


def action(tool="process.run", arguments=None, **overrides):
    return ActionRequest(id="test.action", tool=tool,
                         arguments=arguments if arguments is not None else {"argv": ["git", "status"], "cwd": "/work"},
                         **overrides)


@pytest.mark.parametrize("tool,arguments,expected", [
    ("app.open", {}, "LOW"), ("file.read", {}, "LOW"), ("file.list", {}, "LOW"),
    ("browser.open", {}, "LOW"), ("browser.read", {}, "LOW"),
    ("file.write", {}, "MEDIUM"), ("browser.click", {}, "MEDIUM"),
    ("browser.type", {}, "MEDIUM"), ("task.create", {}, "MEDIUM"),
    ("process.run", {"argv": ["pytest"]}, "MEDIUM"),
    ("file.delete", {}, "HIGH"), ("process.run", {"argv": ["sudo", "ls"]}, "HIGH"),
    ("process.run", {"argv": ["apt", "install", "x"]}, "HIGH"),
    ("process.run", {"argv": ["systemctl", "stop", "x"]}, "HIGH"),
])
def test_trusted_risk(tool, arguments, expected):
    assert PolicyEngine().assess_risk(action(tool, arguments)).value == expected


@pytest.mark.parametrize("hint,expected", [("low", "HIGH"), ("HIGH", "HIGH"), ("critical", "CRITICAL")])
def test_hint_cannot_lower_trusted_risk(hint, expected):
    assert PolicyEngine().assess_risk(action("file.delete", {}, risk_hint=hint)).value == expected


@pytest.mark.parametrize("hint", ["high", "HIGH", "critical", "CRITICAL"])
def test_hint_raises_risk_and_prevents_preapproval(hint):
    engine = PolicyEngine(preapproved_rules=[rule_data()])
    assert engine.evaluate(action(risk_hint=hint)) == PolicyDecision.ASK_USER


DANGEROUS = "rm rmdir unlink shred chmod chown chgrp dd mkfs mount umount shutdown reboot poweroff useradd userdel usermod groupadd groupdel passwd kill pkill killall iptables nft ufw".split()


@pytest.mark.parametrize("executable", DANGEROUS)
@pytest.mark.parametrize("prefix", ["", "/usr/bin/"])
def test_destructive_executables_never_preapproved(executable, prefix):
    executable = prefix + executable
    with pytest.raises(ValidationError, match="cannot be preapproved"):
        PreapprovalRule(**rule_data(executable=executable))
    request = action(arguments={"argv": [executable], "cwd": "/work"}, risk_hint="low")
    assert PolicyEngine().evaluate(request) == PolicyDecision.ASK_USER
    assert PolicyEngine().assess_risk(request).value == "HIGH"


def test_preapproval_contract():
    rule = PreapprovalRule(**rule_data(env_allowlist=["LANG"], network_allowed=True))
    assert rule.risk == "medium"
    assert rule.env_allowlist == ("LANG",)
    assert rule.network_allowed is True
    defaults = PreapprovalRule(**rule_data())
    assert defaults.env_allowlist == () and defaults.network_allowed is False


@pytest.mark.parametrize("field,value", [("risk", "high"), ("risk", "critical"), ("id", " "), ("executable", " "), ("working_roots", [""]), ("timeout_seconds", 1.5), ("network_allowed", "false")])
def test_invalid_preapproval_values(field, value):
    baseline = rule_data()
    PreapprovalRule(**baseline)
    baseline[field] = value
    with pytest.raises(ValidationError):
        PreapprovalRule(**baseline)


def test_cwd_symlink_escape(tmp_path):
    inside = tmp_path / "inside"
    outside = tmp_path / "outside"
    inside.mkdir()
    outside.mkdir()
    (inside / "escape").symlink_to(outside, target_is_directory=True)
    legacy_rule = rule_data(working_roots=[str(inside)])
    engine = PolicyEngine(preapproved_rules=[legacy_rule])
    assert engine.evaluate(action(arguments={"argv": ["git", "status"], "cwd": str(inside / "escape")})) == PolicyDecision.ASK_USER


@pytest.mark.parametrize("cwd", [123, [], {}, False, None, "", " "])
def test_malformed_explicit_cwd_denied(cwd):
    assert PolicyEngine().evaluate(action(arguments={"argv": ["git", "status"], "cwd": cwd}, workspace="/work")) == PolicyDecision.DENY


@pytest.mark.parametrize("path", [123, ["/tmp"], {"path": "/tmp"}, True, None, "", " "])
def test_malformed_file_path_denied(path):
    engine = PolicyEngine(allowed_file_roots=[FileRootConfig(path="/", read=True)])
    assert engine.evaluate(action("file.read", {"path": path})) == PolicyDecision.DENY


def test_approval_requires_explicit_trusted_risk():
    with pytest.raises(TypeError):
        ApprovalRequest.from_action(action(risk_hint="low"))


def test_approval_stores_trusted_risk():
    from app.policy.risk import RiskLevel
    request = action(risk_hint="low")
    approval = ApprovalRequest.from_action(request, risk_level=RiskLevel.HIGH)
    assert approval.risk_level is RiskLevel.HIGH
    assert approval.action_snapshot == request.to_canonical_json()


@pytest.fixture
def approval_payload():
    from app.policy.risk import RiskLevel
    request = action(reason="inspect", request_id="req-1", workspace="/work", agent_id="agent-1")
    payload = ApprovalRequest.from_action(request, risk_level=RiskLevel.MEDIUM).model_dump()
    ApprovalRequest(**payload)  # Every negative case starts from a validated baseline.
    return payload


@pytest.mark.parametrize("field,value,message", [
    ("action_hash", "0" * 64, "Hash does not match"),
    ("action_hash", "short", "64-character"),
    ("action_hash", "g" * 64, "64-character"),
    ("action_id", "other.action", "Mismatched action_id"),
    ("tool", "file.read", "Mismatched tool"),
    ("reason", "other", "Mismatched reason"),
    ("request_id", "other", "Mismatched request_id"),
    ("workspace", "/other", "Mismatched workspace"),
    ("agent_id", "other", "Mismatched agent_id"),
    ("expires_at", 0, "strictly greater"),
    ("created_at", math.nan, "finite"), ("created_at", math.inf, "finite"),
    ("expires_at", math.nan, "finite"), ("expires_at", -math.inf, "finite"),
    ("unauthorized_extra", True, "Extra inputs"),
])
def test_approval_rejects_one_field_mutation(approval_payload, field, value, message):
    approval_payload[field] = value
    with pytest.raises(ValidationError, match=message):
        ApprovalRequest(**approval_payload)
