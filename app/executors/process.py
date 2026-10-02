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
from app.policy.engine import PolicyEvaluation, resolve_trusted_executable
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

    async def execute(self, action: ActionRequest, context: Any = None) -> ActionResult:
        """Execute a process.run action request within trusted constraints."""
        # 1. Parse and validate arguments against strict schema
        try:
            args = ProcessArgs.model_validate(action.arguments)
        except Exception as exc:
            return ActionResult(success=False, error=f"Invalid process arguments: {exc}")

        # 2. Extract trusted preapproval constraints if available
        timeout_seconds = 30
        env_allowlist: tuple[str, ...] = ()
        network_allowed = False
        working_roots: tuple[str, ...] = ()
        resolved_exe: Path | None = None

        if isinstance(context, PolicyEvaluation):
            rule = context.matched_preapproval_rule
            if rule is not None:
                timeout_seconds = rule.timeout_seconds
                env_allowlist = rule.env_allowlist
                network_allowed = rule.network_allowed
                working_roots = rule.working_roots
            if context.resolved_executable is not None:
                resolved_exe = context.resolved_executable

        # 3. Network isolation enforcement
        if not network_allowed:
            return ActionResult(
                success=False,
                error="Network isolation unavailable: preapproved rule specifies network_allowed=False but no network isolation backend is available in PH-040",
            )

        # 4. Immediate cwd revalidation (TOCTOU defense)
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

        # 5. Executable resolution without ambient PATH
        if resolved_exe is None:
            resolved_exe = resolve_trusted_executable(args.argv[0])

        if resolved_exe is None:
            return ActionResult(
                success=False,
                error=f"Executable '{args.argv[0]}' could not be resolved from trusted system locations",
            )

        # 6. Controlled environment construction
        proc_env: dict[str, str] = {
            "PATH": DEFAULT_SAFE_ENV_PATH,
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
        }
        # Safely pass HOME if it exists in environment
        if "HOME" in os.environ:
            proc_env["HOME"] = os.environ["HOME"]

        for k, v in args.env.items():
            if k in DANGEROUS_ENV_VARS:
                return ActionResult(success=False, error=f"Dangerous environment variable '{k}' is forbidden")
            if env_allowlist and k not in env_allowlist:
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
            # Terminate -> bounded wait -> kill escalation
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
            return ActionResult(success=False, error=f"Process timed out after {timeout_seconds}s")

        return ActionResult(
            success=(proc.returncode == 0),
            output=stdout_text,
            error=stderr_text if proc.returncode != 0 else None,
        )
