# Maya Public Interfaces & Canonical Signatures

Every public interface across Maya phases PH-050 through PH-180 is frozen herein. Subsystems must adhere strictly to these method signatures, input validations, preconditions, postconditions, and bounded resource constraints.

---

## 1. Approval Broker & Security Interfaces (PH-050)

### `ApprovalBroker.request_approval`
- **File:** `app/policy/broker.py`
- **Signature:** `async def request_approval(self, req: ActionRequest, reason: str, risk: RiskLevel) -> ApprovalGrant`
- **Inputs:** `req: ActionRequest`, `reason: str`, `risk: RiskLevel`
- **Preconditions:** `req` is validated Pydantic model with immutable canonical JSON payload; `risk` in `(RiskLevel.MEDIUM, RiskLevel.HIGH)`.
- **Postconditions:** Registers in-memory `ApprovalGrant` with UUID, 60s timeout, and `action_hash = sha256(canonical_json(req))`. Spawns native popup subprocess.
- **Resource Bounds:** Max 10 concurrent pending requests in memory.
- **Timeout:** 60.0s. Fails closed to `ApprovalTimeoutError` (resolving strictly to `DENY`).
- **Cancellation:** Kills popup child process and cleans up grant from memory.

### `ApprovalBroker.verify_grant`
- **File:** `app/policy/broker.py`
- **Signature:** `def verify_grant(self, grant_id: str, action_hash: str) -> bool`
- **Inputs:** `grant_id: str`, `action_hash: str`
- **Algorithm:** Uses `hmac.compare_digest` to check grant existence, expiry timestamp against `time.monotonic()`, and exact SHA-256 payload match.
- **Idempotency:** Read-only inspection; idempotent.

### `ApprovalBroker.consume_grant`
- **File:** `app/policy/broker.py`
- **Signature:** `def consume_grant(self, grant_id: str, action_hash: str) -> bool`
- **Inputs:** `grant_id: str`, `action_hash: str`
- **Algorithm:** Verifies grant; if valid, atomically deletes `grant_id` from memory under `asyncio.Lock`.
- **Postconditions:** Grant cannot be replayed or reused for subsequent actions.

---

## 2. NVIDIA AI Provider Interfaces (PH-060)

### `NvidiaProvider.complete`
- **File:** `app/ai/nvidia.py`
- **Signature:** `async def complete(self, messages: list[ChatMessage], tools: list[ToolDefinition] | None = None) -> ChatResponse`
- **Target URL:** `https://integrate.api.nvidia.com/v1`
- **Parameters:** `model = "nvidia/nemotron-3-ultra-550b-a55b"`, `max_retries = 0`, `timeout = 30.0`.
- **Preconditions:** `messages` bounded to max 32 items (~128KB total context).
- **Postconditions:** Strips internal model reasoning traces; returns sanitized content and structured tool calls.

### `NvidiaProvider.stream_chat`
- **File:** `app/ai/nvidia.py`
- **Signature:** `async def stream_chat(self, messages: list[ChatMessage], tools: list[ToolDefinition] | None = None) -> AsyncIterator[ChatChunk]`
- **Postconditions:** Yields SSE delta chunks. Bounded chunk buffer (4KB max per chunk).

---

## 3. Command Router & Agent Runtime Interfaces (PH-070)

### `CommandRouter.route`
- **File:** `app/core/command_router.py`
- **Signature:** `async def route(self, command_text: str, source: str) -> CommandRoutingDecision`
- **Classification Order:**
  1. `ActionRegistry.find_exact_match(command_text)` -> If found, return `ExactMatchDecision` (Zero AI calls).
  2. Built-in system command matcher (e.g. open app, list files).
  3. Structured regex parser for deterministic slot commands.
  4. AI reasoning / tool selection via `NvidiaProvider`.
- **Bounds:** Input trimmed; maximum 1024 characters.

### `AgentRuntime.run_task`
- **File:** `app/agents/runtime.py`
- **Signature:** `async def run_task(self, objective: str, workspace_root: Path) -> AgentTaskResult`
- **Bounds:** Max 15 execution steps, max 20 external AI API calls, max 64KB transcript buffer.
- **Security Boundary:** All tool proposals executed by the agent must pass through `ActionDispatcher.dispatch_action_request`.

---

## 4. Voice & Speech Interfaces (PH-080, PH-090)

### `WakeDetector.process_chunk`
- **File:** `app/voice/wake.py`
- **Signature:** `def process_chunk(self, pcm_chunk: bytes) -> float`
- **Engine:** openWakeWord (1 CPU thread).
- **Inputs:** Exactly 1280 bytes of 16kHz 16-bit mono PCM (80ms frame).
- **Security Invariant:** Zero network sockets or IPC calls invoked.

