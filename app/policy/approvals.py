"""Project H Policy Approval Models and Action Hashing."""

import hashlib
import hmac
import math
import re
import time
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.actions.schema import ActionRequest
from app.policy.risk import RiskLevel

_SHA256_HEX_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


def hash_canonical_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_action(action: ActionRequest) -> str:
    """Calculate deterministic SHA-256 lowercase hex digest for an ActionRequest."""
    canonical_bytes = action.to_canonical_bytes()
    return hash_canonical_bytes(canonical_bytes)


def verify_action(action: ActionRequest, expected_digest: str) -> bool:
    """Verify that an ActionRequest matches the expected SHA-256 digest."""
    if len(expected_digest) != 64:
        return False
    computed = hash_action(action)
    return hmac.compare_digest(computed.encode('utf-8'), expected_digest.lower().encode('utf-8'))


class ApprovalRequest(BaseModel):
    """Immutable security record for an action awaiting user approval."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action_hash: str
    action_id: str
    tool: str
    created_at: float
    expires_at: float
    action_snapshot: str
    risk_level: RiskLevel
    reason: str = ""
    request_id: str = ""
    workspace: str | None = None
    agent_id: str | None = None

    @classmethod
    def from_action(cls, action: ActionRequest, *, risk_level: RiskLevel, expires_in: float = 300.0) -> "ApprovalRequest":
        now = time.time()
        return cls(
            action_hash=hash_action(action),
            action_id=action.id,
            tool=action.tool,
            created_at=now,
            expires_at=now + expires_in,
            action_snapshot=action.to_canonical_json(),
            risk_level=risk_level,
            reason=action.reason,
            request_id=action.request_id,
            workspace=action.workspace,
            agent_id=action.agent_id
        )

    @field_validator("action_hash")
    @classmethod
    def validate_action_hash(cls, v: str) -> str:
        if not _SHA256_HEX_PATTERN.match(v):
            raise ValueError("action_hash must be a 64-character hexadecimal SHA-256 digest")
        return v.lower()

    @model_validator(mode="after")
    def validate_snapshot(self) -> "ApprovalRequest":
        if math.isnan(self.created_at) or math.isinf(self.created_at):
            raise ValueError("created_at must be a finite number")
        if math.isnan(self.expires_at) or math.isinf(self.expires_at):
            raise ValueError("expires_at must be a finite number")
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be strictly greater than created_at")
            
        try:
            req = ActionRequest.model_validate_json(self.action_snapshot)
        except Exception as e:
            raise ValueError(f"Invalid snapshot: {e}")
            
        canonical_str = req.to_canonical_json()
        if canonical_str != self.action_snapshot:
            raise ValueError("Snapshot is not canonically serialized")
            
        expected_digest = hash_canonical_bytes(canonical_str.encode("utf-8"))
        if not hmac.compare_digest(expected_digest, self.action_hash):
            raise ValueError("Hash does not match snapshot")
            
        if self.action_id != req.id:
            raise ValueError("Mismatched action_id")
        if self.tool != req.tool:
            raise ValueError("Mismatched tool")
        if self.reason != req.reason:
            raise ValueError("Mismatched reason")
        if self.request_id != req.request_id:
            raise ValueError("Mismatched request_id")
        if self.workspace != req.workspace:
            raise ValueError("Mismatched workspace")
        if self.agent_id != req.agent_id:
            raise ValueError("Mismatched agent_id")
            
        return self
