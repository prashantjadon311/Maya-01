"""Project H Policy Engine and Decision Outcomes."""

from enum import Enum
from pathlib import Path
from typing import Any

from app.actions.schema import ActionRequest


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
        allowed_file_roots: list[str] | None = None,
        preapproved_rules: list[dict[str, Any]] | None = None,
        permanently_denied_paths: list[str] | None = None,
    ) -> None:
        self.allowed_file_roots = allowed_file_roots or []
        self.preapproved_rules = preapproved_rules or []
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
            if executable == "sudo" or (argv and argv[0] == "sudo"):
                return PolicyDecision.ASK_USER

        # 3. File actions policy check
        if action.tool.startswith("file."):
            path_str = action.arguments.get("path")
            if not path_str:
                return PolicyDecision.DENY

            target_path = Path(path_str).expanduser()

            # Check permanently denied sensitive locations
            for denied_str in self.permanently_denied_paths:
                denied_path = Path(denied_str).expanduser()
                if target_path == denied_path or denied_path in target_path.parents:
                    return PolicyDecision.DENY

            # Check allowed roots containment
            in_allowed_root = False
            for root_str in self.allowed_file_roots:
                root_path = Path(root_str).expanduser()
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
            if rule.get("risk") in ("high", "critical"):
                continue

            if rule.get("tool") and rule["tool"] != action.tool:
                continue

            # Process execution rule matching
            if action.tool == "process.run":
                argv = action.arguments.get("argv", [])
                executable = argv[0] if argv else action.arguments.get("executable", "")

                rule_exec = rule.get("executable")
                if rule_exec and rule_exec != executable:
                    continue

                rule_prefix = rule.get("argv_prefix", [])
                # If rule requires argv prefix, check command args
                if rule_prefix:
                    command_args = argv[1:] if len(argv) > 1 else []
                    if command_args[:len(rule_prefix)] != rule_prefix:
                        continue

                # Check working root containment if specified by rule
                working_roots = rule.get("working_roots", [])
                if working_roots:
                    action_cwd = action.arguments.get("cwd") or action.workspace
                    if not action_cwd:
                        continue
                    cwd_path = Path(action_cwd).expanduser()
                    in_work_root = any(
                        cwd_path == Path(r).expanduser() or Path(r).expanduser() in cwd_path.parents
                        for r in working_roots
                    )
                    if not in_work_root:
                        continue

                return PolicyDecision.ALLOW_PREAPPROVED

        # Default fallback for valid actions requiring user confirmation
        return PolicyDecision.ASK_USER
