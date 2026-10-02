"""Project H Core Events & Request Models."""

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class CommandRequest(BaseModel):
    """Normalized input request from voice, dashboard, or CLI."""

    model_config = ConfigDict(extra="forbid")

    text: str
    source: Literal["voice", "dashboard", "cli"] = "dashboard"
    metadata: dict[str, Any] = Field(default_factory=dict)
