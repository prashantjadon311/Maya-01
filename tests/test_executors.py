"""Tests for PH-040 Safe Executors (Process, File, XDG, Browser)."""

import json
import os
from pathlib import Path
import pytest
from pydantic import ValidationError

from app.actions.schema import ActionDefinition, ActionRequest
from app.core.config import FileRootConfig
from app.core.dispatcher import ActionDispatcher
from app.executors.base import ProcessArgs, FileReadArgs, FileWriteArgs, XdgOpenArgs
from app.executors.files import FileExecutor
from app.executors.process import ProcessExecutor
from app.executors.xdg import XdgExecutor
from app.policy.engine import PolicyEngine, PolicyEvaluation, PolicyDecision, PreapprovalRule, resolve_trusted_executable
from app.policy.risk import RiskLevel


def valid_allow_context(rule: PreapprovalRule | None = None, resolved_exe: Path | None = None) -> PolicyEvaluation:
    """Helper to construct a valid ALLOW_PREAPPROVED PolicyEvaluation context."""
    return PolicyEvaluation(
        decision=PolicyDecision.ALLOW_PREAPPROVED,
        trusted_risk=RiskLevel.LOW,
        matched_preapproval_rule=rule,
        resolved_executable=resolved_exe,
    )


# ---------------------------------------------------------------------------
# PROCESS EXECUTOR TESTS
# ---------------------------------------------------------------------------

def test_process_args_strict_unknown_fields_and_validation():
    # Extra fields like shell or stdin must be rejected
    with pytest.raises(ValidationError):
        ProcessArgs.model_validate({"argv": ["ls"], "cwd": "/work", "shell": True})

    with pytest.raises(ValidationError):
        ProcessArgs.model_validate({"argv": ["ls"], "cwd": "/work", "stdin": "payload"})

    # Empty argv or whitespace only
    with pytest.raises(ValidationError):
        ProcessArgs.model_validate({"argv": [], "cwd": "/work"})

    with pytest.raises(ValidationError):
        ProcessArgs.model_validate({"argv": ["  "], "cwd": "/work"})

    # NUL in argv
    with pytest.raises(ValidationError):
        ProcessArgs.model_validate({"argv": ["echo", "bad\x00arg"], "cwd": "/work"})

    # Valid args
    args = ProcessArgs.model_validate({"argv": ["echo", "hello"], "cwd": "/tmp"})
    assert args.argv == ["echo", "hello"]


@pytest.mark.anyio
async def test_process_shell_metacharacters_remain_literal(tmp_path):
    evil_file = tmp_path / "evil.txt"
    dangerous_arg = f"; touch {evil_file}; echo hacked"

    executor = ProcessExecutor()
    req = ActionRequest(
        id="test.proc",
        tool="process.run",
        arguments={"argv": ["echo", dangerous_arg], "cwd": str(tmp_path)},
    )
    rule = PreapprovalRule(
        id="rule.echo",
        executable="echo",
        argv_prefix=(),
        working_roots=(str(tmp_path),),
        approval="preapproved",
        timeout_seconds=10,
        risk="low",
        network_allowed=True,
    )
    context = valid_allow_context(rule=rule, resolved_exe=resolve_trusted_executable("echo"))

    result = await executor.execute(req, context=context)
    assert result.success
    assert not evil_file.exists()
    assert dangerous_arg in result.output


@pytest.mark.anyio
async def test_process_timeout_kills_process(tmp_path):
    executor = ProcessExecutor()
    req = ActionRequest(
        id="test.sleep",
        tool="process.run",
        arguments={"argv": ["sleep", "10"], "cwd": str(tmp_path)},
    )
    rule = PreapprovalRule(
        id="rule.sleep",
        executable="sleep",
        argv_prefix=(),
        working_roots=(str(tmp_path),),
        approval="preapproved",
        timeout_seconds=1,
        risk="low",
        network_allowed=True,
    )
    context = valid_allow_context(rule=rule, resolved_exe=resolve_trusted_executable("sleep"))

    result = await executor.execute(req, context=context)
    assert not result.success
    assert "timed out" in result.error


