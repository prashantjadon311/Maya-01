# Maya Current Codebase Model (PH-000 → PH-040 Reverse Engineering)

**Baseline SHA:** `d367261e617fb96ca2d353871590c0dc616b8fe0`
**Product Code Base SHA:** `ef00714c86d3d7b5684d693da35aa82595a088d4`
**Test Baseline:** 381 passing tests in `tests/`
**CI Run Baseline:** `37107781413`

This document details the architectural reality of the existing Maya implementation as of PH-040 security closure, serving as the immutable foundation upon which PH-050 through PH-180 are built. All symbols, signatures, and limits documented here reflect actual source code in `app/`.

---

## 1. Subsystem Architecture & Ground Truth Symbols

### 1.1 `app/core/state.py` — Application State

- **Primary Class:** `AppState(BaseModel)`
- **Classification:** `EXTEND`
- **Fields:**
  - `status: Literal["DISABLED", "READY_WAKE", "WAKE_DETECTED", "RECORDING", "TRANSCRIBING", "ROUTING", "THINKING", "AWAITING_APPROVAL", "EXECUTING", "SPEAKING", "ERROR"] = "DISABLED"`
  - `always_listen: StrictBool = False`
  - `voice_output: StrictBool = False`
  - `active_task_id: str | None = None`
  - `pending_approval: StrictBool = False`
  - `metadata: dict[str, Any] = Field(default_factory=dict)`
- **Methods:**
  - `get_state() -> dict[str, Any]`
  - `update(key: str, value: Any) -> None`
- **Ground Truth Invariants:**
  - Status is typed via `Literal` strings; there is **no `SystemState` enum**.
  - There are currently **no listeners, no thread locks, no transition history, and no `transition_to()` method**.
  - `model_config = ConfigDict(extra="forbid", validate_assignment=True)`.

---

### 1.2 `app/actions/registry.py` & `app/actions/matcher.py` — Deterministic Action Registry

- **Primary Symbols:** `ActionRegistry`, `RegistryMatch`, `RegistryAmbiguity`, `ActionDefinition`, `ActionPack`
- **Classification:** `KEEP` / `EXTEND`
- **Key API:**
  - `resolve(command: str) -> RegistryMatch | RegistryAmbiguity | None`
  - `reload() -> list[str]` (returns diagnostics)
  - `get_definition(action_id: str) -> ActionDefinition | None` (returns deep copy)
- **Bounded Resource Limits:**
  - `MAX_PACK_BYTES = 1_048_576` (1 MiB per pack file)
  - `MAX_PACK_FILES = 64` (maximum pack files in `actions_dir`)
  - `MAX_TOTAL_ACTIONS = 2048` (maximum actions across all packs)
  - `MAX_TOTAL_PHRASES = 4096` (global phrase budget preventing regex/RAM exhaustion)
  - `MAX_PHRASES_PER_ACTION = 32`
  - `MAX_PHRASE_CHARS = 512`
  - `MAX_COMMAND_CHARS = 4096`
- **Ground Truth Invariants:**
  - There is **no `find_exact_match`**, **no `find_match`**, **no `confidence` score**, and **no `match.to_request()`**.
  - `RegistryMatch` is a dedicated frozen dataclass representing a deterministic match with verified slot arguments; it is **NOT an `ActionRequest`** and must NEVER be converted to an `ActionRequest`.

---

### 1.3 `app/core/dispatcher.py` — Central Action Dispatcher

- **Primary Symbols:** `ActionDispatcher`, `_CompositeBudget`
- **Classification:** `EXTEND`
- **Core Security Gateway:** Strictly enforces that NO executor is invoked before:
  1. Strict Pydantic schema validation.
  2. Trusted argument materialization / slot binding.
  3. Policy evaluation (`PolicyEngine.evaluate`).
  4. Approval floor check (resolving `ASK_USER` via `ApprovalBroker` in PH-050).
  5. Executor-specific capability & path validation.
- **Dispatch Pathways:**
  - `dispatch_match(outcome: RegistryMatch) -> ActionResult`: Trusted deterministic pathway preserving snapshot-bound registry provenance.
  - `dispatch_request(action: ActionRequest) -> ActionResult`: External / model-proposed pathway.
- **Ground Truth Invariants:**
  - There is **no `dispatch_action_request()`**.
  - An `ActionRequest.id` string grants **zero trusted registry provenance** and is never treated as a verified `RegistryMatch`.
  - Bounded composite recursion limits: `MAX_COMPOSITE_DEPTH = 5`, `MAX_COMPOSITE_STEPS = 32`, `MAX_COMPOSITE_TOTAL_STEPS = 64`.
  - `recent_audits` property returns an immutable tuple of recent audit event copies (bounded `maxlen=256`).

---

### 1.4 `app/core/config.py` — Configuration Models

