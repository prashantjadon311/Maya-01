"""Project H Process Executor.

Enforces argv-only execution with shell=False, cwd containment, minimal
controlled environment, bounded output capture, and process escalation on timeout.
"""

import asyncio
from pathlib import Path
from typing import Any
import os

from app.actions.schema import ActionRequest, ActionResult
from app.executors.base import BaseExecutor, ProcessArgs
from app.policy.engine import PolicyDecision, PolicyEvaluation, resolve_trusted_executable
from app.policy.paths import canonical_path

MAX_PROCESS_OUTPUT_BYTES = 1_048_576  # 1 MiB max captured output per stream
DEFAULT_SAFE_ENV_PATH = "/usr/bin:/bin:/usr/local/bin"

DANGEROUS_ENV_VARS = frozenset({
    "LD_PRELOAD",
    "LD_LIBRARY_PATH",
    "PYTHONPATH",
    "PYTHONHOME",
    "PYTHONINSPECT",
    "PYTHONSTARTUP",
    "BASH_ENV",
    "ENV",
    "NODE_OPTIONS",
    "PERL5OPT",
    "PERL5LIB",
    "RUBYOPT",
    "RUBYLIB",
    "GIT_SSH_COMMAND",
    "GIT_ASKPASS",
    "SSH_ASKPASS",
    "SUDO_ASKPASS",
    "PROMPT_COMMAND",
    "IFS",
    "LD_AUDIT",
})


class NetworkIsolationBackend:
    """Explicit capability abstraction for network isolation backends."""

    def is_available(self) -> bool:
        return False


async def _read_stream_bounded(stream: asyncio.StreamReader, limit: int) -> str:
    """Read an asyncio stream up to limit bytes without unbounded memory growth."""
    buffer = bytearray()
    while True:
        chunk = await stream.read(min(8192, limit - len(buffer) + 1 if len(buffer) < limit else 8192))
        if not chunk:
            break
        if len(buffer) < limit:
            remaining = limit - len(buffer)
            buffer.extend(chunk[:remaining])
    return buffer.decode("utf-8", errors="replace")


class ProcessExecutor(BaseExecutor):
    """Executes subprocesses securely with argv-only semantics and no shell."""

    def __init__(self, network_backend: NetworkIsolationBackend | None = None) -> None:
        self.network_backend = network_backend

    async def execute(self, action: ActionRequest, context: Any = None) -> ActionResult:
        """Execute a process.run action request within trusted constraints."""
        # 1. Defense-in-depth API check: require valid PolicyEvaluation context
        if (
            not isinstance(context, PolicyEvaluation)
            or context.decision != PolicyDecision.ALLOW_PREAPPROVED
            or context.matched_preapproval_rule is None
            or context.resolved_executable is None
        ):
            return ActionResult(
                success=False,
                error="Process execution denied: requires valid preapproved PolicyEvaluation context",
            )

        # 2. Parse and validate arguments against strict schema
        try:
            args = ProcessArgs.model_validate(action.arguments)
        except Exception as exc:
            return ActionResult(success=False, error=f"Invalid process arguments: {exc}")

        # 3. Extract trusted preapproval constraints
        rule = context.matched_preapproval_rule
        timeout_seconds = rule.timeout_seconds
        env_allowlist = rule.env_allowlist
        network_allowed = rule.network_allowed
        working_roots = rule.working_roots
        resolved_exe = context.resolved_executable

        # 4. Network isolation enforcement
        if not network_allowed:
            if self.network_backend is None or not self.network_backend.is_available():
                return ActionResult(
                    success=False,
                    error="Network isolation unavailable: preapproved rule specifies network_allowed=False but no network isolation backend is available in PH-040",
                )

        # 5. Immediate cwd revalidation (TOCTOU defense)
        try:
            cwd_path = canonical_path(args.cwd)
        except Exception as exc:
            return ActionResult(success=False, error=f"Malformed cwd: {exc}")

        if not cwd_path.is_dir():
            return ActionResult(success=False, error=f"cwd is not an existing directory: {cwd_path}")

        if working_roots:
            in_root = any(cwd_path.is_relative_to(canonical_path(r)) for r in working_roots)
            if not in_root:
                return ActionResult(success=False, error=f"cwd '{cwd_path}' is outside allowed working roots")

        # 6. Controlled environment construction
        proc_env: dict[str, str] = {
            "PATH": DEFAULT_SAFE_ENV_PATH,
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
        }
        if "HOME" in os.environ:
            proc_env["HOME"] = os.environ["HOME"]

        for k, v in args.env.items():
            if k in DANGEROUS_ENV_VARS:
                return ActionResult(success=False, error=f"Dangerous environment variable '{k}' is forbidden")
            if k not in env_allowlist:
                return ActionResult(success=False, error=f"Environment variable '{k}' not permitted by rule allowlist")
            proc_env[k] = v

        # 7. Subprocess spawn (argv only, shell=False, stdin=DEVNULL)
        try:
            proc = await asyncio.create_subprocess_exec(
                str(resolved_exe),
                *args.argv[1:],
                cwd=str(cwd_path),
                env=proc_env,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except Exception as exc:
            return ActionResult(success=False, error=f"Subprocess spawn failed: {exc}")

        # 8. Bounded stream reading and timeout escalation
        stdout_task = asyncio.create_task(_read_stream_bounded(proc.stdout, MAX_PROCESS_OUTPUT_BYTES))
        stderr_task = asyncio.create_task(_read_stream_bounded(proc.stderr, MAX_PROCESS_OUTPUT_BYTES))

        try:
            await asyncio.wait_for(proc.wait(), timeout=timeout_seconds)
            stdout_text = await stdout_task
            stderr_text = await stderr_task
        except asyncio.TimeoutError:
            try:
                proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=2.0)
            except (asyncio.TimeoutError, OSError):
                try:
                    proc.kill()
                    await asyncio.wait_for(proc.wait(), timeout=2.0)
                except OSError:
                    pass

            stdout_task.cancel()
            stderr_task.cancel()
            await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)
            return ActionResult(success=False, error=f"Process timed out after {timeout_seconds}s")

        return ActionResult(
            success=(proc.returncode == 0),
            output=stdout_text,
            error=stderr_text if proc.returncode != 0 else None,
        )