@pytest.mark.anyio
async def test_process_bounded_output(tmp_path):
    executor = ProcessExecutor()
    py_script = "import sys; sys.stdout.write('A' * 2_000_000)"
    req = ActionRequest(
        id="test.output",
        tool="process.run",
        arguments={"argv": ["python3", "-c", py_script], "cwd": str(tmp_path)},
    )
    rule = PreapprovalRule(
        id="rule.py",
        executable="python3",
        argv_prefix=("-c",),
        working_roots=(str(tmp_path),),
        approval="preapproved",
        timeout_seconds=10,
        risk="medium",
        network_allowed=True,
    )
    context = valid_allow_context(rule=rule, resolved_exe=resolve_trusted_executable("python3"))

    result = await executor.execute(req, context=context)
    assert result.success
    assert len(result.output) <= 1_048_576


@pytest.mark.anyio
async def test_process_stdin_unavailable(tmp_path):
    executor = ProcessExecutor()
    script = "import sys; data = sys.stdin.read(); print(f'read:{len(data)}')"
    req = ActionRequest(
        id="test.stdin",
        tool="process.run",
        arguments={"argv": ["python3", "-c", script], "cwd": str(tmp_path)},
    )
    rule = PreapprovalRule(
        id="rule.stdin",
        executable="python3",
        argv_prefix=("-c",),
        working_roots=(str(tmp_path),),
        approval="preapproved",
        timeout_seconds=5,
        risk="medium",
        network_allowed=True,
    )
    context = valid_allow_context(rule=rule, resolved_exe=resolve_trusted_executable("python3"))

    result = await executor.execute(req, context=context)
    assert result.success
    assert "read:0" in result.output


@pytest.mark.anyio
async def test_process_malformed_and_escaping_cwd_denied(tmp_path):
    executor = ProcessExecutor()
    nonexistent = tmp_path / "nonexistent"

    req = ActionRequest(
        id="test.cwd",
        tool="process.run",
        arguments={"argv": ["echo", "test"], "cwd": str(nonexistent)},
    )
    rule = PreapprovalRule(
        id="rule.echo",
        executable="echo",
        argv_prefix=(),
        working_roots=(str(tmp_path),),
        approval="preapproved",
        timeout_seconds=5,
        risk="low",
        network_allowed=True,
    )
    context = valid_allow_context(rule=rule, resolved_exe=resolve_trusted_executable("echo"))

    result = await executor.execute(req, context=context)
    assert not result.success
    assert "cwd is not an existing directory" in result.error

    outside = tmp_path / "outside"
    outside.mkdir()
    inside = tmp_path / "work"
    inside.mkdir()
    sym_escape = inside / "link_to_outside"
    sym_escape.symlink_to(outside)

    req2 = ActionRequest(
        id="test.escape",
        tool="process.run",
        arguments={"argv": ["echo", "test"], "cwd": str(sym_escape)},
    )
    rule2 = PreapprovalRule(
        id="rule.echo2",
        executable="echo",
        argv_prefix=(),
        working_roots=(str(inside),),
        approval="preapproved",
        timeout_seconds=5,
        risk="low",
        network_allowed=True,
    )
    context2 = valid_allow_context(rule=rule2, resolved_exe=resolve_trusted_executable("echo"))

    result2 = await executor.execute(req2, context=context2)
    assert not result2.success
    assert "outside allowed working roots" in result2.error


