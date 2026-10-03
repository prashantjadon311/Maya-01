"""Project H File Executor.

Enforces canonicalization, root containment, capability checks, atomic writing,
and prevents traversal/symlink escapes. Rechecks all security invariants immediately before I/O.
Uses file-descriptor anchored I/O for relative paths under matched roots to prevent TOCTOU symlink swaps.
"""

import json
import os
from pathlib import Path
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
from app.policy.engine import DEFAULT_SENSITIVE_PATHS, PolicyDecision, PolicyEvaluation
from app.policy.paths import canonical_path


def _open_dirfd_under_root(root_path: Path, relative_components: tuple[str, ...]) -> int:
    """Open directory descriptor anchored under root_path following relative_components securely without symlinks."""
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    curr_fd = os.open(str(root_path), flags)
    for comp in relative_components:
        try:
            next_fd = os.open(comp, flags, dir_fd=curr_fd)
        except Exception:
            os.close(curr_fd)
            raise
        os.close(curr_fd)
        curr_fd = next_fd
    return curr_fd


def _open_parent_dirfd(root_path: Path, relative_components: tuple[str, ...]) -> tuple[int, str]:
    """Open parent directory descriptor under root_path for relative_components and return (parent_fd, leaf_name)."""
    if not relative_components:
        raise ValueError("relative_components must not be empty for parent dirfd")
    parent_components = relative_components[:-1]
    leaf_name = relative_components[-1]
    parent_fd = _open_dirfd_under_root(root_path, parent_components)
    return parent_fd, leaf_name


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

    def _verify_path_security(self, path_str: str, required_cap: str) -> tuple[Path | None, Path | None, str | None]:
        """Canonicalize path and verify against sensitive defaults and allowed root capabilities."""
        try:
            target = canonical_path(path_str)
        except Exception as exc:
            return None, None, f"Malformed path '{path_str}': {exc}"

        # Sensitive paths check
        for denied_str in self.permanently_denied_paths:
            denied_path = Path(denied_str)
            if target == denied_path or denied_path in target.parents:
                return None, None, f"Access to sensitive path '{target}' is permanently denied"

        # Credential file check (.env)
        if target.name == ".env" or target.name.startswith(".env."):
            return None, None, "Access to credential files (.env) is denied"

        # Root containment and capability check
        in_allowed_root = False
        has_capability = False
        matched_root: Path | None = None
        for root in self.allowed_roots:
            try:
                root_path = canonical_path(root.path)
            except Exception:
                continue
            if target == root_path or root_path in target.parents:
                in_allowed_root = True
                if required_cap == "read" and root.read:
                    has_capability = True
                    matched_root = root_path
                    break
                if required_cap == "write" and root.write:
                    has_capability = True
                    matched_root = root_path
                    break
                if required_cap == "delete" and root.delete:
                    has_capability = True
                    matched_root = root_path
                    break

        if not in_allowed_root:
            return None, None, f"Path '{target}' is outside configured allowed file roots"
        if not has_capability or matched_root is None:
            return None, None, f"Allowed root does not grant '{required_cap}' capability for '{target}'"

        return target, matched_root, None

    async def execute(self, action: ActionRequest, context: Any = None) -> ActionResult:
        """Route to appropriate file operation based on action.tool."""
        if not isinstance(context, PolicyEvaluation) or context.decision != PolicyDecision.ALLOW_PREAPPROVED:
            return ActionResult(
                success=False,
                error="File execution denied: requires valid preapproved PolicyEvaluation context",
            )
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
        """Execute file.read operation using descriptor-bound open with O_NOFOLLOW."""
        try:
            args = FileReadArgs.model_validate(action.arguments)
        except Exception as exc:
            return ActionResult(success=False, error=f"Invalid file.read arguments: {exc}")

        target, matched_root, error = self._verify_path_security(args.path, "read")
        if error is not None:
            return ActionResult(success=False, error=error)
        assert target is not None and matched_root is not None

        rel_parts = target.relative_to(matched_root).parts
        if not rel_parts:
            return ActionResult(success=False, error=f"File not found or not a regular file: {target}")

        try:
            parent_fd, leaf_name = _open_parent_dirfd(matched_root, rel_parts)
        except OSError as exc:
            return ActionResult(success=False, error=f"Failed to open parent directory safely: {exc}")

        try:
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
            try:
                fd = os.open(leaf_name, flags, dir_fd=parent_fd)
            except OSError as exc:
                return ActionResult(success=False, error=f"Failed to open file safely (symlink or access error): {exc}")

            try:
                st = os.fstat(fd)
                import stat
                if not stat.S_ISREG(st.st_mode):
                    return ActionResult(success=False, error=f"File not found or not a regular file: {target}")
                if st.st_size > args.max_bytes:
                    return ActionResult(
                        success=False,
                        error=f"File size ({st.st_size} bytes) exceeds max limit ({args.max_bytes} bytes)",
                    )

                with os.fdopen(fd, "rb", closefd=True) as f:
                    data = f.read(args.max_bytes + 1)
                if len(data) > args.max_bytes:
                    return ActionResult(success=False, error=f"File content exceeds max limit ({args.max_bytes} bytes)")

                content = data.decode("utf-8", errors="replace")
                return ActionResult(success=True, output=content)
            except Exception as exc:
                return ActionResult(success=False, error=f"Failed to read file: {exc}")
        finally:
            os.close(parent_fd)

    async def execute_list(self, action: ActionRequest) -> ActionResult:
        """Execute file.list operation without following child symlinks."""
        try:
            args = FileListArgs.model_validate(action.arguments)
        except Exception as exc:
            return ActionResult(success=False, error=f"Invalid file.list arguments: {exc}")

        target, matched_root, error = self._verify_path_security(args.path, "read")
        if error is not None:
            return ActionResult(success=False, error=error)
        assert target is not None and matched_root is not None

        if target.is_symlink():
            return ActionResult(success=False, error="Target is a symlink: directory listing through symlinks is denied")

        rel_parts = target.relative_to(matched_root).parts
        try:
            if not rel_parts:
                dir_fd = os.open(str(matched_root), os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0))
            else:
                dir_fd = _open_dirfd_under_root(matched_root, rel_parts)
        except OSError as exc:
            return ActionResult(success=False, error=f"Failed to open directory safely: {exc}")

        try:
            st = os.fstat(dir_fd)
            import stat
            if not stat.S_ISDIR(st.st_mode):
                return ActionResult(success=False, error=f"Target is not an existing directory: {target}")

            entries = []
            with os.scandir(dir_fd) as scanner:
                sorted_entries = sorted(list(scanner), key=lambda e: e.name)
                for idx, entry in enumerate(sorted_entries):
                    if idx >= args.max_entries:
                        break
                    is_sym = entry.is_symlink()
                    is_dir = False if is_sym else entry.is_dir(follow_symlinks=False)
                    is_file = False if is_sym else entry.is_file(follow_symlinks=False)
                    entry_size = None
                    if is_file:
                        try:
                            entry_size = entry.stat(follow_symlinks=False).st_size
                        except OSError:
                            pass
                    entries.append({
                        "name": entry.name,
                        "is_dir": is_dir,
                        "size": entry_size,
                    })
            return ActionResult(success=True, output=json.dumps(entries))
        except Exception as exc:
            return ActionResult(success=False, error=f"Failed to list directory: {exc}")
        finally:
            os.close(dir_fd)

    async def execute_write(self, action: ActionRequest) -> ActionResult:
        """Execute atomic file.write operation with fsync and symlink protection."""
        try:
            args = FileWriteArgs.model_validate(action.arguments)
        except Exception as exc:
            return ActionResult(success=False, error=f"Invalid file.write arguments: {exc}")

        target, matched_root, error = self._verify_path_security(args.path, "write")
        if error is not None:
            return ActionResult(success=False, error=error)
        assert target is not None and matched_root is not None

        # Re-check symlink on the target path: never write through a symlink
        raw_path = Path(args.path).expanduser()
        if raw_path.is_symlink() or target.is_symlink():
            return ActionResult(success=False, error="Writing through a symlink is strictly forbidden")

        rel_parts = target.relative_to(matched_root).parts
        if not rel_parts:
            return ActionResult(success=False, error="Writing directly to allowed root directory path is forbidden")

        try:
            parent_fd, leaf_name = _open_parent_dirfd(matched_root, rel_parts)
        except OSError as exc:
            return ActionResult(success=False, error=f"Parent directory does not exist or access error: {exc}")

        try:
            import stat
            # Check if leaf_name is already a symlink in parent_fd
            try:
                st = os.lstat(leaf_name, dir_fd=parent_fd)
                if stat.S_ISLNK(st.st_mode):
                    return ActionResult(success=False, error="Writing through a symlink is strictly forbidden")
            except OSError:
                pass

            payload: bytes
            if isinstance(args.content, str):
                payload = args.content.encode("utf-8")
            else:
                payload = args.content

            # Create temporary file inside parent_fd directory descriptor
            temp_name = f".tmp_projh_{os.urandom(8).hex()}"
            flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
            try:
                temp_fd = os.open(temp_name, flags, 0o600, dir_fd=parent_fd)
            except OSError as exc:
                return ActionResult(success=False, error=f"Failed to create temp file: {exc}")

            try:
                os.write(temp_fd, payload)
                os.fsync(temp_fd)
            finally:
                os.close(temp_fd)

            # TOCTOU revalidation immediately before replace
            rechecked, _, recheck_err = self._verify_path_security(str(target), "write")
            if recheck_err is not None or rechecked != target:
                os.unlink(temp_name, dir_fd=parent_fd)
                return ActionResult(success=False, error="Target path changed during write")

            if raw_path.is_symlink() or target.is_symlink():
                os.unlink(temp_name, dir_fd=parent_fd)
                return ActionResult(success=False, error="Writing through a symlink is strictly forbidden")

            try:
                st2 = os.lstat(leaf_name, dir_fd=parent_fd)
                if stat.S_ISLNK(st2.st_mode):
                    os.unlink(temp_name, dir_fd=parent_fd)
                    return ActionResult(success=False, error="Writing through a symlink is strictly forbidden")
            except OSError:
                pass

            os.replace(temp_name, leaf_name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
            return ActionResult(success=True, output=f"Successfully wrote {len(payload)} bytes to {target.name}")
        except Exception as exc:
            try:
                os.unlink(temp_name, dir_fd=parent_fd)
            except OSError:
                pass
            return ActionResult(success=False, error=f"Atomic write failed: {exc}")
        finally:
            os.close(parent_fd)

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

        _target, _, error = self._verify_path_security(args.path, "delete")
        if error is not None:
            return ActionResult(success=False, error=error)

        # Fails closed in PH-040: delete requires human approval
        return ActionResult(
            success=False,
            error="File deletion is high risk and requires explicit interactive user approval (PH-050)",
        )
