# Maya Public Interfaces & Canonical Signatures

Every public interface across Maya phases PH-050 through PH-180 is frozen herein. Subsystems must adhere strictly to these method signatures, input validations, preconditions, postconditions, and bounded resource constraints.

---

## 1. Approval Broker & Security Interfaces (PH-050)

### `ApprovalBroker.request_decision`
- **File:** `app/policy/broker.py`
- **Signature:** `async def request_decision(self, req: ActionRequest, reason: str, risk: RiskLevel) -> PopupDecision`
- **Inputs:** `req: ActionRequest`, `reason: str`, `risk: RiskLevel`
- **Preconditions:** `req` is a validated Pydantic model with immutable canonical payload; `risk` in `(RiskLevel.MEDIUM, RiskLevel.HIGH)`.
- **Postconditions:** Registers in-memory `PendingApproval` (NOT a grant) with UUID, 60s timeout, and `action_hash = sha256(canonical_bytes)`. Awaits user decision from `PopupBackend`. If user chooses `ALLOW_ONCE`, mints single-use `ApprovalGrant(source="HUMAN_ALLOW_ONCE")` and returns `PopupDecision.ALLOW_ONCE`. On denial, timeout, or error, fails closed to `PopupDecision.DENY` and mints NO grant.
- **Resource Bounds:** Max 10 concurrent pending requests in memory. When capacity is full, fails closed / busy (never evicts an active pending approval).
- **Timeout:** 60.0s. Fails closed on timeout to `DENY`.
- **Cancellation:** Kills popup child process and clears pending request.

### `ApprovalBroker.consume_grant`
- **File:** `app/policy/broker.py`
- **Signature:** `async def consume_grant(self, grant_id: str, request: ActionRequest) -> bool`
- **Inputs:** `grant_id: str`, `request: ActionRequest`
- **Algorithm:** Inside one `asyncio.Lock`:
  1. Look up `grant_id` in in-memory grant store.
  2. Verify expiry (`time.monotonic() < expires_at`).
  3. Recompute SHA-256 hash of canonical bytes of `request`.
  4. Constant-time comparison `hmac.compare_digest(grant.action_hash, request_hash)`.
  5. If expired, missing, or hash mismatch: pop grant (if present) and return `False`.
  6. If valid: pop grant atomically from memory and return `True`.
- **Security Invariant:** PENDING approvals are NEVER consumable. A consumed grant cannot be reused (second consume returns `False`).

---

## 2. Post-Approval Execution Authorization (PH-050)

### `ExecutionAuthorization`
- **File:** `app/policy/broker.py` / `app/executors/base.py`
- **Structure:**
  ```python
  @dataclass(frozen=True)
  class ExecutionAuthorization:
      source: Literal["PREAPPROVED", "HUMAN_ALLOW_ONCE"]
      action_hash: str
      trusted_risk: RiskLevel
      process_constraints: ProcessExecutionConstraints | None = None
  ```
- **Constructor Gate:** Constructed solely by `ActionDispatcher` after policy evaluation and (if required) successful single-use `consume_grant()`.
- **Executor Contract:** Safe executors (`ProcessExecutor`, `FileExecutor`, `XdgExecutor`) accept `ExecutionAuthorization` as trusted execution context. Human approval never bypasses hard execution constraints (forbidden paths, traversal protection, timeouts, bounded output, argv schema).

---

## 3. NVIDIA AI Provider Interfaces (PH-060)

### `AIProvider` Protocol
- **File:** `app/ai/base.py`
- **Definition:**
  ```python
  class AIProvider(Protocol):
      async def complete(self, messages: list[ChatMessage], tools: list[ToolDefinition] | None = None) -> ChatResponse: ...
      async def stream_chat(self, messages: list[ChatMessage], tools: list[ToolDefinition] | None = None) -> AsyncIterator[ChatChunk]: ...
      async def aclose(self) -> None: ...
  ```

### `NvidiaProvider.complete` & `stream_chat`
- **File:** `app/ai/nvidia.py`
- **Signature:** `async def complete(self, messages: list[ChatMessage], tools: list[ToolDefinition] | None = None) -> ChatResponse`
- **Streaming Signature:** `async def stream_chat(self, messages: list[ChatMessage], tools: list[ToolDefinition] | None = None) -> AsyncIterator[ChatChunk]`
- **Configuration:** Sourced from `config.ai` (model=`"nvidia/nemotron-3-ultra-550b-a55b"`, `max_retries = 0`, explicit timeout).
- **Reasoning Tag Filter:** Stateful reasoning parser across chunk boundaries (`<think>...</think>`); handles split tags (e.g. `"<thi"` + `"nk>secret"` + `"</think>"`) without leaking private thoughts.
- **Resource Cleanup:** `async def aclose(self) -> None` closes the underlying `AsyncOpenAI` client session.

---

## 4. Command Router & Agent Interfaces (PH-070)

### `CommandRouter.route`
- **File:** `app/core/command_router.py`
- **Signature:** `async def route(self, command_text: str, source: str) -> CommandRoutingDecision`
- **Precedence Order:**
  1. `registry.resolve(command_text)`: If `isinstance(outcome, RegistryMatch)`, immediately return `EXACT_MATCH` and dispatch via `dispatcher.dispatch_match(outcome)`. Zero AI calls.
  2. Built-ins / System Commands (`BUILTIN`).
  3. Structured Tool Intent (`STRUCTURED`).
  4. External AI reasoning proposal (`AI_REASONING`): model output parsed as `ActionRequest` and dispatched via `dispatcher.dispatch_request(request)`.
