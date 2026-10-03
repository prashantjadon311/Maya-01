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
