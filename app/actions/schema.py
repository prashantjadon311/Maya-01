"""Project H Actions & Tool Schemas."""

import json
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


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


class ActionResult(BaseModel):
    """Result of an action execution."""

    model_config = ConfigDict(extra="forbid")

    success: bool
    output: str = ""
    error: str | None = None


class ActionDefinition(BaseModel):
    """Definition of an action loaded from an action pack."""

    model_config = ConfigDict(extra="forbid")

    id: str
    enabled: bool = True
    phrases: list[str] = Field(default_factory=list)
    executor: Literal["process", "xdg_open", "browser", "file", "composite"]
    arguments: dict[str, Any] = Field(default_factory=dict)
    approval: Literal["preapproved", "ask_user", "always_ask", "deny"] = "preapproved"
    risk: Literal["low", "medium", "high", "critical"] = "low"
    timeout_seconds: int = 30


class ActionPack(BaseModel):
    """Versioned action pack containing multiple action definitions."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    pack_id: str
    label: str
    actions: list[ActionDefinition] = Field(default_factory=list)
