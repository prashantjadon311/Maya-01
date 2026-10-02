"""Project H Policy Engine and Decision Outcomes."""

from enum import Enum
from pathlib import Path
import os
from typing import Any
from pydantic import BaseModel, ConfigDict

from app.actions.schema import ActionRequest
from app.core.config import FileRootConfig

class PreapprovalRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str | None = None
    tool: str | None = None
    executable: str | None = None
    argv_prefix: list[str] | None = None
    working_roots: list[str] | None = None
    risk: str | None = None
    approval: str | None = None


class PolicyDecision(str, Enum):
    """Canonical 3-state policy outcome for Project H actions."""

    ALLOW_PREAPPROVED = "ALLOW_PREAPPROVED"
    ASK_USER = "ASK_USER"
    DENY = "DENY"


# Recognized supported tools for V1
SUPPORTED_TOOLS = {
    "process.run",
    "app.open",
    "file.read",
    "file.write",
    "file.list",
    "file.delete",
    "browser.open",
    "browser.read",
    "browser.click",
    "browser.type",
    "task.create",
}

# Sensitive system locations permanently denied by policy
DEFAULT_SENSITIVE_PATHS = [
    "/etc",
    "/root",
    "/proc",
    "/sys",
    "/dev",
    "~/.ssh",
    "~/.gnupg",
]


class PolicyEngine:
    """Computes deterministic policy decisions for proposed actions."""

    def __init__(
        self,
        allowed_file_roots: list[str | FileRootConfig] | None = None,
        preapproved_rules: list[dict[str, Any] | PreapprovalRule] | None = None,
        permanently_denied_paths: list[str] | None = None,
    ) -> None:
        self.allowed_file_roots = allowed_file_roots or []
        parsed_rules = []
        for r in (preapproved_rules or []):
            if isinstance(r, dict):
                try:
                    parsed_rules.append(PreapprovalRule.model_validate(r))
                except Exception:
                    pass # ignore invalid rules
            else:
                parsed_rules.append(r)
        self.preapproved_rules = parsed_rules
        self.permanently_denied_paths = permanently_denied_paths or DEFAULT_SENSITIVE_PATHS

    def evaluate(self, action: ActionRequest) -> PolicyDecision:
        """Evaluate action against configured policy rules and security invariants."""
        # 1. Unknown or unsupported tool fails closed
        if action.tool not in SUPPORTED_TOOLS:
            return PolicyDecision.DENY

        # 2. Terminal commands policy check
        if action.tool == "process.run":
            argv = action.arguments.get("argv", [])
            executable = argv[0] if argv else action.arguments.get("executable", "")

            # sudo / privileged command always resolves to ASK_USER (never ALLOW_PREAPPROVED, not DENY)
            privileged = {"sudo", "su", "doas", "pkexec", "apt", "systemctl", "dpkg", "dnf", "yum"}
            if executable in privileged:
                return PolicyDecision.ASK_USER
            if executable == "env" and len(argv) > 1 and argv[1] in privileged:
                return PolicyDecision.ASK_USER

        # 3. File actions policy check
        if action.tool.startswith("file."):
            path_str = action.arguments.get("path")
            if not path_str:
                return PolicyDecision.DENY

            target_path = Path(os.path.normpath(Path(path_str).expanduser()))

            # Check permanently denied sensitive locations
            for denied_str in self.permanently_denied_paths:
                denied_path = Path(os.path.normpath(Path(denied_str).expanduser()))
                if target_path == denied_path or denied_path in target_path.parents:
                    return PolicyDecision.DENY

            # Check allowed roots containment
            in_allowed_root = False
            for root_config in self.allowed_file_roots:
                if isinstance(root_config, FileRootConfig):
                    root_path = Path(os.path.normpath(Path(root_config.path).expanduser()))
                    if target_path == root_path or root_path in target_path.parents:
                        if action.tool == "file.read" and not root_config.read:
                            continue
                        if action.tool == "file.write" and not root_config.write:
                            continue
                        if action.tool == "file.delete" and not root_config.delete:
                            continue
                        in_allowed_root = True
                        break
                else:
                    root_path = Path(os.path.normpath(Path(root_config).expanduser()))
                    if target_path == root_path or root_path in target_path.parents:
                        in_allowed_root = True
                        break

            if not in_allowed_root:
                return PolicyDecision.DENY

        # 4. High-risk operations are NEVER silently pre-approved in V1
        if action.risk_hint in ("high", "critical") or action.tool == "file.delete":
            return PolicyDecision.ASK_USER

        # 5. Check structured preapproval rules
        for rule in self.preapproved_rules:
            # Rule cannot preapprove high/critical risk
            if rule.risk in ("high", "critical"):
                continue

            if rule.tool and rule.tool != action.tool:
                continue

            # Process execution rule matching
            if action.tool == "process.run":
                argv = action.arguments.get("argv", [])
                executable = argv[0] if argv else action.arguments.get("executable", "")

                if rule.executable and rule.executable != executable:
                    continue

                # If rule requires argv prefix, check command args
                if rule.argv_prefix:
                    command_args = argv[1:] if len(argv) > 1 else []
                    if command_args[:len(rule.argv_prefix)] != rule.argv_prefix:
                        continue

                # Check working root containment if specified by rule
                if rule.working_roots:
                    action_cwd = action.arguments.get("cwd") or action.workspace
                    if not action_cwd:
                        continue
                    cwd_path = Path(os.path.normpath(Path(action_cwd).expanduser()))
                    in_work_root = any(
                        cwd_path == Path(os.path.normpath(Path(r).expanduser())) or Path(os.path.normpath(Path(r).expanduser())) in cwd_path.parents
                        for r in rule.working_roots
                    )
                    if not in_work_root:
                        continue

                return PolicyDecision.ALLOW_PREAPPROVED

        # Default fallback for valid actions requiring user confirmation
        return PolicyDecision.ASK_USER
