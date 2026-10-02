"""Project H File Executor.

Enforces canonicalization, root containment, capability checks, atomic writing,
and prevents traversal/symlink escapes. Rechecks all security invariants immediately before I/O.
"""

import json
import os
from pathlib import Path
import tempfile
from typing import Any

from app.actions.schema import ActionRequest, ActionResult
from app.core.config import FileRootConfig
from app.executors.base import (
    BaseExecutor,
    FileDeleteArgs,
    FileListArgs,
    FileReadArgs,
    FileWriteArgs,
)
from app.policy.engine import DEFAULT_SENSITIVE_PATHS
from app.policy.paths import canonical_path


class FileExecutor(BaseExecutor):
    """Executes contained file system operations."""

    def __init__(
        self,
        allowed_roots: list[FileRootConfig] | None = None,
        permanently_denied_paths: list[str] | None = None,
    ) -> None:
        self.allowed_roots = list(allowed_roots or [])
        custom_paths = set(permanently_denied_paths) if permanently_denied_paths else set()
        all_denied = set(DEFAULT_SENSITIVE_PATHS).union(custom_paths)
        self.permanently_denied_paths = [
            str(canonical_path(p))
            for p in all_denied
        ]

    def _verify_path_security(self, path_str: str, required_cap: str) -> tuple[Path | None, str | None]:
        """Canonicalize path and verify against sensitive defaults and allowed root capabilities."""
        try:
            target = canonical_path(path_str)
        except Exception as exc:
            return None, f"Malformed path '{path_str}': {exc}"

        # Sensitive paths check
        for denied_str in self.permanently_denied_paths:
            denied_path = Path(denied_str)
            if target == denied_path or denied_path in target.parents:
                return None, f"Access to sensitive path '{target}' is permanently denied"

        # Credential file check (.env)
        if target.name == ".env" or target.name.startswith(".env."):
            return None, "Access to credential files (.env) is denied"

        # Root containment and capability check
        in_allowed_root = False
        has_capability = False
        for root in self.allowed_roots:
            try:
                root_path = canonical_path(root.path)
            except Exception:
                continue
            if target == root_path or root_path in target.parents:
                in_allowed_root = True
                if required_cap == "read" and root.read:
                    has_capability = True
                    break
                if required_cap == "write" and root.write:
                    has_capability = True
                    break
                if required_cap == "delete" and root.delete:
                    has_capability = True
                    break

        if not in_allowed_root:
            return None, f"Path '{target}' is outside configured allowed file roots"
        if not has_capability:
            return None, f"Allowed root does not grant '{required_cap}' capability for '{target}'"

        return target, None

    async def execute(self, action: ActionRequest, context: Any = None) -> ActionResult:
        """Route to appropriate file operation based on action.tool."""
        if action.tool == "file.read":
            return await self.execute_read(action)
        elif action.tool == "file.list":
            return await self.execute_list(action)
        elif action.tool == "file.write":
            return await self.execute_write(action)
        elif action.tool == "file.delete":
            return await self.execute_delete(action)
        return ActionResult(success=False, error=f"Unsupported file tool: {action.tool}")

    async def execute_read(self, action: ActionRequest) -> ActionResult:
        """Execute file.read operation within root containment and size limits."""
        try:
            args = FileReadArgs.model_validate(action.arguments)
        except Exception as exc:
            return ActionResult(success=False, error=f"Invalid file.read arguments: {exc}")

        target, error = self._verify_path_security(args.path, "read")
        if error is not None:
            return ActionResult(success=False, error=error)
        assert target is not None

        if not target.is_file():
            return ActionResult(success=False, error=f"File not found or not a regular file: {target}")

        try:
            st = target.stat()
            if st.st_size > args.max_bytes:
                return ActionResult(
                    success=False,
                    error=f"File size ({st.st_size} bytes) exceeds max limit ({args.max_bytes} bytes)",
                )

            with open(target, "rb") as f:
                data = f.read(args.max_bytes + 1)
            if len(data) > args.max_bytes:
                return ActionResult(success=False, error=f"File content exceeds max limit ({args.max_bytes} bytes)")

            content = data.decode("utf-8", errors="replace")
            return ActionResult(success=True, output=content)
        except Exception as exc:
            return ActionResult(success=False, error=f"Failed to read file: {exc}")

    async def execute_list(self, action: ActionRequest) -> ActionResult:
        """Execute file.list operation within root containment and entry limits."""
        try:
            args = FileListArgs.model_validate(action.arguments)
        except Exception as exc:
            return ActionResult(success=False, error=f"Invalid file.list arguments: {exc}")

        target, error = self._verify_path_security(args.path, "read")
        if error is not None:
            return ActionResult(success=False, error=error)
        assert target is not None

        if not target.is_dir():
            return ActionResult(success=False, error=f"Target is not an existing directory: {target}")

        try:
            entries = []
            for idx, entry in enumerate(sorted(target.iterdir(), key=lambda p: p.name)):
                if idx >= args.max_entries:
                    break
                entries.append({
                    "name": entry.name,
                    "is_dir": entry.is_dir(),
                    "size": entry.stat().st_size if entry.is_file() else None,
                })
            return ActionResult(success=True, output=json.dumps(entries))
        except Exception as exc:
            return ActionResult(success=False, error=f"Failed to list directory: {exc}")

    async def execute_write(self, action: ActionRequest) -> ActionResult:
        """Execute atomic file.write operation with fsync and symlink protection."""
        try:
            args = FileWriteArgs.model_validate(action.arguments)
        except Exception as exc:
            return ActionResult(success=False, error=f"Invalid file.write arguments: {exc}")

        target, error = self._verify_path_security(args.path, "write")
        if error is not None:
            return ActionResult(success=False, error=error)
        assert target is not None

        # Re-check symlink on the target path: never write through a symlink
        raw_path = Path(args.path).expanduser()
        if raw_path.is_symlink() or target.is_symlink():
            return ActionResult(success=False, error="Writing through a symlink is strictly forbidden")

        parent = target.parent
        if not parent.is_dir():
            return ActionResult(success=False, error=f"Parent directory does not exist: {parent}")

        # Verify parent is also within allowed root
        parent_target, parent_error = self._verify_path_security(str(parent), "write")
        if parent_error is not None:
            return ActionResult(success=False, error=f"Parent directory access error: {parent_error}")

        payload: bytes
        if isinstance(args.content, str):
            payload = args.content.encode("utf-8")
        else:
            payload = args.content

        # Atomic write via temporary file in the same directory
        temp_fd, temp_path_str = tempfile.mkstemp(dir=parent, prefix=".tmp_projh_")
        temp_path = Path(temp_path_str)
        try:
            with os.fdopen(temp_fd, "wb") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())

            # TOCTOU revalidation immediately before replace
            rechecked, recheck_err = self._verify_path_security(str(target), "write")
            if recheck_err is not None or rechecked != target:
                temp_path.unlink(missing_ok=True)
                return ActionResult(success=False, error="Target path changed during write")

            if raw_path.is_symlink() or target.is_symlink():
                temp_path.unlink(missing_ok=True)
                return ActionResult(success=False, error="Writing through a symlink is strictly forbidden")

            os.replace(temp_path, target)
            return ActionResult(success=True, output=f"Successfully wrote {len(payload)} bytes to {target.name}")
        except Exception as exc:
            temp_path.unlink(missing_ok=True)
            return ActionResult(success=False, error=f"Atomic write failed: {exc}")

    async def execute_delete(self, action: ActionRequest) -> ActionResult:
        """Defensive implementation of file.delete.

        CRITICAL SECURITY INVARIANT:
        High-risk file deletion cannot execute automatically in PH-040 because
        interactive user approval (PH-050) is not yet active.
        """
        try:
            args = FileDeleteArgs.model_validate(action.arguments)
        except Exception as exc:
            return ActionResult(success=False, error=f"Invalid file.delete arguments: {exc}")

        _target, error = self._verify_path_security(args.path, "delete")
        if error is not None:
            return ActionResult(success=False, error=error)

        # Fails closed in PH-040: delete requires human approval
        return ActionResult(
            success=False,
            error="File deletion is high risk and requires explicit interactive user approval (PH-050)",
        )