@pytest.mark.anyio
async def test_process_controlled_env_and_dangerous_rejected(tmp_path):
    executor = ProcessExecutor()
    rule = PreapprovalRule(
        id="rule.echo",
        executable="echo",
        argv_prefix=(),
        working_roots=(str(tmp_path),),
        approval="preapproved",
        timeout_seconds=5,
        risk="low",
        env_allowlist=("SAFE_VAR",),
        network_allowed=True,
    )
    context = valid_allow_context(rule=rule, resolved_exe=resolve_trusted_executable("echo"))

    req_dangerous = ActionRequest(
        id="test.danger",
        tool="process.run",
        arguments={"argv": ["echo", "hi"], "cwd": str(tmp_path), "env": {"LD_PRELOAD": "/tmp/evil.so"}},
    )
    res_danger = await executor.execute(req_dangerous, context=context)
    assert not res_danger.success
    assert "Dangerous environment variable" in res_danger.error

    req_unallowed = ActionRequest(
        id="test.unallowed",
        tool="process.run",
        arguments={"argv": ["echo", "hi"], "cwd": str(tmp_path), "env": {"OTHER_VAR": "val"}},
    )
    res_unallowed = await executor.execute(req_unallowed, context=context)
    assert not res_unallowed.success
    assert "not permitted by rule allowlist" in res_unallowed.error

    req_allowed = ActionRequest(
        id="test.allowed",
        tool="process.run",
        arguments={"argv": ["echo", "hi"], "cwd": str(tmp_path), "env": {"SAFE_VAR": "hello_safe"}},
    )
    res_allowed = await executor.execute(req_allowed, context=context)
    assert res_allowed.success


@pytest.mark.anyio
async def test_process_path_hijack_cannot_change_preapproved_executable(tmp_path, monkeypatch):
    hijack_dir = tmp_path / "hijack_bin"
    hijack_dir.mkdir()
    fake_git = hijack_dir / "git"
    fake_git.write_text("#!/bin/sh\necho HIJACKED\n", encoding="utf-8")
    fake_git.chmod(0o755)

    original_path = os.environ.get("PATH", "")
    monkeypatch.setenv("PATH", f"{hijack_dir}:{original_path}")

    engine = PolicyEngine(
        preapproved_rules=[
            PreapprovalRule(
                id="rule.git",
                executable="git",
                argv_prefix=("--version",),
                working_roots=(str(tmp_path),),
                approval="preapproved",
                timeout_seconds=5,
                risk="low",
                network_allowed=True,
            )
        ]
    )
    req = ActionRequest(
        id="test.git",
        tool="process.run",
        arguments={"argv": ["git", "--version"], "cwd": str(tmp_path)},
    )
    eval_res = engine.evaluate_detailed(req)
    assert eval_res.decision == PolicyDecision.ALLOW_PREAPPROVED
    assert eval_res.resolved_executable is not None
    assert str(eval_res.resolved_executable) != str(fake_git)
    assert eval_res.resolved_executable.is_relative_to(Path("/usr/bin")) or eval_res.resolved_executable.is_relative_to(Path("/bin"))

    executor = ProcessExecutor()
    result = await executor.execute(req, context=eval_res)
    assert result.success
    assert "HIJACKED" not in result.output
    assert "git version" in result.output


@pytest.mark.anyio
async def test_process_no_fake_network_allowed_enforcement(tmp_path):
    executor = ProcessExecutor()
    rule = PreapprovalRule(
        id="rule.echo",
        executable="echo",
        argv_prefix=(),
        working_roots=(str(tmp_path),),
        approval="preapproved",
        timeout_seconds=5,
        risk="low",
        network_allowed=False,
    )
    context = valid_allow_context(rule=rule, resolved_exe=resolve_trusted_executable("echo"))

    req = ActionRequest(
        id="test.echo",
        tool="process.run",
        arguments={"argv": ["echo", "test"], "cwd": str(tmp_path)},
    )
    result = await executor.execute(req, context=context)
    assert not result.success
    assert "Network isolation unavailable" in result.error


