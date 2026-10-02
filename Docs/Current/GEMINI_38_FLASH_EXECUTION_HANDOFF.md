# Gemini 3.8 Flash High — Execution Handoff V3

## 1. Context for Flash Execution
You are implementing Project H V2. The architecture has been rigorously audited and frozen by Gemini 3.1 Pro High. 
The task ledger in `Docs/TASKS.md` is your single source of truth. Do not invent new tasks or redefine interfaces.

## 2. Dependency Order and Batch Table

| BATCH | TASK IDs | PRODUCES | CONSUMES | REVIEW GATE |
|---|---|---|---|---|
| Batch 1A | PH-000 | (baseline harness, config fixtures) | None | FLASH_SAFE |
| Batch 1B | PH-010 | Config, AppState, CommandRequest, ActionRequest, ActionResult | None | FLASH_SAFE |
| Batch 2 | PH-020 | PolicyDecision, ApprovalRequest, PolicyEngine | ActionRequest | PRO_REVIEW_REQUIRED_AFTER |
| Batch 3 | PH-030 | ActionDefinition, ActionRegistry | ActionRequest | FLASH_SAFE |
| Batch 4 | PH-040 | ActionDispatcher, BaseExecutor, ProcessExecutor, FileExecutor, BrowserBridge (stub) | PolicyEngine, ActionRequest, ActionResult, PolicyDecision, ApprovalRequest | PRO_REVIEW_REQUIRED_AFTER |
| Batch 5 | PH-050 | ApprovalBroker | ApprovalRequest, PolicyDecision | FLASH_SAFE |
| Batch 6 | PH-060 | AIProvider, NvidiaProvider | None | FLASH_SAFE |
| Batch 7 | PH-070 | CommandRouter, AgentTask, AgentRuntime | ActionDispatcher, AIProvider, ActionRegistry | FLASH_SAFE |
| Batch 8 | PH-080 | WakeDetector, CommandRecorder | None | FLASH_SAFE |
| Batch 9 | PH-090 | STTProvider | CommandRecorder | FLASH_SAFE |
| Batch 10 | PH-100 | Tray | AppState | FLASH_SAFE |
| Batch 11 | PH-110 | BrowserBridge (Unix-socket) | None | PRO_REVIEW_REQUIRED_AFTER |
| Batch 12 | PH-120 | SiteAdapters | BrowserBridge | FLASH_SAFE |
| Batch 13 | PH-130 | AuditEvent, Dashboard Backend API | AppState, CommandRouter | FLASH_SAFE |
| Batch 14 | PH-140 | Dashboard Frontend | Dashboard Backend API | FLASH_SAFE |
| Batch 15 | PH-150 | Developer Workflows | ActionDispatcher | FLASH_SAFE |
| Batch 16 | PH-160 | Resource Hardening | All | FLASH_SAFE |
| Batch 17 | PH-170 | Packaging | All | FLASH_SAFE |
| Batch 18 | PH-180 | Final Acceptance | All | PRO_REVIEW_REQUIRED_AFTER |

## 3. Implementation Batches

### Batch 1A: Repository Harness (FLASH_SAFE)
**TASK IDs:** PH-000

**Exact Files to CREATE:**
- `app/__init__.py`
- `app/main.py`
- `tests/__init__.py`
- `tests/test_harness.py`
- `tests/fixtures/config.example.toml`

**Exact Files to MODIFY:**
- `pyproject.toml`
- `.gitignore`

**Exact Interfaces Produced:** None (Daemon entrypoint stub only).
**Exact Interfaces Consumed:** None.
**Exact Config Fixtures:** `tests/fixtures/config.example.toml`

**TDD Contract:**
- **RED TESTS:** `tests/test_harness.py` (test memory baseline, test empty daemon starts/stops)
- **VERIFY RED:** `pytest tests/test_harness.py`
- **GREEN:** `app/main.py` (empty daemon stub), `.gitignore` (secrets/audio/temp), `pyproject.toml` (pytest, anyio, psutil)
- **VERIFY GREEN:** `pytest tests/test_harness.py`
- **FULL REGRESSION:** `pytest`

**Acceptance Criteria:**
- Empty daemon starts/stops.
- Baseline RSS recorded via `psutil`.
- `.gitignore` prevents secret/audio commit.
- Config fixtures added.

### Batch 1B: Config & Schemas (FLASH_SAFE)
**TASK IDs:** PH-010

**Exact Files to CREATE:**
- `app/core/config.py`
- `app/core/state.py`
- `app/core/events.py`
- `app/actions/schema.py`
- `tests/test_config.py`
- `tests/test_schemas.py`

**Exact Files to MODIFY:** None.

**Exact Interfaces Produced:** `Config` (from `config.toml`), `AppState`, `CommandRequest`, `ActionRequest`, `ActionResult`.
**Exact Interfaces Consumed:** None.
**Exact Config Fixtures:** Reads from `tests/fixtures/config.example.toml`.

