"""Project H Actions & Tool Schemas."""

import json
from typing import Any, Literal
import math
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator



def validate_canonical_json(val: Any) -> Any:
    if val is None:
        return val
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            raise ValueError("NaN and Infinity are not allowed in canonical JSON")
        return val
    if isinstance(val, str):
        return val
    if isinstance(val, list):
        return [validate_canonical_json(item) for item in val]
    if isinstance(val, dict):
        for k in val.keys():
            if not isinstance(k, str):
                raise ValueError(f"Dictionary keys must be strings, got {type(k)}")
        return {k: validate_canonical_json(v) for k, v in val.items()}
    raise ValueError(f"Type {type(val)} is not allowed in canonical JSON")


class ActionRequest(BaseModel):
    """Model-proposed or deterministic action execution request."""

    model_config = ConfigDict(extra="forbid")

    id: str
    tool: str
    arguments: dict[str, Any]
    reason: str = ""
    request_id: str = ""
    workspace: str | None = None
    risk_hint: str | None = None
    agent_id: str | None = None

    def to_canonical_json(self) -> str:
        """Deterministic, compact canonical JSON representation for hashing/audit."""
        payload = {
            "agent_id": self.agent_id,
            "arguments": self.arguments,
            "id": self.id,
            "reason": self.reason,
            "request_id": self.request_id,
            "risk_hint": self.risk_hint,
            "tool": self.tool,
            "workspace": self.workspace,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)

    def to_canonical_bytes(self) -> bytes:
        """Deterministic UTF-8 encoded bytes of the canonical JSON representation."""
        return self.to_canonical_json().encode("utf-8")

    @model_validator(mode="after")
    def validate_json_args(self) -> "ActionRequest":
        validate_canonical_json(self.arguments)
        return self

class ActionResult(BaseModel):
    """Result of an action execution."""

    model_config = ConfigDict(extra="forbid")

    success: bool
    output: str = ""
    error: str | None = None
class ActionDefinition(BaseModel):
    """Definition of an action loaded from an action pack."""

    model_config = ConfigDict(extra="forbid", strict=True)

    id: str = Field(pattern=r"^[a-z0-9_]+\.[a-z0-9_]+$")
    enabled: bool = True
    phrases: list[str] = Field(default_factory=list)
    executor: Literal["process", "xdg_open", "browser", "file", "composite"]
    arguments: dict[str, Any] = Field(default_factory=dict)
    approval: Literal["preapproved", "ask_user", "always_ask", "deny"]
    risk: Literal["low", "medium", "high", "critical"]
    timeout_seconds: int = Field(default=30, gt=0)

    @field_validator("arguments", mode="before")
    @classmethod
    def validate_json_args(cls, value: Any) -> Any:
        return validate_canonical_json(value)

    @model_validator(mode="after")
    def validate_security_contract(self) -> "ActionDefinition":
        if self.risk in {"high", "critical"} and self.approval == "preapproved":
            raise ValueError(f"Action '{self.id}' with risk '{self.risk}' cannot be preapproved")
        return self

class ActionPack(BaseModel):
    """Versioned action pack containing multiple action definitions."""

    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal[1] = 1
    pack_id: str = Field(pattern=r"^[a-z0-9_]+$")
    label: str
    actions: list[ActionDefinition] = Field(default_factory=list)

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Pack label must not be empty")
        return value

    @model_validator(mode="after")
    def validate_unique_ids(self) -> "ActionPack":
        ids = [action.id for action in self.actions]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate action ID within pack")
        return self
