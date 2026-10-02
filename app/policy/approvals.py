"""Project H Policy Approval Models and Action Hashing."""

import hashlib
import re
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
    return hash_action(action) == expected_digest.lower()


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

    @field_validator("action_hash")
    @classmethod
    def validate_action_hash(cls, v: str) -> str:
        if not _SHA256_HEX_PATTERN.match(v):
            raise ValueError("action_hash must be a 64-character hexadecimal SHA-256 digest")
        return v.lower()

    @model_validator(mode="after")
    def validate_expiry(self) -> "ApprovalRequest":
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be strictly greater than created_at")
        return self
