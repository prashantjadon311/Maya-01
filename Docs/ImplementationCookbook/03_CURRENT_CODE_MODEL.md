# Maya Current Codebase Model (PH-000 → PH-040 Reverse Engineering)

**Baseline SHA:** `ef00714c86d3d7b5684d693da35aa82595a088d4`  
**Test Baseline:** 381 passing tests in `tests/`  
**CI Run Baseline:** `37107781413`

This document details the architectural reality of the existing Maya implementation as of PH-040 security closure, serving as the immutable foundation upon which PH-050 through PH-180 are built.

---

## 1. Subsystem Architecture & Classification

### 1.1 `app/core/dispatcher.py` — Central Action Dispatcher

- **Primary Symbols:** `ActionDispatcher`, `_CompositeBudget`
- **Classification:** `EXTEND`
- **Security Role:** Central enforcement gateway. Strictly enforces that NO executor is invoked before:
  1. Strict Pydantic schema validation.
  2. Trusted argument materialization / slot binding.
  3. Policy evaluation (`PolicyEngine.evaluate`).
  4. Approval floor check (resolving `ASK_USER` via the `ApprovalBroker` in PH-050).
  5. Executor-specific capability & path validation.
- **State Owned:**
  - `policy_engine`: Instance of `PolicyEngine`
  - `registry`: Instance of `ActionRegistry`
  - `process_executor`, `file_executor`, `xdg_executor`, `browser_bridge`
- **Side Effects:**
  - Executes subprocesses, file operations, desktop launches, or browser commands.
  - Emits audit events via `AuditSink`.
- **Resource Ownership:** Bounded composite recursion (`MAX_COMPOSITE_DEPTH = 5`, `MAX_COMPOSITE_STEPS = 32`, `MAX_COMPOSITE_TOTAL_STEPS = 64`).
- **Tests:** `tests/test_dispatcher.py`, `tests/test_executors.py`
- **Future Extension Points:**
  - PH-050: Integrate `ApprovalBroker` for interactive `ASK_USER` resolution with single-use cryptographic grants.
  - PH-070: Expose dispatch interfaces to the agent loop.

---

### 1.2 `app/core/state.py` — Application State Machine

- **Primary Symbols:** `AppState`, `SystemState`
- **Classification:** `EXTEND`
- **Security Role:** Single source of truth for runtime daemon state (`READY_WAKE`, `RECORDING`, `ROUTING`, `THINKING`, `AWAITING_APPROVAL`, `EXECUTING`, `SPEAKING`, `ERROR`).
- **State Owned:** `current_state`, thread locks, state listeners.
- **Side Effects:** Emits state change callbacks to subscribers (dashboard SSE, system tray).
- **Resource Ownership:** Bounded state history.
- **Tests:** `tests/test_schemas.py`
- **Future Extension Points:**
  - PH-080: Integrate wake word detection triggers (`READY_WAKE` → `WAKE_DETECTED` → `RECORDING`).
  - PH-100: Feed state transitions to D-Bus/SNI system tray indicator.

---

### 1.3 `app/policy/` — Policy Engine & Security Evaluation

- **Primary Symbols:** `PolicyEngine`, `RiskLevel`, `RiskClassifier`, `PathValidator`, `ApprovalStore`
- **Classification:** `EXTEND`
- **Security Role:** Determines execution authorization:
  - `ALLOW`: Pre-approved low/medium actions matching explicit hash/path rules.
  - `ASK_USER`: High risk actions, destructive operations, or unregistered commands.
  - `DENY`: Hard-blocked commands (e.g. `rm -rf /`, `/dev/`, `chmod 777`, shell meta-characters).
- **State Owned:** In-memory preapproval rules, forbidden paths, allowed command hashes.
- **Side Effects:** None directly; purely functional policy evaluation.
- **Resource Ownership:** Read-only cached rules loaded at daemon initialization.
- **Tests:** `tests/test_policy.py`
- **Future Extension Points:**
  - PH-050: Verification of signed, single-use approval grants with payload hash binding.

---

### 1.4 `app/actions/` — Action Registry & Matcher

- **Primary Symbols:** `ActionRegistry`, `RegistryMatch`, `match_action`, `substitute_arguments`, `ActionDefinition`, `ActionRequest`, `ActionResult`
- **Classification:** `KEEP` / `EXTEND`
- **Security Role:**
  - `substitute_arguments`: `DO_NOT_TOUCH`. Guarantees strict literal substitution, rejecting template injection and shell escape attempts.
  - `ActionRegistry`: `EXTEND`. Validates action packs from disk, rejecting symlinks, oversized packs, and duplicate action IDs.
- **State Owned:** Active action pack dictionary, phrase-to-action lookup table.
- **Side Effects:** None.
- **Resource Ownership:** Bounded pack limits (max 50 packs, max 500 actions, max 2000 phrases).
- **Tests:** `tests/test_registry.py`
- **Future Extension Points:**
  - PH-150: Dynamic registration of developer action packs.

---

### 1.5 `app/executors/` — Safe Action Executors

- **Primary Symbols:**
  - `ProcessExecutor` (`EXTEND`): Executes allowlisted binaries via `asyncio.create_subprocess_exec` (never `shell=True`). Enforces 64KB bounded output buffers and strict process timeouts.
  - `FileExecutor` (`EXTEND`): Sandboxed file operations (read, write, append, delete). Enforces root boundaries, canonical path resolution (preventing symlink swaps), and file size limits (1MB read, 5MB write).
  - `XdgExecutor` (`KEEP`): Safe desktop launching using `xdg-open` on validated URLs (`http`/`https`) and local files.
- **Security Role:** Terminal execution isolation.
- **Side Effects:** OS process spawning, filesystem mutation, application launch.
- **Resource Ownership:**
  - `ProcessExecutor`: Bounded subprocess runtime and output deques.
  - `FileExecutor`: Bounded read/write buffer sizes.
- **Tests:** `tests/test_executors.py`

---

### 1.6 `app/browser/` — Browser Automation Protocol

- **Primary Symbols:** `BrowserBridge`
- **Classification:** `EXTEND`
- **Security Role:** Abstract interface for communicating with the Firefox extension via Native Messaging.
- **State Owned:** Extension connection state.
- **Side Effects:** Sends JSON payloads over local stdin/stdout pipe.
- **Resource Ownership:** Managed subprocess / native messaging host.
- **Future Extension Points:**
  - PH-110: Implementation of the native messaging protocol host with session tokens and origin verification.
  - PH-120: Specialized DOM adapters for Google, Amazon, ChatGPT, Claude, and Gemini.

---

## 2. Invariant Rules for Existing Code

1. **NO SHELL EXECUTION:** All subprocess execution must remain `create_subprocess_exec` with explicit argv lists; `shell=True` is strictly forbidden.
2. **NO POLICY BYPASS:** No code path—whether originating from voice, web UI, local CLI, or autonomous agent—may bypass `ActionDispatcher`.
3. **FAIL-CLOSED:** In the event of any exception during policy evaluation, argument substitution, or approval verification, the action must fail closed with an explicit rejection.
4. **NO MODEL TRUST:** AI model output is strictly untrusted text. It must be parsed as an `ActionRequest` and pass full policy checks before execution.