- **Primary Symbols:**
  - `AssistantConfig` (name, identity)
  - `VoiceConfig` (wake_model, wake_threshold, max_command_seconds, sample_rate)
  - `STTConfig` (model="nvidia/parakeet-1_1b-rnnt-multilingual-asr", endpoint, language, timeout_seconds)
  - `AIConfig` (model="nvidia/nemotron-3-ultra-550b-a55b", api_key_env, base_url, timeout_seconds, max_output_tokens, streaming)
  - `DashboardConfig` (host="127.0.0.1", port=8443, allowed_origins)
  - `AgentsConfig` (max_active_tasks, default_budget_usd, max_steps_per_task)
  - `ResourcesConfig` (max_resident_memory_mb, max_child_processes, max_audio_command_seconds)
  - `PrivacyConfig` (local_wake_only, log_audio_recordings, mask_audit_secrets)
  - `BrowserDomainConfig`, `BrowserConfig` (enabled, allowed_domains, frame_size_limit_bytes, connect_timeout_seconds)
  - `FileRootConfig` (name, path, read_only, allow_hidden), `FilesConfig` (roots)
  - `Config` (root configuration container aggregating the above)
- **Ground Truth Invariants:**
  - Root config object contains: `assistant`, `voice`, `stt`, `ai`, `dashboard`, `agents`, `resources`, `privacy`, `browser`, `files`.
  - Allowed file roots are accessed via `config.files.roots`.
  - There is **no `config.storage`**, **no `config.policy`**, **no `config.approval`**, **no `config.security`**, and **no `config.nvidia`** in the existing codebase.

---

### 1.5 `app/policy/engine.py`, `risk.py`, `paths.py` — Policy Engine

- **Primary Symbols:**
  - `PolicyEngine` (`app/policy/engine.py`): `evaluate(action: ActionRequest) -> PolicyDecision`, `evaluate_detailed(action: ActionRequest) -> PolicyEvaluation`, `assess_risk(action: ActionRequest) -> RiskLevel`.
  - `PreapprovalRule`, `PolicyDecision` (`ALLOW_PREAPPROVED`, `ASK_USER`, `DENY`), `PolicyEvaluation`.
  - `RiskLevel` (`LOW`, `MEDIUM`, `HIGH`) in `app/policy/risk.py`.
  - `canonical_path`, `is_contained_in` in `app/policy/paths.py`.
- **Ground Truth Invariants:**
  - The codebase contains **no `RiskClassifier`**, **no `PathValidator`**, and **no `ApprovalStore`** classes.
  - Risk assessment is performed via functions `assess_command_risk`, `assess_file_risk`, and method `PolicyEngine.assess_risk`.
  - Path containment is verified via `canonical_path()` and `is_contained_in()` against `FileRootConfig` objects in `allowed_file_roots`.

---

### 1.6 `app/executors/` — Safe Action Executors

- **Primary Symbols:**
  - `ProcessExecutor` (`app/executors/process.py`):
    - Signature: `async def execute(self, action: ActionRequest, context: Any = None) -> ActionResult`
    - Requires valid `PolicyEvaluation` context with `decision == PolicyDecision.ALLOW_PREAPPROVED`, matching `matched_preapproval_rule` and `resolved_executable`.
    - Never accepts raw `(argv, cwd=...)` directly from unauthenticated callers.
    - Uses continuous stream draining tasks (`_read_stream_bounded`) to capture at most `MAX_PROCESS_OUTPUT_BYTES = 1_048_576` bytes per stream.
    - Escalates process termination on timeout: `terminate() -> wait(0.5s) -> kill() -> wait()`.
  - `FileExecutor` (`app/executors/files.py`):
    - Signature: `async def execute(self, action: ActionRequest, context: Any = None) -> ActionResult`
    - Enforces root containment against `allowed_roots`, rejecting traversal (`../`), symlinks outside roots, and size bounds (1 MiB read, 5 MiB write).
  - `XdgExecutor` (`app/executors/xdg.py`):
    - Safe desktop application and URL launcher using `/usr/bin/xdg-open` with `http`/`https` scheme validation.

---

## 2. Invariant Rules for Future Phases

1. **NO SHELL EXECUTION:** All subprocess executions must use `asyncio.create_subprocess_exec` with explicit argv lists; `shell=True` is strictly forbidden.
2. **NO POLICY BYPASS:** No code path may bypass `ActionDispatcher`.
3. **FAIL-CLOSED:** In the event of any exception during policy evaluation, argument substitution, or approval verification, the action must fail closed with an explicit rejection.
4. **NO MODEL TRUST:** AI model output is strictly untrusted text. It must be parsed as an `ActionRequest` and pass full policy checks before execution.
5. **TYPED POST-APPROVAL AUTHORIZATION:** In PH-050, human approval produces an `ExecutionAuthorization(source="HUMAN_ALLOW_ONCE")` passed to executors via dispatcher; human approval must never be faked as `ALLOW_PREAPPROVED`.