### `STTAdapter.transcribe`
- **File:** `app/voice/stt.py`
- **Signature:** `async def transcribe(self, pcm_bytes: bytes, language: str = 'hi-IN') -> str`
- **Preconditions:** Called strictly for post-wake command audio; max length 10.0s (320KB PCM).
- **Cleanup:** `pcm_bytes` released from memory immediately post-transcription.


### `AudioSource.read_frames`
- **File:** `app/voice/audio.py`
- **Signature:** `async def read_frames(self, num_frames: int) -> bytes`
- **Inputs:** `num_frames: int` (> 0).
- **Bounds:** Max ring buffer size 3 seconds (96,000 bytes). Oldest dropped on overflow.
- **Timeout:** 1.0s. Cancellation interrupts buffer await cleanly.
- **Audit Code:** `AUD-VOIC-READ`.

---

## 5. System Tray & Browser Native Bridge Interfaces (PH-100, PH-110, PH-120)

### `StatusNotifierTray.update_state`
- **File:** `app/tray/status_notifier.py`
- **Signature:** `def update_state(self, new_state: SystemState) -> None`
- **Protocol:** Freedesktop StatusNotifierItem via session D-Bus.

### `NativeMessageBridge.send_command`
- **File:** `app/browser/native_bridge.py`
- **Signature:** `async def send_command(self, action: BrowserCommand) -> BrowserResponse`
- **Framing:** 4-byte native endian unsigned int length prefix + UTF-8 JSON payload. Max payload 1MB.
- **Security Gates:** Destination domain verified against daemon policy allowlist before dispatch.

### `GoogleAdapter.extract`
- **File:** `extension/firefox/adapters/google.js`
- **Signature:** `function extract(document: Document) -> AdapterResult`
- **Preconditions:** `window.location.origin` is `'https://www.google.com'`.
- **Postconditions:** Returns top 5 organic search results (title, snippet, URL).
- **Security Boundary:** Yes (`test_site_adapters_semantic_extraction`).
- **Bounds:** Max 5 results, max 500 chars snippet per result. Timeout 2.0s.
- **Audit Code:** `SEC-ADPT-EXTRACT`. Errors: `DOMSelectorNotFoundError`.

---

## 6. Dashboard & Storage Interfaces (PH-130)

### `create_dashboard_app`
- **File:** `app/api/app.py`
- **Signature:** `def create_dashboard_app(dispatcher: ActionDispatcher, storage: SQLiteStorage) -> FastAPI`
- **Preconditions:** `dispatcher` and `storage` initialized.
- **Postconditions:** Returns FastAPI application bound strictly to localhost with no wildcard CORS.
- **Security Boundary:** Yes (`test_dashboard_cors_and_localhost_binding`).
- **Bounds:** Request body size limited to 64KB. Timeout 30.0s.
- **Audit Code:** `SEC-API-CREATE`. Errors: `AppFactoryError`.

---

## 7. Developer Tool Execution Interfaces (PH-150)

### `DeveloperToolExecutor.run_workflow`
- **File:** `app/executors/developer.py`
- **Signature:** `async def run_workflow(self, repo_path: Path, steps: list[DevStep]) -> WorkflowResult`
- **Preconditions:** `repo_path` is verified git repository inside allowed roots; all steps pass policy.
- **Postconditions:** Executes edit -> test -> inspect diff loop; auto-commit is NOT triggered.
- **Security Boundary:** Yes (`test_auto_commit_disabled_by_default`).
- **Bounds:** Max 10 steps per workflow, max diff capture 100KB. Timeout 120.0s.
- **Audit Code:** `SEC-DEV-RUN`. Errors: `GitExecutionError`, `TestExecutionFailedError`.

---

## 8. Resource & Lifecycle Interfaces (PH-160)

### `LifecycleManager.monitor_memory`
- **File:** `app/core/lifecycle.py`
- **Signature:** `def monitor_memory(self) -> MemorySnapshot`
- **Preconditions:** cgroup v2 memory controller or `/proc/self/status` available.
- **Postconditions:** Returns MemorySnapshot with `current_rss_mb`, `peak_rss_mb`, and `limit_mb`.
- **Bounds:** Instantaneous procfs read. Timeout 0.1s. Idempotent: True.
- **Audit Code:** `AUD-RES-MONITOR`. Errors: `ProcfsReadError`.