**TDD Contract:**
- **RED TESTS:** 
  - `tests/test_config.py`: test unknown field fails, invalid memory limit fails, valid config loads.
  - `tests/test_schemas.py`: test action pack schema validation, test canonical JSON deterministic serialization of `ActionRequest`.
- **VERIFY RED:** `pytest tests/test_config.py tests/test_schemas.py`
- **GREEN:** `app/core/config.py` (toml parsing), `app/actions/schema.py` (Pydantic v2 schemas + deterministic hash logic), `app/core/state.py`, `app/core/events.py`.
- **VERIFY GREEN:** `pytest tests/test_config.py tests/test_schemas.py`
- **FULL REGRESSION:** `pytest`

**Acceptance Criteria:**
- `ConfigDict(extra="forbid")` on config and security schemas.
- `ActionRequest` provides deterministic JSON serialization for hashing.

### Batch 2: Policy Engine (PRO_REVIEW_REQUIRED_AFTER)
**TASK IDs:** PH-020

**Exact Files to CREATE:**
- `app/policy/engine.py`
- `app/policy/approvals.py`
- `tests/test_policy.py`

**Exact Files to MODIFY:** None.

**Exact Interfaces Produced:** `PolicyDecision` (Enum: `ALLOW_PREAPPROVED`, `ASK_USER`, `DENY`), `ApprovalRequest` (frozen Pydantic model with digest), `PolicyEngine`.
**Exact Interfaces Consumed:** `ActionRequest`.

**TDD Contract:**
- **RED TESTS:** `tests/test_policy.py` (test sudo denies, test out of root denies, test approval digest generation and verification).
- **VERIFY RED:** `pytest tests/test_policy.py`
- **GREEN:** `app/policy/engine.py`, `app/policy/approvals.py`.
- **VERIFY GREEN:** `pytest tests/test_policy.py`
- **FULL REGRESSION:** `pytest`

**Acceptance Criteria:**
- `ApprovalRequest` is immutable (`ConfigDict(frozen=True)`) and verifies SHA-256 of canonical `ActionRequest`.

### Batch 3: Action Registry (FLASH_SAFE)
**TASK IDs:** PH-030

**Exact Files to CREATE:**
- `app/actions/registry.py`
- `tests/test_registry.py`

**Exact Files to MODIFY:** None.

**Exact Interfaces Produced:** `ActionDefinition`, `ActionRegistry`.
**Exact Interfaces Consumed:** `ActionRequest`, `Config`.

**TDD Contract:**
- **RED TESTS:** `tests/test_registry.py` (test phrase matching, disabled action ignored, malformed JSON rejected).
- **VERIFY RED:** `pytest tests/test_registry.py`
- **GREEN:** `app/actions/registry.py`.
- **VERIFY GREEN:** `pytest tests/test_registry.py`
- **FULL REGRESSION:** `pytest`

### Batch 4: Action Dispatcher & Safe Executors (PRO_REVIEW_REQUIRED_AFTER)
**TASK IDs:** PH-040

**Exact Files to CREATE:**
- `app/core/dispatcher.py`
- `app/executors/base.py`
- `app/executors/process.py`
- `app/executors/files.py`
- `app/browser/protocol.py` (BrowserBridge stub)
- `tests/test_executors.py`

**Exact Files to MODIFY:** None.

**Exact Interfaces Produced:** `ActionDispatcher`, `BaseExecutor`, `ProcessExecutor`, `FileExecutor`, `BrowserBridge` (stub).
**Exact Interfaces Consumed:** `PolicyEngine`, `ActionRequest`, `ActionResult`, `PolicyDecision`, `ApprovalRequest`.

**TDD Contract:**
- **RED TESTS:** `tests/test_executors.py` (dispatcher halts on DENY without running executor, FileExecutor symlink traversal throws error).
- **VERIFY RED:** `pytest tests/test_executors.py`
- **GREEN:** `app/core/dispatcher.py`, `app/executors/files.py` (uses `os.path.realpath` checks), `app/executors/process.py` (`shell=False` only).
- **VERIFY GREEN:** `pytest tests/test_executors.py`
- **FULL REGRESSION:** `pytest`

## 4. NEXT EXACT PROMPT — GEMINI 3.8 FLASH HIGH
```text
TASK MODE: PROJECT H V2 — FLASH IMPLEMENTATION / BATCH 1A ONLY

MODEL ROLE:
You are Gemini 3.8 Flash High acting as the implementation engineer.

Gemini 3.1 Pro High has audited the architecture and prepared the handoff.
Your job is to execute ONLY Batch 1A from the CURRENT corrected handoff:
Docs/Current/GEMINI_38_FLASH_EXECUTION_HANDOFF.md

Read Docs/Current/GEMINI_38_FLASH_EXECUTION_HANDOFF.md Batch 1A definition.
Follow the exact TDD Contract (RED -> VERIFY RED -> GREEN -> VERIFY GREEN).
Create the exact files, add pytest/anyio/psutil to pyproject.toml, and create the .gitignore and config fixtures as strictly specified.
Run the full regression test and update your Antigravity task artifact.
Output a result packet when done, then STOP. Do not begin Batch 1B.
```
