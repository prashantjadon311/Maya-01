"""Project H XDG / Application Executor.

Provides controlled app/file opening via xdg-open. Strictly forbids URL schemes
like http:// and https:// which must pass browser domain policy via BrowserBridge.
"""

import asyncio
from typing import Any
import shutil

from app.actions.schema import ActionRequest, ActionResult
from app.executors.base import BaseExecutor, XdgOpenArgs
from app.policy.engine import resolve_trusted_executable


class XdgExecutor(BaseExecutor):
    """Executes local application/file opening via xdg-open without shell."""

    async def execute(self, action: ActionRequest, context: Any = None) -> ActionResult:
        """Execute an app.open action request."""
        # 1. Parse and validate arguments against strict schema
        try:
            args = XdgOpenArgs.model_validate(action.arguments)
        except Exception as exc:
            return ActionResult(success=False, error=f"Invalid app.open arguments: {exc}")

        # 2. Re-verify URL exclusion: HTTP/HTTPS URLs must not bypass browser policy
        target_lower = args.target.lower()
        if target_lower.startswith("http://") or target_lower.startswith("https://"):
            return ActionResult(
                success=False,
                error="xdg-open cannot open HTTP/HTTPS URLs; browser URLs must pass browser policy via BrowserBridge",
            )

        # 3. Resolve xdg-open binary securely
        xdg_bin = resolve_trusted_executable("xdg-open")
        if xdg_bin is None:
            # Fallback check using shutil.which if not in standard /usr/bin or /bin
            found = shutil.which("xdg-open")
            if found:
                resolved = resolve_trusted_executable(found)
                if resolved:
                    xdg_bin = resolved

        if xdg_bin is None:
            return ActionResult(
                success=False,
                error="xdg-open binary not available in trusted system locations",
            )

        # 4. Execute xdg-open with argv only (shell=False)
        try:
            proc = await asyncio.create_subprocess_exec(
                str(xdg_bin),
                args.target,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_data, stderr_data = await asyncio.wait_for(proc.communicate(), timeout=10.0)
            if proc.returncode != 0:
                err_text = stderr_data.decode("utf-8", errors="replace")
                return ActionResult(success=False, error=f"xdg-open exited with code {proc.returncode}: {err_text}")
            return ActionResult(success=True, output=f"Opened '{args.target}' via xdg-open")
        except asyncio.TimeoutError:
            try:
                proc.kill()
                await proc.wait()
            except OSError:
                pass
            return ActionResult(success=False, error="xdg-open execution timed out")
        except Exception as exc:
            return ActionResult(success=False, error=f"Failed to spawn xdg-open: {exc}")