- **Provenance Rule:** `RegistryMatch` is NEVER converted to an `ActionRequest`.

### `AgentRuntime.run_task`
- **File:** `app/agents/runtime.py`
- **Signature:** `async def run_task(self, task: AgentTask) -> AgentTaskResult`
- **Bounds:** Max steps (`task.max_steps <= 30`), max API budget (`task.max_budget_calls <= 50`).
- **Verification Gate:** Requires explicit verification by `AgentVerifier` before declaring a task successfully completed. A coding task cannot finish solely because the model says "done".

---

## 5. Voice Pipeline & Audio Capture Interfaces (PH-080)

### `WakeDetector.process_chunk`
- **File:** `app/voice/wake.py`
- **Signature:** `def process_chunk(self, pcm_chunk: bytes) -> float`
- **Preconditions:** 1280-byte 16kHz 16-bit mono PCM chunks.
- **Enforcement:** Runs local openWakeWord model in a single dedicated thread. Zero network calls.

### `AudioSource.read_frames`
- **File:** `app/voice/audio.py`
- **Signature:** `async def read_frames(self, num_frames: int) -> bytes`
- **Concurrency & Privacy:** Bridge between audio callback thread and asyncio event loop uses `asyncio.Queue(maxsize=16)`. Pre-wake audio ring buffer is wake-detector-only and is **NEVER prepended** to command audio sent to cloud STT.

---

## 6. STT Adapter & Provenance Interfaces (PH-090)

### `STTAdapter.transcribe`
- **File:** `app/voice/stt.py`
- **Signature:** `async def transcribe(self, segment: CommandAudioSegment) -> str`
- **Provenance:** Consumes internal trusted `CommandAudioSegment` created post-wake by `CommandRecorder`.
- **Service Protocol:** Connects to authoritative NVIDIA Riva gRPC service (`grpc.nvcf.nvidia.com:443`) or local Riva NIM container (port 9000).
- **Memory Release:** Releases internal buffers and BytesIO references in `finally`. The coordinator releases `CommandAudioSegment` immediately post-transcription.

---

## 7. System Tray Subsystem (PH-100)

### `StatusNotifierTray.update_state`
- **File:** `app/tray/status_notifier.py`
- **Signature:** `def update_state(self, new_state: str) -> None`
- **Decoupled Architecture:** Receives injected asynchronous shutdown callback; does not take concrete `LifecycleManager` dependency.
- **IPC Protocol:** D-Bus `org.kde.StatusNotifierItem` specification using `dbus-fast`.

---

## 8. Browser Native Protocol Interfaces (PH-110, PH-120)

### `NativeMessageBridge.send_command`
- **File:** `app/browser/native_bridge.py`
- **Signature:** `async def send_command(self, action: BrowserCommand) -> BrowserResponse`
- **IPC:** Resident daemon connects over user-owned UDS under `XDG_RUNTIME_DIR` (mode `0600`) with `SO_PEERCRED` UID verification. Transient native host communicates with Firefox via standard 4-byte framed JSON.
- **4-Fold Security Check:**
  1. Daemon domain allowlist check.
  2. Domain capability check.
  3. Firefox extension host permission check.
  4. Immediate current-origin recheck before DOM action.
  5. Password and sensitive input extraction hard-blocked.

---

## 9. Dashboard Backend Interfaces (PH-130)

### `create_dashboard_app`
- **File:** `app/api/app.py`
- **Signature:** `def create_dashboard_app(dispatcher: ActionDispatcher, storage: SQLiteStorage) -> FastAPI`
- **Endpoints:** Sourced across dedicated route modules:
  - `app/api/routes_state.py` (SSE state stream, status)
  - `app/api/routes_config.py` (validated config CRUD)
  - `app/api/routes_actions.py` (deterministic action list / reload)
  - `app/api/routes_audit.py` (paginated audit log queries)
  - `app/api/routes_agents.py` (agent task control)
- **Database Concurrency:** Single connection + dedicated serialized worker thread + SQLite WAL mode. In-memory fallback if disk storage degrades.

---

## 10. Developer Tooling Interfaces (PH-150)

### `DeveloperToolExecutor.run_workflow` & `DeveloperWorkflowService`
- **File:** `app/executors/developer.py`
- **Architecture:** `DeveloperWorkflowService` sits above `ActionDispatcher`.
- **Routing:**
  - Process operations (`git`, `pytest`): `ActionRequest(tool="process.run")` routed to `dispatcher.dispatch_request()`.
  - File operations: `ActionRequest(tool="file.*")` routed to `dispatcher.dispatch_request()`.
  - Deterministic actions: `RegistryMatch` routed to `dispatcher.dispatch_match()`.
  - Allowed file roots sourced from `config.files.roots`. Auto-commit disabled by default.

---

## 11. Lifecycle Hardening Interfaces (PH-160)

### `LifecycleManager.monitor_memory`
- **File:** `app/core/lifecycle.py`
- **Signature:** `def monitor_memory(self) -> MemorySnapshot`
- **Hardening:** Cgroup-aware RSS measurement accounting for daemon and child processes. Never relies on `gc.collect()` after `MemoryMax=300M` crossing.