# ---------------------------------------------------------------------------
# FILE EXECUTOR TESTS
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_file_traversal_denied(tmp_path):
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("classified", encoding="utf-8")

    executor = FileExecutor(
        allowed_roots=[FileRootConfig(path=str(work_dir), read=True, write=True, delete=False)]
    )

    req = ActionRequest(
        id="test.read",
        tool="file.read",
        arguments={"path": str(work_dir / ".." / "secret.txt")},
    )
    result = await executor.execute(req, context=valid_allow_context())
    assert not result.success
    assert "outside configured allowed file roots" in result.error


@pytest.mark.anyio
async def test_file_symlink_escape_denied(tmp_path):
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("classified", encoding="utf-8")

    symlink_file = work_dir / "symlink_secret"
    symlink_file.symlink_to(secret_file)

    executor = FileExecutor(
        allowed_roots=[FileRootConfig(path=str(work_dir), read=True, write=True, delete=False)]
    )

    req = ActionRequest(
        id="test.read",
        tool="file.read",
        arguments={"path": str(symlink_file)},
    )
    result = await executor.execute(req, context=valid_allow_context())
    assert not result.success
    assert "outside configured allowed file roots" in result.error


@pytest.mark.anyio
async def test_file_capability_enforcement(tmp_path):
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    test_file = work_dir / "test.txt"
    test_file.write_text("sample content", encoding="utf-8")

    read_only_exec = FileExecutor(
        allowed_roots=[FileRootConfig(path=str(work_dir), read=True, write=False, delete=False)]
    )

    ctx = valid_allow_context()
    read_res = await read_only_exec.execute(
        ActionRequest(id="test.read", tool="file.read", arguments={"path": str(test_file)}),
        context=ctx,
    )
    assert read_res.success
    assert read_res.output == "sample content"

    write_res = await read_only_exec.execute(
        ActionRequest(
            id="test.write",
            tool="file.write",
            arguments={"path": str(work_dir / "new.txt"), "content": "hello"},
        ),
        context=ctx,
    )
    assert not write_res.success
    assert "does not grant 'write' capability" in write_res.error

    delete_res = await read_only_exec.execute(
        ActionRequest(
            id="test.delete",
            tool="file.delete",
            arguments={"path": str(test_file)},
        ),
        context=ctx,
    )
    assert not delete_res.success
    assert "does not grant 'delete' capability" in delete_res.error


@pytest.mark.anyio
async def test_file_atomic_write_success(tmp_path):
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    target_file = work_dir / "atomic.txt"

    executor = FileExecutor(
        allowed_roots=[FileRootConfig(path=str(work_dir), read=True, write=True, delete=False)]
    )

    req = ActionRequest(
        id="test.write",
        tool="file.write",
        arguments={"path": str(target_file), "content": "atomic payload"},
    )
    res = await executor.execute(req, context=valid_allow_context())
    assert res.success
    assert target_file.read_text(encoding="utf-8") == "atomic payload"


@pytest.mark.anyio
async def test_file_write_through_symlink_rejected(tmp_path):
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    real_file = work_dir / "real.txt"
    real_file.write_text("original content", encoding="utf-8")

    symlink_target = work_dir / "symlink.txt"
    symlink_target.symlink_to(real_file)

    executor = FileExecutor(
        allowed_roots=[FileRootConfig(path=str(work_dir), read=True, write=True, delete=False)]
    )

    req = ActionRequest(
        id="test.write",
        tool="file.write",
        arguments={"path": str(symlink_target), "content": "overwritten"},
    )
    res = await executor.execute(req, context=valid_allow_context())
    assert not res.success
    assert "Writing through a symlink is strictly forbidden" in res.error
    assert real_file.read_text(encoding="utf-8") == "original content"


@pytest.mark.anyio
async def test_file_delete_does_not_auto_execute(tmp_path):
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    target = work_dir / "victim.txt"
    target.write_text("important", encoding="utf-8")

    executor = FileExecutor(
        allowed_roots=[FileRootConfig(path=str(work_dir), read=True, write=True, delete=True)]
    )

    req = ActionRequest(
        id="test.delete",
        tool="file.delete",
        arguments={"path": str(target)},
    )
    res = await executor.execute(req, context=valid_allow_context())
    assert not res.success
    assert "requires explicit interactive user approval (PH-050)" in res.error
    assert target.exists()


