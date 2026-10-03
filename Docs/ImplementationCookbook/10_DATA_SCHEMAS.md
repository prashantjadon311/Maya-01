# Maya Data Schemas & Strict Contract Specifications

All data schemas across Maya are frozen using **Pydantic v2** with strict parsing and forbidden extra fields. In accordance with project security guidelines, `frozen=True` is not relied upon for deep immutability; nested mutable structures are defended with defensive copies or converted to immutable tuples.

```python
model_config = ConfigDict(
    strict=True,
    extra="forbid",
)
```

---

## 1. Approval & Authorization Schemas (`app/policy/broker.py`)

```python
from enum import Enum
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from app.actions.schema import ActionRequest
from app.policy.risk import RiskLevel


class PopupDecision(str, Enum):
    ALLOW_ONCE = "ALLOW_ONCE"
    DENY = "DENY"


class PendingApproval(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    pending_id: str
    action_hash: str  # 64-char lowercase hex SHA-256
    created_at: float  # time.monotonic()
    expires_at: float  # time.monotonic() + timeout
    reason: str
    risk: RiskLevel
    request: ActionRequest


class ApprovalGrant(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    grant_id: str  # UUIDv4
    action_hash: str  # 64-char lowercase hex SHA-256
    created_at: float
    expires_at: float
    risk: RiskLevel
    source: Literal["HUMAN_ALLOW_ONCE"] = "HUMAN_ALLOW_ONCE"


class ProcessExecutionConstraints(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    resolved_executable: Path
    exact_argv: tuple[str, ...]
    cwd: Path
    timeout_seconds: int
    env_allowlist: tuple[str, ...]
    network_allowed: bool


class ExecutionAuthorization(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    source: Literal["PREAPPROVED", "HUMAN_ALLOW_ONCE"]
    action_hash: str
    trusted_risk: RiskLevel
    process_constraints: ProcessExecutionConstraints | None = None
```

---

## 2. Audit Event Schema (`app/storage/schema.py`)

```python
class AuditEvent(BaseModel):
    """Typed allowlisted audit event containing metadata only.

    SECURITY INVARIANT:
    Never persists stdout, stderr, raw arguments, env vars, prompts,
    exceptions, or DOM HTML content.
    """
    model_config = ConfigDict(strict=True, extra="forbid")

    timestamp: float
    request_id: str
    actor: str  # "voice", "dashboard", "agent", "hotkey"
    tool: str   # "process.run", "file.read", "browser.click", etc.
    policy_decision: Literal["ALLOW_PREAPPROVED", "ASK_USER", "DENY"]
    approval_result: Literal["NOT_REQUIRED", "HUMAN_ALLOW_ONCE", "DENIED", "TIMEOUT"] | None = None
    target: str | None = None  # sanitized executable or file path
    result_code: int | None = None
    duration_ms: float
    error_code: str | None = None
```

---

## 3. Audio Segment Schema (`app/voice/audio.py`)

```python
class CommandAudioSegment(BaseModel):
    """Internal trusted post-wake command audio segment.

    SECURITY INVARIANT:
    Created by CommandRecorder post-wake only. Released immediately
    post-transcription. Never contains pre-wake ambient audio.
    """
    model_config = ConfigDict(strict=True, extra="forbid")

    segment_id: str
    sample_rate: int = 16000
    pcm_data: bytes
    start_timestamp: float
    end_timestamp: float
```

---

## 4. AI Provider Schemas (`app/ai/base.py`, `app/ai/nvidia.py`)

```python
class ToolFunction(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    name: str
    arguments: str  # JSON-encoded string


class ToolCall(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    id: str
    type: Literal["function"]
    function: ToolFunction


class ChatMessage(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    role: Literal["system", "user", "assistant", "tool"]
    content: str = ""
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None


class ChatResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    content: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    finish_reason: Literal["stop", "tool_calls", "length", "error"]


class ChatChunk(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    delta_content: str = ""
    tool_call_deltas: list[ToolCall] = Field(default_factory=list)
```

---

## 5. Router & Agent Schemas (`app/core/command_router.py`, `app/agents/model.py`)

```python
class CommandRoutingDecision(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    mode: Literal["EXACT_MATCH", "BUILTIN", "STRUCTURED", "AI_REASONING"]
    action_request: ActionRequest | None = None


class AgentTask(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    task_id: str
    objective: str
    workspace_root: str
    max_steps: int = Field(default=15, le=30)
    max_budget_calls: int = Field(default=20, le=50)


class AgentTaskResult(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    task_id: str
    success: bool
    step_count: int
    api_calls_used: int
    evidence: list[str] = Field(default_factory=list)
    error: str | None = None
```

---

## 6. Browser Native Protocol Schemas (`app/browser/protocol.py`)

```python
class BrowserCommand(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    request_id: str
    tab_id: int
    command_type: Literal["OPEN", "READ", "CLICK", "TYPE", "SUBMIT"]
    target_url: str
    selector: str | None = None
    value: str | None = None


class BrowserResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    request_id: str
    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None
```

---

## 7. Resource Monitoring Schema (`app/core/lifecycle.py`)

```python
class MemorySnapshot(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    current_rss_mb: float
    peak_rss_mb: float
    limit_mb: float = 300.0
    status: Literal["OK", "WARNING", "EXCEEDED"]
```
