"""Project H Core AppState."""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class AppState(BaseModel):
    """In-memory state store for daemon and dashboard synchronization."""

    model_config = ConfigDict(extra="forbid")

    status: str = "READY"
    always_listen: bool = False
    voice_output: bool = False
    active_task_id: str | None = None
    pending_approval: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    def get_state(self) -> dict[str, Any]:
        """Return full state dictionary."""
        return self.model_dump()

    def update(self, key: str, value: Any) -> None:
        """Update a state attribute."""
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            self.metadata[key] = value
