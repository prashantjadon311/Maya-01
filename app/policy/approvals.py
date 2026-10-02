"""Project H Policy Approval Models and Action Hashing."""

import hashlib
import hmac
import math
import re
import time
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.actions.schema import ActionRequest

_SHA256_HEX_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


def hash_action(action: ActionRequest) -> str:
    """Calculate deterministic SHA-256 lowercase hex digest for an ActionRequest."""
    canonical_bytes = action.to_canonical_bytes()
    return hashlib.sha256(canonical_bytes).hexdigest()


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
    reason: str = ""
    request_id: str = ""
    workspace: str | None = None
    agent_id: str | None = None

    @classmethod
    def from_action(cls, action: ActionRequest, expires_in: float = 300.0) -> "ApprovalRequest":
        now = time.time()
        return cls(
            action_hash=hash_action(action),
            action_id=action.id,
            tool=action.tool,
            created_at=now,
            expires_at=now + expires_in,
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
    def validate_expiry(self) -> "ApprovalRequest":
        if math.isnan(self.created_at) or math.isinf(self.created_at):
            raise ValueError("created_at must be a finite number")
        if math.isnan(self.expires_at) or math.isinf(self.expires_at):
            raise ValueError("expires_at must be a finite number")
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be strictly greater than created_at")
        return self