# ---------------------------------------------------------------------------
# XDG EXECUTOR TESTS
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_xdg_cannot_bypass_browser_url_policy():
    executor = XdgExecutor()

    with pytest.raises(ValidationError, match="xdg-open cannot open HTTP/HTTPS URLs"):
        XdgOpenArgs(target="https://google.com")

    req = ActionRequest(
        id="test.xdg",
        tool="app.open",
        arguments={"target": "http://malicious.com"},
    )
    res = await executor.execute(req, context=valid_allow_context())
    assert not res.success
    assert "URI scheme in target" in res.error or "browser URLs must pass browser policy" in res.error


# ---------------------------------------------------------------------------
# PH-040 POST-MERGE SECURITY CLOSURE TESTS
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_empty_env_allowlist_rejects_custom_env(tmp_path):
    executor = ProcessExecutor()
    rule = PreapprovalRule(
        id="rule.echo",
        executable="echo",
        argv_prefix=(),
        working_roots=(str(tmp_path),),
        approval="preapproved",
        timeout_seconds=5,
        risk="low",
        env_allowlist=(),
        network_allowed=True,
    )
    context = valid_allow_context(rule=rule, resolved_exe=resolve_trusted_executable("echo"))

    req_valid = ActionRequest(
        id="test.empty_env",
        tool="process.run",
        arguments={"argv": ["echo", "hi"], "cwd": str(tmp_path), "env": {}},
    )
    res_valid = await executor.execute(req_valid, context=context)
    assert res_valid.success

    req_invalid = ActionRequest(
        id="test.custom_env",
        tool="process.run",
        arguments={"argv": ["echo", "hi"], "cwd": str(tmp_path), "env": {"CUSTOM_VAR": "value"}},
    )
    res_invalid = await executor.execute(req_invalid, context=context)
    assert not res_invalid.success
    assert "not permitted by rule allowlist" in res_invalid.error


@pytest.mark.anyio
async def test_process_executor_requires_valid_allow_context(tmp_path):
    executor = ProcessExecutor()
    req = ActionRequest(
        id="test.proc",
        tool="process.run",
        arguments={"argv": ["echo", "hi"], "cwd": str(tmp_path)},
    )

    res_no_ctx = await executor.execute(req, context=None)
    assert not res_no_ctx.success

    ask_ctx = PolicyEvaluation(
        decision=PolicyDecision.ASK_USER,
        trusted_risk=RiskLevel.HIGH,
    )
    res_ask_ctx = await executor.execute(req, context=ask_ctx)
    assert not res_ask_ctx.success


def test_resolve_trusted_executable_strict_v1():
    from app.policy.engine import resolve_trusted_executable, TRUSTED_EXEC_DIRS

    resolved_git = resolve_trusted_executable("git")
    assert resolved_git is not None
    assert any(resolved_git.is_relative_to(d) or resolved_git.parent.resolve() == d for d in TRUSTED_EXEC_DIRS)

    assert resolve_trusted_executable("/home/user/bin/git") is None
    assert resolve_trusted_executable("/tmp/malicious_git") is None

    assert resolve_trusted_executable("./git") is None
    assert resolve_trusted_executable("bin/git") is None


