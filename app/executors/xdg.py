"""Project H XDG / Application Executor.

Provides controlled app/file opening via xdg-open for local filesystem targets only.
Strictly forbids URI schemes to prevent bypassing browser domain security policy.
"""

import asyncio
from pathlib import Path
from typing import Any

from app.actions.schema import ActionRequest, ActionResult
from app.core.config import FileRootConfig
from app.executors.base import BaseExecutor, XdgOpenArgs
from app.policy.engine import DEFAULT_SENSITIVE_PATHS, PolicyDecision, PolicyEvaluation, resolve_trusted_executable
from app.policy.paths import canonical_path


class XdgExecutor(BaseExecutor):
    """Executes local application/file opening via xdg-open without shell."""

    def __init__(self, allowed_file_roots: list[FileRootConfig] | None = None) -> None:
        self.allowed_file_roots = list(allowed_file_roots or [])

    async def execute(self, action: ActionRequest, context: Any = None) -> ActionResult:
        """Execute an app.open action request."""
        # 0. Require valid PolicyEvaluation context
        if not isinstance(context, PolicyEvaluation) or context.decision != PolicyDecision.ALLOW_PREAPPROVED:
            return ActionResult(
                success=False,
                error="XDG execution denied: requires valid preapproved PolicyEvaluation context",
            )
        # 1. Parse and validate arguments against strict schema
        try:
            args = XdgOpenArgs.model_validate(action.arguments)
        except Exception as exc:
            return ActionResult(success=False, error=f"Invalid app.open arguments: {exc}")

        target_str = args.target.strip()

        # 2. Reject URI schemes: xdg-open is restricted to local filesystem targets
        if ":" in target_str:
            return ActionResult(
                success=False,
                error=f"xdg-open is restricted to local filesystem targets; URI scheme in target '{target_str}' is rejected",
            )

        # 3. Canonicalize and verify local filesystem path
        try:
            target_path = canonical_path(target_str)
        except Exception as exc:
            return ActionResult(success=False, error=f"Invalid local file target for xdg-open: {exc}")

        if not target_path.exists():
            return ActionResult(success=False, error=f"Target file does not exist: {target_path}")

        # Check sensitive paths
        for denied_str in DEFAULT_SENSITIVE_PATHS:
            try:
                denied_path = canonical_path(denied_str)
                if target_path == denied_path or denied_path in target_path.parents:
                    return ActionResult(success=False, error=f"Access to sensitive path '{target_path}' is denied")
            except Exception:
                continue

        if target_path.name == ".env" or target_path.name.startswith(".env."):
            return ActionResult(success=False, error="Access to credential files (.env) is denied")

        # Root containment check
        in_allowed_root = False
        for root in self.allowed_file_roots:
            try:
                root_path = canonical_path(root.path)
                if (target_path == root_path or root_path in target_path.parents) and root.read:
                    in_allowed_root = True
                    break
            except Exception:
                continue

        if not in_allowed_root:
            return ActionResult(success=False, error=f"Target path '{target_path}' is outside allowed read roots")

        # 4. Resolve xdg-open binary securely (NO ambient shutil.which fallback)
        xdg_bin = resolve_trusted_executable("xdg-open")
        if xdg_bin is None:
            return ActionResult(
                success=False,
                error="xdg-open binary not available in trusted system locations",
            )

        # Immediate re-verification before spawn (TOCTOU defense)
        try:
            rechecked = canonical_path(str(target_path))
            if not rechecked.exists() or rechecked != target_path:
                return ActionResult(success=False, error="Target path changed immediately prior to execution")
        except Exception:
            return ActionResult(success=False, error="Target path re-verification failed")

        # 5. Execute xdg-open with argv only (shell=False, DEVNULL for stdout and stderr)
        try:
            proc = await asyncio.create_subprocess_exec(
                str(xdg_bin),
                str(target_path),
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            try:
                await asyncio.wait_for(proc.wait(), timeout=10.0)
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                    await proc.wait()
                except OSError:
                    pass
                return ActionResult(success=False, error="xdg-open execution timed out")

            if proc.returncode != 0:
                return ActionResult(success=False, error=f"xdg-open exited with code {proc.returncode}")
            return ActionResult(success=True, output=f"Opened '{target_path}' via xdg-open")
        except Exception as exc:
            return ActionResult(success=False, error=f"Failed to spawn xdg-open: {exc}")
