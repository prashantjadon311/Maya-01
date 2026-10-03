# Maya Current Codebase Model (PH-000 → PH-040 Reverse Engineering)

**Baseline SHA:** `d367261e617fb96ca2d353871590c0dc616b8fe0`
**Product Code Base SHA:** `ef00714c86d3d7b5684d693da35aa82595a088d4`
**Test Baseline:** 409 passing tests in `tests/`
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
  - Status is typed via `Literal` strings; there is **no `SystemState` enum** in current source.
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
  - `AssistantConfig`: `name`, `identity` (non-empty, trimmed strings)
  - `VoiceConfig`: `enabled`, `always_listen`, `push_to_talk_hotkey`, `wake_engine`, `wake_model`, `wake_threshold=0.55`, `vad_enabled`, `max_command_seconds=30`, `retain_command_audio`. (Note: **no `sample_rate`** in current code model).
  - `STTConfig`: `provider`, `model`, `api_key_env`, `default_language`. (Note: **no `endpoint` or `timeout`** in current code model).
  - `AIConfig`: `provider`, `base_url`, `model`, `api_key_env`, `timeout_seconds=120`, `reasoning_effort`, `reasoning_budget`, `max_output_tokens=8192`. (Note: **no `streaming`** in current code model).
  - `DashboardConfig`: `host="127.0.0.1"`, `port=8765`, `open_browser=True`. (Note: **no 8443 or `allowed_origins`** in current code model).
  - `AgentsConfig`: `max_active=1`, `max_steps=30`, `max_api_calls_per_task=20`, `default_timeout_minutes=30`.
  - `ResourcesConfig`: `memory_high_mb=240`, `memory_max_mb=300`, `max_event_queue=256`, `max_audio_command_seconds=30`.
  - `PrivacyConfig`: `store_chat_history`, `store_action_audit`, `log_prompt_content`, `log_response_content`, `retain_audio`.
  - `BrowserDomainConfig`: `pattern`, `enabled`, `capabilities`, `adapter`.
  - `BrowserConfig`: `domains: list[BrowserDomainConfig]`. (Note: **no `allowed_domains`** in current code model).
  - `FileRootConfig`: `path`, `read`, `write`, `delete`.
  - `FilesConfig`: `roots: list[FileRootConfig]`.
  - `Config`: Root configuration aggregating all subsystem models.
- **Ground Truth Invariants:**
  - Allowed file roots are accessed via `config.files.roots`.
  - There is **no `config.storage`**, **no `config.policy`**, **no `config.approval`**, **no `config.security`**, and **no `config.nvidia`** in the current codebase.

---

### 1.5 `app/policy/engine.py`, `risk.py`, `paths.py` — Policy Engine

- **Primary Symbols:**
  - `PolicyEngine` (`app/policy/engine.py`): `evaluate(action: ActionRequest) -> PolicyDecision`, `evaluate_detailed(action: ActionRequest) -> PolicyEvaluation`, `assess_risk(action: ActionRequest) -> RiskLevel`.
  - `PreapprovalRule`, `PolicyDecision` (`ALLOW_PREAPPROVED`, `ASK_USER`, `DENY`), `PolicyEvaluation`.
  - `RiskLevel`: Four levels: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` in `app/policy/risk.py`.
  - `canonical_path`, `is_contained_in` in `app/policy/paths.py`.
- **Ground Truth Invariants:**
  - The codebase contains **no `RiskClassifier`**, **no `PathValidator`**, and **no `ApprovalStore`** classes.
  - Risk assessment is performed via functions `assess_command_risk`, `assess_file_risk`, and method `PolicyEngine.assess_risk`.
  - Path containment is verified via `canonical_path()` and `is_contained_in()` against `FileRootConfig` objects in `config.files.roots`.

---

### 1.6 `app/executors/` — Safe Action Executors

- **Primary Symbols:**
  - `ProcessExecutor` (`app/executors/process.py`):
    - Signature: `async def execute(self, action: ActionRequest, context: Any = None) -> ActionResult`
    - Requires valid `PolicyEvaluation` context with `decision == PolicyDecision.ALLOW_PREAPPROVED`, matching `matched_preapproval_rule` and `resolved_executable`.
    - Never accepts raw `(argv, cwd=...)` directly from unauthenticated callers.
    - Uses continuous stream draining tasks to capture stdout/stderr bounded by `MAX_PROCESS_OUTPUT_BYTES = 102_400` (100 KB) in `app/executors/base.py`.
    - Escalates process termination on timeout: `terminate() -> wait(0.5s) -> kill() -> wait()`.
  - `FileExecutor` (`app/executors/files.py`):
    - Signature: `async def execute(self, action: ActionRequest, context: Any = None) -> ActionResult`
    - Enforces root containment against `allowed_roots`, rejecting traversal (`../`), symlinks outside roots.
    - Bounded by `MAX_FILE_BYTES = 10_485_760` (10 MiB) in `app/executors/base.py`.
  - `XdgExecutor` (`app/executors/xdg.py`):
    - Opens **LOCAL FILE targets only**; strictly rejects URL schemes containing `:` (e.g. `http:`, `https:`).
    - Resolves `/usr/bin/xdg-open` strictly without ambient `shutil.which` PATH fallbacks.

---

## 2. Invariant Rules for Future Phases

1. **NO SHELL EXECUTION:** All subprocess executions must use `asyncio.create_subprocess_exec` with explicit argv lists; `shell=True` is strictly forbidden.
2. **NO POLICY BYPASS:** No code path may bypass `ActionDispatcher`.
3. **FAIL-CLOSED:** In the event of any exception during policy evaluation, argument substitution, or approval verification, the action must fail closed with an explicit rejection.
4. **NO MODEL TRUST:** AI model output is strictly untrusted text. It must be parsed as an `ActionRequest` and pass full policy checks before execution.
5. **TYPED POST-APPROVAL AUTHORIZATION:** In PH-050, human approval produces an `ExecutionAuthorization(source="HUMAN_ALLOW_ONCE")` passed to executors via dispatcher; human approval must never be faked as `ALLOW_PREAPPROVED`.