@pytest.mark.anyio
async def test_xdg_no_ambient_shutil_which_fallback(tmp_path, monkeypatch):
    hijack_dir = tmp_path / "hijack_bin"
    hijack_dir.mkdir()
    fake_xdg = hijack_dir / "xdg-open"
    fake_xdg.write_text("#!/bin/sh\necho MALICIOUS\n", encoding="utf-8")
    fake_xdg.chmod(0o755)

    monkeypatch.setenv("PATH", str(hijack_dir))

    def mock_resolve(exe, trusted_dirs=None):
        if exe == "xdg-open":
            return None
        from app.policy.engine import resolve_trusted_executable as orig_resolve
        return orig_resolve(exe, trusted_dirs) if trusted_dirs else orig_resolve(exe)

    monkeypatch.setattr("app.executors.xdg.resolve_trusted_executable", mock_resolve)

    target_file = tmp_path / "test.txt"
    target_file.write_text("hello", encoding="utf-8")

    executor = XdgExecutor(allowed_file_roots=[FileRootConfig(path=str(tmp_path), read=True)])
    req = ActionRequest(
        id="test.xdg",
        tool="app.open",
        arguments={"target": str(target_file)},
    )

    res = await executor.execute(req, context=valid_allow_context())
    assert not res.success
    assert "xdg-open binary not available in trusted system locations" in res.error


@pytest.mark.anyio
async def test_xdg_target_schemes_and_root_security(tmp_path):
    target_file = tmp_path / "test.txt"
    target_file.write_text("hello", encoding="utf-8")

    executor = XdgExecutor(allowed_file_roots=[FileRootConfig(path=str(tmp_path), read=True)])
    ctx = valid_allow_context()

    forbidden_targets = [
        "http://example.com",
        "https://example.com",
        "ftp://example.com/file",
        "mailto:user@example.com",
        "ssh://user@host",
        "javascript:alert(1)",
        "data:text/html,hello",
        f"file://{target_file}",
    ]

    for target in forbidden_targets:
        req = ActionRequest(
            id="test.xdg_scheme",
            tool="app.open",
            arguments={"target": target},
        )
        res = await executor.execute(req, context=ctx)
        assert not res.success, f"Target '{target}' should have been rejected"

    outside_file = tmp_path.parent / "outside_file.txt"
    req_outside = ActionRequest(
        id="test.xdg_outside",
        tool="app.open",
        arguments={"target": str(outside_file)},
    )
    res_outside = await executor.execute(req_outside, context=ctx)
    assert not res_outside.success


@pytest.mark.anyio
async def test_file_read_symlink_swap_denied(tmp_path):
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    secret_dir = tmp_path / "secret"
    secret_dir.mkdir()
    secret_file = secret_dir / "secret.txt"
    secret_file.write_text("SUPER_SECRET", encoding="utf-8")

    sym_file = work_dir / "link.txt"
    sym_file.symlink_to(secret_file)

    executor = FileExecutor(allowed_roots=[FileRootConfig(path=str(work_dir), read=True)])
    req = ActionRequest(
        id="test.read_sym",
        tool="file.read",
        arguments={"path": str(sym_file)},
    )
    res = await executor.execute(req, context=valid_allow_context())
    assert not res.success


@pytest.mark.anyio
async def test_file_list_child_symlink_not_followed(tmp_path):
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()

    sym_link = work_dir / "link_to_outside"
    sym_link.symlink_to(outside_dir)

    executor = FileExecutor(allowed_roots=[FileRootConfig(path=str(work_dir), read=True)])
    req = ActionRequest(
        id="test.list",
        tool="file.list",
        arguments={"path": str(work_dir)},
    )
    res = await executor.execute(req, context=valid_allow_context())
    assert res.success
    entries = json.loads(res.output)
    sym_entry = next(e for e in entries if e["name"] == "link_to_outside")
    assert sym_entry["is_dir"] is False


