"""Project H Policy Engine and Decision Outcomes."""

from enum import Enum
from pathlib import Path
import os
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.actions.schema import ActionRequest
from app.core.config import FileRootConfig

NEVER_PREAPPROVE_EXECUTABLES = frozenset({
    "sudo", "su", "doas", "pkexec", "env",
    "sh", "bash", "dash", "zsh", "fish",
    "apt", "apt-get", "dpkg", "dnf", "yum", "rpm", "snap", "flatpak",
    "systemctl", "service"
})

class PreapprovalRule(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    id: str = Field(min_length=1)
    executable: str = Field(min_length=1)
    argv_prefix: tuple[str, ...]
    working_roots: tuple[str, ...] = Field(min_length=1)
    approval: Literal["preapproved"]
    timeout_seconds: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_executable(self) -> "PreapprovalRule":
        import os
        if os.path.basename(self.executable) in NEVER_PREAPPROVE_EXECUTABLES:
            raise ValueError(f"Executable {self.executable} cannot be preapproved")
        return self


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
    "~/.mozilla",
    "~/.local/share/keyrings",
    "~/.config/project-h",
]


class PolicyEngine:
    """Computes deterministic policy decisions for proposed actions."""

    def __init__(
        self,
        allowed_file_roots: list[FileRootConfig] | None = None,
        preapproved_rules: list[dict[str, Any] | PreapprovalRule] | None = None,
        permanently_denied_paths: list[str] | None = None,
    ) -> None:
        self.allowed_file_roots = []
        for root in (allowed_file_roots or []):
            if isinstance(root, str):
                raise ValueError("Raw string roots are no longer supported. Use FileRootConfig.")
            self.allowed_file_roots.append(root)

        parsed_rules = []
        for r in (preapproved_rules or []):
            if isinstance(r, dict):
                parsed_rules.append(PreapprovalRule.model_validate(r))
            else:
                parsed_rules.append(r)
        self.preapproved_rules = parsed_rules
        
        custom_paths = set(permanently_denied_paths) if permanently_denied_paths else set()
        all_denied = set(DEFAULT_SENSITIVE_PATHS).union(custom_paths)
        
        self.permanently_denied_paths = [
            str(Path(os.path.normpath(Path(p).expanduser())).resolve())
            for p in all_denied
        ]

    def evaluate(self, action: ActionRequest) -> PolicyDecision:
        """Evaluate action against configured policy rules and security invariants."""
        # 1. Unknown or unsupported tool fails closed
        if action.tool not in SUPPORTED_TOOLS:
            return PolicyDecision.DENY

        # 2. Terminal commands policy check
        if action.tool == "process.run":
            argv = action.arguments.get("argv")
            if not isinstance(argv, list) or not argv:
                return PolicyDecision.DENY
            for arg in argv:
                if not isinstance(arg, str) or not arg.strip():
                    return PolicyDecision.DENY

            executable = argv[0]
            exec_basename = os.path.basename(executable)
            if exec_basename in NEVER_PREAPPROVE_EXECUTABLES:
                return PolicyDecision.ASK_USER

        # 3. File actions policy check
        if action.tool.startswith("file."):
            path_str = action.arguments.get("path")
            if not path_str:
                return PolicyDecision.DENY

            target_path = Path(os.path.normpath(Path(path_str).expanduser())).resolve()

            # Check permanently denied sensitive locations
            for denied_str in self.permanently_denied_paths:
                denied_path = Path(denied_str)
                if target_path == denied_path or denied_path in target_path.parents:
                    return PolicyDecision.DENY

            # Credential check inside any allowed project roots
            basename = target_path.name
            if basename == ".env" or basename.startswith(".env."):
                return PolicyDecision.DENY

            # Check allowed roots containment
            in_allowed_root = False
            for root_config in self.allowed_file_roots:
                root_path = Path(os.path.normpath(Path(root_config.path).expanduser())).resolve()
                if target_path == root_path or root_path in target_path.parents:
                    if action.tool == "file.read" and not root_config.read:
                        continue
                    if action.tool == "file.list" and not root_config.read:
                        continue
                    if action.tool == "file.write" and not root_config.write:
                        continue
                    if action.tool == "file.delete" and not root_config.delete:
                        continue
                        
                    in_allowed_root = True
                    break

            if not in_allowed_root:
                return PolicyDecision.DENY

        # 4. High-risk operations are NEVER silently pre-approved in V1
        if action.risk_hint in ("high", "critical") or action.tool == "file.delete":
            return PolicyDecision.ASK_USER

        # 5. Check structured preapproval rules
        for rule in self.preapproved_rules:
            # All preapproval rules are currently constrained to process.run by schema/contract
            if action.tool != "process.run":
                continue

            argv = action.arguments.get("argv")
            # We already validated argv above, so we know it's a non-empty list of strings
            if not argv:
                continue

            executable = argv[0]

            if rule.executable != executable:
                continue

            command_args = argv[1:] if len(argv) > 1 else []
            if command_args[:len(rule.argv_prefix)] != list(rule.argv_prefix):
                continue

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
