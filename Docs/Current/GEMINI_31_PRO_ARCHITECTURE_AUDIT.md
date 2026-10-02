# Gemini 3.1 Pro High — Architecture & Security Audit V2

## 1. Repository State Findings
- **Current State:** The `Docs/` directory holds the definitive V2 authority documents. `TASKS.md` has been fully rebuilt to accurately reflect the 18 phases of the V2 plan.
- **Reusable Work:** The `agent.py` script proves the NVIDIA Nemotron connection works. `pyproject.toml` contains baseline dependencies but needs expansion for V2.

## 2. Architecture Contradictions & Security Findings

### Finding A: Policy Engine Bypass (Agent Containment)
- **Defect:** If `AgentRuntime` calls `PolicyEngine` and then independently calls `Executors`, a bug in the agent runtime could bypass policy enforcement.
- **Resolution:** `AgentRuntime` must not have direct access to `Executors`. Instead, `AgentRuntime` yields an `ActionRequest` to a centralized `ActionDispatcher`. The dispatcher strictly queries `PolicyEngine` and only invokes the executor if approved.

### Finding B: Approval Immutability & Hashing Contract
- **Defect:** A frozen Pydantic model (`ApprovalRequest`) with nested mutable dicts (like arguments) does not guarantee deep immutability. If an action's arguments mutate after approval, the executor could run an unapproved payload.
- **Resolution:** The contract enforces canonical JSON serialization for `ActionRequest` followed by a SHA-256 hash. `ApprovalRequest` stores this digest. Before the `ActionDispatcher` runs an executor, it re-serializes and re-hashes the pending action to ensure the digest precisely matches the approved token.

### Finding C: Browser IPC Security
- **Defect:** A naked `localhost` HTTP bridge for the Firefox Native Messaging host introduces a local privilege escalation surface, allowing any local process to send requests bypassing browser-side checks.
- **Resolution:** The bridge must use an authenticated, user-owned Unix-domain socket for IPC between the native messaging host and the `project-hd` daemon.

### Finding D: Policy Decision Semantics
- **Defect:** Previous audits lost the distinction between pre-approved automated execution and user-intervened execution.
- **Resolution:** `PolicyDecision` is strictly typed as an Enum containing `ALLOW_PREAPPROVED`, `ASK_USER`, and `DENY` exactly as required by `SECURITY.md`.

### Finding E: File Path Security (Symlink Escapes)
- **Defect:** `FileExecutor` could allow symlink-based directory traversal.
- **Resolution:** `FileExecutor` must invoke `os.path.realpath` on all paths and strictly enforce `path.is_relative_to(allowed_root)` before I/O.

## 3. Memory Risks & Budget Defense (300 MiB Limit)
- **Wake Word Engine:** `openwakeword` must not load its TFLite/ONNX models globally on module import. Lazy loading is required only when "Always Listen" is enabled.
- **HTTP Connections:** Default `AsyncOpenAI` connection pools can grow. Must be limited via `httpx.Limits(max_connections=5)`.

## 4. Frozen Interface Contracts (Reconciled with TASKS.md)

- **`AppState` (PH-010):** In-memory state store.
- **`CommandRequest` (PH-010):** Normalized input (text/voice).
- **`ActionRequest` (PH-010):** Typed tool call model (includes canonical hashing logic).
- **`ActionResult` (PH-010):** Execution result payload.
- **`PolicyDecision` (PH-020):** Enum (`ALLOW_PREAPPROVED`, `ASK_USER`, `DENY`).
- **`ApprovalRequest` (PH-020):** Immutable record (SHA-256 digest, expiry).
- **`PolicyEngine` (PH-020):** Evaluates requests against rules.
- **`ActionDefinition` (PH-030):** Parsed schema from action packs.
- **`ActionRegistry` (PH-030):** Loads and resolves determinist actions.
- **`ActionDispatcher` (PH-040):** Unites PolicyEngine and Executors securely.
- **`BaseExecutor` (PH-040):** Protocol for all executors.
- **`ProcessExecutor` (PH-040):** Subprocess execution (`shell=False`).
- **`FileExecutor` (PH-040):** Contained file operations.
- **`AIProvider` (PH-060):** LLM protocol.
- **`AgentTask` / `AgentRuntime` (PH-070):** Multi-step loop interacting *only* with `ActionDispatcher`.
- **`WakeDetector` (PH-080):** Local continuous audio frame processing.
- **`CommandRecorder` (PH-080):** Voice recorder with VAD.
- **`STTProvider` (PH-090):** Remote transcription adapter.
- **`BrowserBridge` (PH-110):** Authenticated IPC connection to Firefox.
- **`AuditEvent` (PH-130):** Storage record for dashboard viewing.

## 5. Verification Check
- **Policy bypass closed:** YES (via `ActionDispatcher`).
- **Symlink/realpath containment:** YES.
- **Browser IPC authenticated:** YES (Unix-domain socket).
- **Wake-before-network invariant:** YES.
- **Approval Integrity:** YES (Canonical SHA-256 hashing).
- **Task/Interface consistency:** YES.
- **300 MiB Resource Gate:** Enforced via strict dependency lazy-loading rules.
