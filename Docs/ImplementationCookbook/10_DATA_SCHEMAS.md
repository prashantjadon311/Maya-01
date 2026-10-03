# Maya Data Schemas & Strict Contract Specifications

All data schemas across Maya are frozen using **Pydantic v2** with strict parsing and forbidden extra fields. In accordance with the project security guidelines, `frozen=True` is not relied upon for deep immutability; nested mutable structures are defended with defensive copies or converted to immutable tuples.

```python
model_config = ConfigDict(
    strict=True,
    extra="forbid",
)
```

---

## 1. Approval Schemas (`app/policy/broker.py`)

```python
class ApprovalGrant(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    
    grant_id: str  # UUIDv4
    action_hash: str  # 64-char lowercase hex SHA-256
    created_at: float  # time.monotonic()
    expires_at: float  # time.monotonic() + timeout
    risk: RiskLevel
    status: Literal["PENDING", "GRANTED", "CONSUMED", "EXPIRED", "DENIED"]
```

---

## 2. AI Provider Schemas (`app/ai/nvidia.py`)

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
```

---

## 3. Router & Agent Schemas (`app/core/command_router.py`, `app/agents/model.py`)

```python
class CommandRoutingDecision(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    mode: Literal["EXACT_MATCH", "BUILTIN", "STRUCTURED", "AI_REASONING"]
    action_request: ActionRequest | None = None
    confidence: float = 1.0

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

## 4. Browser Native Protocol Schemas (`app/browser/protocol.py`)

```python
class BrowserCommand(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    tab_id: int
    command_type: Literal["OPEN", "READ", "CLICK", "TYPE", "SUBMIT"]
    target_url: str
    selector: str | None = None
    value: str | None = None

class BrowserResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None
```

---

## 5. Resource Monitoring Schema (`app/core/lifecycle.py`)

```python
class MemorySnapshot(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    current_rss_mb: float
    peak_rss_mb: float
    limit_mb: float = 300.0
    status: Literal["OK", "WARNING", "EXCEEDED"]
```
