"""Project H Policy Engine and Decision Outcomes."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import os
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator

from app.actions.schema import ActionRequest
from app.core.config import FileRootConfig

from app.policy.paths import canonical_path
from app.policy.risk import RiskLevel, assess_risk, NEVER_PREAPPROVE_EXECUTABLES

TRUSTED_EXEC_DIRS: tuple[Path, ...] = (
    Path("/usr/bin"),
    Path("/bin"),
    Path("/usr/local/bin"),
)


def resolve_trusted_executable(
    executable_str: str,
    trusted_dirs: tuple[Path, ...] = TRUSTED_EXEC_DIRS,
) -> Path | None:
    """Resolve an executable securely without consulting ambient os.environ['PATH'].

    - If executable_str is an absolute path, verify it is resolved.
    - If executable_str is a basename without slashes, search trusted_dirs only.
    - Relative paths with slashes (e.g. './foo', 'bin/foo') are never resolved.
    """
    if not isinstance(executable_str, str) or not executable_str.strip() or "\x00" in executable_str:
        return None

    p = Path(executable_str)
    if p.is_absolute():
        try:
            resolved = p.resolve(strict=False)
            return resolved
        except (OSError, RuntimeError):
            return None
    elif "/" not in executable_str and "\\" not in executable_str:
        for d in trusted_dirs:
            candidate = (d / executable_str).resolve(strict=False)
            try:
                if candidate.exists() and candidate.is_file() and os.access(candidate, os.X_OK):
                    return candidate
            except (OSError, RuntimeError):
                continue
    return None


@dataclass(frozen=True)
class PolicyEvaluation:
    """Detailed policy evaluation outcome including trusted risk and matched rule constraints."""

    decision: "PolicyDecision"
    trusted_risk: RiskLevel
    matched_preapproval_rule: "PreapprovalRule | None" = None
    resolved_executable: Path | None = None


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
    timeout_seconds: int = Field(gt=0, strict=True)
    risk: Literal["low", "medium"]
    env_allowlist: tuple[str, ...] = ()
    network_allowed: StrictBool = False

    @field_validator("id", "executable")
    @classmethod
    def validate_nonempty(cls, value: str) -> str:
        if not value.strip() or "\x00" in value:
            raise ValueError("Value must be nonempty and contain no NUL")
        return value

    @field_validator("working_roots")
    @classmethod
    def validate_roots(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        for value in values:
            canonical_path(value)
        return values

    @model_validator(mode="after")
    def validate_executable(self) -> "PreapprovalRule":
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
        trusted_search_path: tuple[Path, ...] = TRUSTED_EXEC_DIRS,
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
        self.trusted_search_path = trusted_search_path
        
        custom_paths = set(permanently_denied_paths) if permanently_denied_paths else set()
        all_denied = set(DEFAULT_SENSITIVE_PATHS).union(custom_paths)
        
        self.permanently_denied_paths = [
            str(canonical_path(p))
            for p in all_denied
        ]

    def assess_risk(self, action: ActionRequest) -> RiskLevel:
        return assess_risk(action)

    def evaluate_detailed(self, action: ActionRequest) -> PolicyEvaluation:
        """Evaluate action against configured policy rules and security invariants, returning full evaluation context."""
        risk = self.assess_risk(action)

        # 1. Unknown or unsupported tool fails closed
        if action.tool not in SUPPORTED_TOOLS:
            return PolicyEvaluation(decision=PolicyDecision.DENY, trusted_risk=risk)

        # 2. Terminal commands policy check
        if action.tool == "process.run":
            argv = action.arguments.get("argv")
            if not isinstance(argv, list) or not argv:
                return PolicyEvaluation(decision=PolicyDecision.DENY, trusted_risk=risk)
            for arg in argv:
                if not isinstance(arg, str) or not arg.strip() or "\x00" in arg:
                    return PolicyEvaluation(decision=PolicyDecision.DENY, trusted_risk=risk)

            action_cwd = action.arguments.get("cwd", action.workspace)
            if "cwd" in action.arguments or action_cwd is not None:
                try:
                    canonical_path(action_cwd)
                except (ValueError, OSError, RuntimeError):
                    return PolicyEvaluation(decision=PolicyDecision.DENY, trusted_risk=risk)

            executable = argv[0]
            exec_basename = os.path.basename(executable)
            if exec_basename in NEVER_PREAPPROVE_EXECUTABLES:
                return PolicyEvaluation(decision=PolicyDecision.ASK_USER, trusted_risk=RiskLevel.HIGH)

        # 3. File actions policy check
        if action.tool.startswith("file."):
            path_str = action.arguments.get("path")
            try:
                target_path = canonical_path(path_str)
            except (ValueError, OSError, RuntimeError):
                return PolicyEvaluation(decision=PolicyDecision.DENY, trusted_risk=risk)

            # Check permanently denied sensitive locations
            for denied_str in self.permanently_denied_paths:
                denied_path = Path(denied_str)
                if target_path == denied_path or denied_path in target_path.parents:
                    return PolicyEvaluation(decision=PolicyDecision.DENY, trusted_risk=risk)

            # Credential check inside any allowed project roots
            basename = target_path.name
            if basename == ".env" or basename.startswith(".env."):
                return PolicyEvaluation(decision=PolicyDecision.DENY, trusted_risk=risk)

            # Check allowed roots containment
            in_allowed_root = False
            for root_config in self.allowed_file_roots:
                try:
                    root_path = canonical_path(root_config.path)
                except (ValueError, OSError, RuntimeError):
                    return PolicyEvaluation(decision=PolicyDecision.DENY, trusted_risk=risk)
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
                return PolicyEvaluation(decision=PolicyDecision.DENY, trusted_risk=risk)

        # 4. High-risk operations are NEVER silently pre-approved in V1
        if risk in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            return PolicyEvaluation(decision=PolicyDecision.ASK_USER, trusted_risk=risk)

        # 5. Check structured preapproval rules
        for rule in self.preapproved_rules:
            # All preapproval rules are currently constrained to process.run by schema/contract
            if action.tool != "process.run":
                continue

            argv = action.arguments.get("argv")
            if not argv:
                continue

            executable = argv[0]
            if rule.executable != executable:
                continue

            command_args = argv[1:] if len(argv) > 1 else []
            if command_args[:len(rule.argv_prefix)] != list(rule.argv_prefix):
                continue

            action_cwd = action.arguments.get("cwd", action.workspace)
            if not action_cwd:
                continue
            try:
                cwd_path = canonical_path(action_cwd)
                in_work_root = any(cwd_path.is_relative_to(canonical_path(r)) for r in rule.working_roots)
            except (ValueError, OSError, RuntimeError):
                return PolicyEvaluation(decision=PolicyDecision.DENY, trusted_risk=risk)
            if not in_work_root:
                continue

            resolved_exe = resolve_trusted_executable(executable, trusted_dirs=self.trusted_search_path)
            if resolved_exe is None:
                continue

            return PolicyEvaluation(
                decision=PolicyDecision.ALLOW_PREAPPROVED,
                trusted_risk=risk,
                matched_preapproval_rule=rule,
                resolved_executable=resolved_exe,
            )

        # Default fallback for valid actions requiring user confirmation
        return PolicyEvaluation(decision=PolicyDecision.ASK_USER, trusted_risk=risk)

    def evaluate(self, action: ActionRequest) -> PolicyDecision:
        """Evaluate action against configured policy rules and security invariants."""
        return self.evaluate_detailed(action).decision
