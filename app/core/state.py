"""Project H Core AppState."""

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, StrictBool


class AppState(BaseModel):
    """In-memory state store for daemon and dashboard synchronization."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    status: Literal["DISABLED", "READY_WAKE", "WAKE_DETECTED", "RECORDING", "TRANSCRIBING", "ROUTING", "THINKING", "AWAITING_APPROVAL", "EXECUTING", "SPEAKING", "ERROR"] = "DISABLED"
    always_listen: StrictBool = False
    voice_output: StrictBool = False
    active_task_id: str | None = None
    pending_approval: StrictBool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    def get_state(self) -> dict[str, Any]:
        """Return full state dictionary."""
        return self.model_dump()

    def update(self, key: str, value: Any) -> None:
        """Update a state attribute."""
        if key not in type(self).model_fields:
            raise KeyError(key)
        setattr(self, key, value)