# ---------------------------------------------------------------------------
# NEW MANDATORY MANDATE REGRESSION TESTS
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_file_and_xdg_context_requirement(tmp_path):
    target_file = tmp_path / "test.txt"
    target_file.write_text("hello", encoding="utf-8")

    file_exec = FileExecutor(allowed_roots=[FileRootConfig(path=str(tmp_path), read=True)])
    xdg_exec = XdgExecutor(allowed_file_roots=[FileRootConfig(path=str(tmp_path), read=True)])

    req_file = ActionRequest(id="test.read", tool="file.read", arguments={"path": str(target_file)})
    req_xdg = ActionRequest(id="test.xdg", tool="app.open", arguments={"target": str(target_file)})

    # Call without context -> denied
    res1 = await file_exec.execute(req_file, context=None)
    assert not res1.success
    assert "File execution denied" in res1.error

    res2 = await xdg_exec.execute(req_xdg, context=None)
    assert not res2.success
    assert "XDG execution denied" in res2.error

    # Call with ASK_USER context -> denied
    ask_ctx = PolicyEvaluation(decision=PolicyDecision.ASK_USER, trusted_risk=RiskLevel.MEDIUM)
    res3 = await file_exec.execute(req_file, context=ask_ctx)
    assert not res3.success

    res4 = await xdg_exec.execute(req_xdg, context=ask_ctx)
    assert not res4.success


@pytest.mark.anyio
async def test_process_executor_rule_rebinding(tmp_path):
    executor = ProcessExecutor()
    rule = PreapprovalRule(
        id="rule.echo",
        executable="echo",
        argv_prefix=("safe",),
        working_roots=(str(tmp_path),),
        approval="preapproved",
        timeout_seconds=5,
        risk="low",
        network_allowed=True,
    )
    ctx = valid_allow_context(rule=rule, resolved_exe=resolve_trusted_executable("echo"))

    # Wrong argv[0] mismatch
    req_bad_exe = ActionRequest(
        id="test.bad_exe",
        tool="process.run",
        arguments={"argv": ["sleep", "safe"], "cwd": str(tmp_path)},
    )
    res_bad_exe = await executor.execute(req_bad_exe, context=ctx)
    assert not res_bad_exe.success
    assert "does not match preapproved rule executable" in res_bad_exe.error

    # Prefix mismatch
    req_bad_prefix = ActionRequest(
        id="test.bad_prefix",
        tool="process.run",
        arguments={"argv": ["echo", "unsafe"], "cwd": str(tmp_path)},
    )
    res_bad_prefix = await executor.execute(req_bad_prefix, context=ctx)
    assert not res_bad_prefix.success
    assert "argv prefix does not match preapproved rule" in res_bad_prefix.error

    # Resolved executable mismatch
    fake_ctx = PolicyEvaluation(
        decision=PolicyDecision.ALLOW_PREAPPROVED,
        trusted_risk=RiskLevel.LOW,
        matched_preapproval_rule=rule,
        resolved_executable=Path("/usr/bin/custom_fake_echo"),
    )
    req_ok = ActionRequest(
        id="test.ok",
        tool="process.run",
        arguments={"argv": ["echo", "safe"], "cwd": str(tmp_path)},
    )
    res_mismatch = await executor.execute(req_ok, context=fake_ctx)
    assert not res_mismatch.success
    assert "resolved executable mismatch" in res_mismatch.error


@pytest.mark.anyio
async def test_composite_parent_gate_deny_and_high_risk(tmp_path):
    reg = ActionDispatcher(policy_engine=PolicyEngine(), registry=None)

    # Deny approval composite definition
    defn_deny = ActionDefinition(
        id="comp.deny",
        phrases=["run deny"],
        executor="composite",
        arguments={"steps": ["s1"]},
        approval="deny",
        risk="low",
    )
    res_deny = reg._definition_container_gate(defn_deny)
    assert res_deny is not None
    assert not res_deny.success

    # High risk composite definition
    defn_high = ActionDefinition(
        id="comp.high",
        phrases=["run high"],
        executor="composite",
        arguments={"steps": ["s1"]},
        approval="ask_user",
        risk="high",
    )
    res_high = reg._definition_container_gate(defn_high)
    assert res_high is not None
    assert not res_high.success
    assert "requires user approval" in res_high.error
