# Maya PH-050→PH-180 Cookbook Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate and freeze a complete, low-token, fresher-safe implementation cookbook for Maya phases PH-050 through PH-180 without implementing those production phases.

**Architecture:** Treat the cookbook as compiled engineering data: pin one repository snapshot, extract authority requirements and current symbols into machine-readable manifests, derive one final PH-180 architecture, then compile small phase-local packets plus reference-code capsules and exact tests. A stdlib-only validator checks ownership, traceability, interface uniqueness, bounds, and freeze counters so the cookbook cannot be marked frozen by prose alone.

**Tech Stack:** Python 3.11+, stdlib (`ast`, `json`, `hashlib`, `pathlib`, `tomllib`, `dataclasses`), existing Pydantic v2 only where useful for schema validation, pytest for validator tests, Markdown + JSON for cookbook artifacts, Context7/current official docs for implementation-sensitive external APIs.

**Spec:** `MAYA_IMPLEMENTATION_COMPILER_V3_DESIGN.md` approved by the user; implementation snapshot is `ef00714c86d3d7b5684d693da35aa82595a088d4`.

## Global Constraints

- Behavioral authority order is: `DOCS.md` > `SECURITY.md` > `ARCHITECTURE.md` > `CONFIG.md` > `UI.md` > `PLAN.md` > `TASKS.md` > `EXECUTION.md`.
- Repository implementation truth is established from current Git tree/code/tests/CI before stale task-ledger prose.
- Do not implement PH-050–PH-180 production code while generating the cookbook.
- Do not redesign PH-000–PH-040 without a concrete future-blocking defect.
- One resident Python process remains the preferred runtime model.
- No local LLM, heavy agent framework, Electron, React/Vite runtime, unrestricted browser automation, or hidden policy bypass may enter the cookbook.
- Project H final resident cgroup target remains `MemoryHigh=240M`, `MemoryMax=300M`.
- Pre-wake audio remains local, memory-only, untranscribed, and off-network.
- Policy approval remains mandatory before executors; model/tool IDs never grant trust by themselves.
- Every queue/buffer/history/output/transcript/agent loop must have an explicit bound.
- Security-sensitive schemas must define strictness/unknown-field behavior explicitly; `frozen=True` is not treated as deep immutability.
- Default automated tests must not consume hosted NVIDIA/OpenAI-compatible API quota.
- External API details must be reverified from current authoritative docs at cookbook generation and again at phase execution.
- Phase execution packets target roughly 3k–8k tokens normally, 10k–15k only for security-heavy phases.
- No `TBD`/`TODO`/`FIXME` may remain in frozen cookbook artifacts.
- Freeze is blocked unless all mandatory counters are zero.

## Review Focus

1. **Stale implementation state:** a task ledger or old review says one thing while current `main` contains something else; validator/inventory must prefer pinned Git evidence for what exists.
2. **Duplicate ownership:** two future phases claim the same public symbol/state owner; machine validation must fail rather than let the later phase improvise.
3. **False security coverage:** a test name claims a race/attack but setup never performs it; test recipes must include explicit attack/fault-injection steps.
4. **Unbounded resource:** a queue/history/audio/provider/tool-output structure has no hard maximum or limit behavior; resource audit must fail freeze.
5. **External API drift:** cookbook references an SDK/browser/system API that current docs no longer support; external-doc ledger must mark it unresolved and block affected phase freeze.

---

## File Structure Locked by This Plan

### Documentation artifacts

Create under `Docs/ImplementationCookbook/`:

- `00_FREEZE_MANIFEST.md` — pinned SHAs, cookbook version, freeze counters, final hashes.
- `01_AUTHORITY_MAP.md` — authority hierarchy, source blob SHAs, conflict decisions.
- `02_REQUIREMENTS.md` — human-readable atomic requirement ledger.
- `03_CURRENT_CODE_MODEL.md` — relevant existing files/symbols and KEEP/EXTEND/etc classification.
- `04_FINAL_SYSTEM_ARCHITECTURE.md` — one PH-180 end-state dependency/data-flow model.
- `05_TRUST_BOUNDARIES.md`
- `06_STATE_OWNERSHIP.md`
- `07_OBJECT_LIFETIMES.md`
- `08_COMPOSITION_ROOT.md`
- `09_PUBLIC_INTERFACES.md`
- `10_DATA_SCHEMAS.md`
- `11_STATE_MACHINES.md`
- `12_CONCURRENCY.md`
- `13_ERRORS_RETRIES_CANCELLATION.md`
- `14_RESOURCE_BUDGET.md`
- `15_SECURITY_MODEL.md`
- `16_FILE_OWNERSHIP.md`
- `17_REFERENCE_CODE_CAPSULES.md`
- `18_TEST_FIXTURES.md`
- `19_TEST_MATRIX.md`
- `20_FAILURE_MATRIX.md`
- `21_END_TO_END_JOURNEYS.md`
- `phases/PH050.md` through `phases/PH180.md`
- `machine/authority.json`
- `machine/requirements.json`
- `machine/symbols.json`
- `machine/interfaces.json`
- `machine/file_owners.json`
- `machine/phase_manifest.json`
- `machine/tests.json`
- `machine/dependencies.json`
- `execution/MASTER_EXECUTION_PROMPT.md`
- `execution/CHECKPOINT_SCHEMA.json`
- `execution/DELTA_CHECK.md`
- `execution/REVIEW_CHECKLIST.md`

### Validation tooling

Create:

- `tools/cookbook/__init__.py`
- `tools/cookbook/model.py` — typed internal dataclasses/Pydantic models for manifest loading.
- `tools/cookbook/inventory.py` — AST/source inventory from a pinned checkout.
- `tools/cookbook/validate.py` — cross-artifact freeze validator.
- `tools/cookbook/fingerprint.py` — deterministic SHA-256 fingerprints for frozen manifests.
- `tests/test_cookbook_inventory.py`
- `tests/test_cookbook_validation.py`
- `tests/fixtures/cookbook/` — small synthetic manifests for validator tests.

Do not add these modules to the runtime `app` package.

---

### Task 1: Pin Snapshot and Bootstrap the Cookbook Skeleton

**Files:**
- Create: `Docs/ImplementationCookbook/00_FREEZE_MANIFEST.md`
- Create: `Docs/ImplementationCookbook/01_AUTHORITY_MAP.md`
- Create: `Docs/ImplementationCookbook/machine/authority.json`
- Create: empty directory structure for `phases/`, `machine/`, and `execution/`
- Test: `tests/test_cookbook_validation.py` (first baseline checks)

**Interfaces:**
- Consumes: pinned Git tree at `ef00714c86d3d7b5684d693da35aa82595a088d4`.
- Produces: canonical snapshot metadata consumed by every later cookbook task.

- [ ] **Step 1: Write failing snapshot tests**

Add tests asserting `machine/authority.json` contains:
- `base_sha == "ef00714c86d3d7b5684d693da35aa82595a088d4"`
- exact authority order;
- blob SHA for every authority document;
- Python floor `>=3.11`;
- target OS `Ubuntu`;
- cookbook status initially `DRAFT`.

Run: `pytest tests/test_cookbook_validation.py -v`  
Expected: FAIL because cookbook files do not exist.

- [ ] **Step 2: Verify pinned remote state before writing artifacts**

Check current `main`, base commit, tree SHA, CI run, and authority-file blob SHAs. Record any divergence rather than silently updating the base.

- [ ] **Step 3: Create skeleton and snapshot metadata**

Populate only immutable snapshot/authority information. Do not yet claim requirement completeness.

- [ ] **Step 4: Run snapshot tests**

Run: `pytest tests/test_cookbook_validation.py -v`  
Expected: snapshot assertions PASS.

- [ ] **Step 5: Commit**

```bash
git add Docs/ImplementationCookbook tests/test_cookbook_validation.py
git commit -m "docs(cookbook): pin implementation compiler snapshot"
```

---

### Task 2: Build the Machine Manifest Model and Freeze Validator

**Files:**
- Create: `tools/cookbook/__init__.py`
- Create: `tools/cookbook/model.py`
- Create: `tools/cookbook/validate.py`
- Create: `tools/cookbook/fingerprint.py`
- Modify: `tests/test_cookbook_validation.py`
- Create: `tests/fixtures/cookbook/valid_minimal/`
- Create: `tests/fixtures/cookbook/invalid_*/`

**Interfaces:**
- Consumes: cookbook JSON files.
- Produces:
  - `load_cookbook(root: Path) -> CookbookModel`
  - `validate_cookbook(model: CookbookModel) -> list[ValidationIssue]`
  - `fingerprint_json(path: Path) -> str`

- [ ] **Step 1: Write failing validator tests**

Cover duplicate public interface owner, unmapped requirement, acceptance criterion without test, file without owner phase, illegal forward dependency, resource without bound, security invariant without test, unknown referenced symbol, duplicate IDs, and nonzero freeze counters.

- [ ] **Step 2: Implement canonical manifest models**

Use small typed records with explicit required fields. Unknown machine-manifest keys must be rejected rather than ignored.

- [ ] **Step 3: Implement deterministic validation**

Each issue returns:

```python
ValidationIssue(
    code: str,
    path: str,
    message: str,
    severity: Literal["critical", "important", "warning"],
)
```

- [ ] **Step 4: Implement deterministic fingerprints**

Canonical JSON: UTF-8, sorted keys, no insignificant whitespace, reject NaN/Infinity, SHA-256 lowercase hex.

- [ ] **Step 5: Run validator tests**

Run: `pytest tests/test_cookbook_validation.py -v`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/cookbook tests/test_cookbook_validation.py tests/fixtures/cookbook
git commit -m "test(cookbook): add freeze manifest validator"
```

---

### Task 3: Reverse-Engineer the Current Codebase into `symbols.json`

**Files:**
- Create: `tools/cookbook/inventory.py`
- Create: `tests/test_cookbook_inventory.py`
- Create: `Docs/ImplementationCookbook/machine/symbols.json`
- Create: `Docs/ImplementationCookbook/03_CURRENT_CODE_MODEL.md`

**Interfaces:**
- Consumes: pinned repository source.
- Produces: `inventory_python_tree(root: Path) -> SymbolInventory` and machine-readable symbol records.

- [ ] **Step 1: Write AST inventory tests** for modules, classes, functions, async functions, methods, signatures, imports, constants, and bases.
- [ ] **Step 2: Implement inventory using `ast` only**; never import/execute repository modules.
- [ ] **Step 3: Generate pinned inventory** for `app/`, tests, `pyproject.toml`, CI workflow, and integration stubs relevant to PH-050→180.
- [ ] **Step 4: Manually enrich classifications** with state ownership, side effects, security role, resource ownership, test coverage, and KEEP/EXTEND/etc status.
- [ ] **Step 5: Cross-check inventory against Git tree** so no relevant source file is silently omitted.
- [ ] **Step 6: Run inventory + validator tests**.
- [ ] **Step 7: Commit** with message `docs(cookbook): inventory current Maya code`.

---

### Task 4: Compile Atomic Requirements and Resolve Authority Conflicts

**Files:**
- Create: `02_REQUIREMENTS.md`
- Complete: `01_AUTHORITY_MAP.md`
- Create: `machine/requirements.json`
- Modify: `machine/authority.json`
- Test: `tests/test_cookbook_validation.py`

**Interfaces:**
- Consumes: eight authority docs + current code/CI state.
- Produces: atomic requirement IDs and conflict ledger.

- [ ] Extract requirements document-by-document in authority order.
- [ ] Record implementation-state contradictions separately from behavioral authority conflicts.
- [ ] Create conflict ledger with higher authority, lower source/current code, decision, rationale, affected phases, required repair.
- [ ] Map every requirement provisionally to PH-050…PH-180 or explicitly justified `OUT_OF_V1`.
- [ ] Add validator rules for unique IDs, valid source, valid phase, and `OUT_OF_V1` rationale.
- [ ] Run validation; expected unmapped provisional requirements = 0.
- [ ] Commit `docs(cookbook): compile Maya authority requirements`.

---

### Task 5: Freeze Final PH-180 Architecture, Dependency Graph, State and Lifetimes

**Files:**
- Create: `04_FINAL_SYSTEM_ARCHITECTURE.md`
- Create: `05_TRUST_BOUNDARIES.md`
- Create: `06_STATE_OWNERSHIP.md`
- Create: `07_OBJECT_LIFETIMES.md`
- Create: `08_COMPOSITION_ROOT.md`
- Create: `machine/dependencies.json`
- Modify: `machine/requirements.json`

**Interfaces:**
- Consumes: current code model + atomic requirements.
- Produces: one final component graph and ownership model.

- [ ] Define final components and allowed dependency edges.
- [ ] Add validator failures for provider→OS, dashboard→shell, extension→policy bypass, executor→post-execution policy, agent→direct arbitrary filesystem, and circular dependencies.
- [ ] Define validation/authorization/bounds/audit/failure behavior for every trust crossing.
- [ ] Assign exactly one owner to every mutable state object.
- [ ] Define lifetimes, construction order, and shutdown order.
- [ ] Validate no illegal edges/duplicate owners/cycles.
- [ ] Commit `docs(cookbook): freeze final Maya system model`.

---

### Task 6: Freeze Public Interfaces, Data Schemas, State Machines and Failure Semantics

**Files:**
- Create: `09_PUBLIC_INTERFACES.md`
- Create: `10_DATA_SCHEMAS.md`
- Create: `11_STATE_MACHINES.md`
- Create: `12_CONCURRENCY.md`
- Create: `13_ERRORS_RETRIES_CANCELLATION.md`
- Create: `machine/interfaces.json`

**Interfaces:**
- Consumes: final system model.
- Produces: canonical signatures/contracts used verbatim by phase packets.

- [ ] Freeze ApprovalBroker/PopupBackend, AIProvider/NvidiaProvider, CommandRouter, AgentRuntime/AgentTask, WakeDetector/Recorder, STTProvider, tray, BrowserBridge/native protocol, site adapters, storage/audit, FastAPI composition, developer workflow interfaces.
- [ ] Freeze schema fields, bounds, strictness, unknown-field behavior, serialization, and versioning.
- [ ] Freeze voice/approval/agent/provider/browser/daemon state machines.
- [ ] Freeze task/queue/semaphore/lock ownership, capacity, backpressure, and shutdown.
- [ ] Freeze timeout/retry/idempotency/error semantics.
- [ ] Add validator rules for conflicting signatures, undefined states, unbounded queues, unsafe non-idempotent retries.
- [ ] Commit `docs(cookbook): freeze Maya implementation interfaces`.

---

### Task 7: Verify External APIs and Freeze Resource/Security/Dependency Rules

**Files:**
- Create: `14_RESOURCE_BUDGET.md`
- Create: `15_SECURITY_MODEL.md`
- Create: `16_FILE_OWNERSHIP.md`
- Create: `machine/file_owners.json`

**Interfaces:**
- Consumes: current authoritative external docs + frozen interfaces.
- Produces: API ledger, security matrix, resource budgets, file ownership.

- [ ] Verify Pydantic v2, FastAPI, OpenAI Python/AsyncOpenAI, NVIDIA provider specifics, openWakeWord, Firefox WebExtension/Native Messaging, systemd, D-Bus/SNI, SQLite layer, asyncio/subprocess/path APIs.
- [ ] Record source/date/version/API surface; unresolved external API blocks affected phase.
- [ ] Freeze runtime dependency choices and resident/lazy lifetime.
- [ ] Build resource budget with hard bounds and estimated-vs-measured labels.
- [ ] Build security matrix: asset, attacker/source, primary enforcement, defense-in-depth, test ID, phase.
- [ ] Assign every future file one primary owner and forbidden responsibilities.
- [ ] Validate zero unowned files, zero unbounded resident structures, zero security invariants without test placeholders.
- [ ] Commit `docs(cookbook): freeze security and resource contracts`.

---

### Task 8: Build Reference Code Capsules, Fakes, Test Matrix and Failure Matrix

**Files:**
- Create: `17_REFERENCE_CODE_CAPSULES.md`
- Create: `18_TEST_FIXTURES.md`
- Create: `19_TEST_MATRIX.md`
- Create: `20_FAILURE_MATRIX.md`
- Create: `machine/tests.json`

**Interfaces:**
- Consumes: frozen interfaces/security/resource contracts.
- Produces: reusable low-token implementation/test patterns.

- [ ] Write Tier-A near-complete capsules for approval grants, bounded async structures, cancellation ownership, provider stream/tool parsing, bounded context, authenticated local messages, storage transactions, secret-safe audit, lifecycle ownership.
- [ ] Write Tier-B/Tier-C patterns for ordinary services/UI/packaging.
- [ ] Freeze reusable fakes for AI/STT/popup/browser/audio/wake/clock/audit/executor.
- [ ] Build requirement→test matrix; security requirements require negative/adversarial tests.
- [ ] Build failure matrix for restart/crash/provider/browser/audio/config/storage/disk/cancellation/shutdown/memory pressure.
- [ ] Require `attack_setup` or `fault_injection` plus `assert_not` for security-test entries.
- [ ] Validate + commit `docs(cookbook): add implementation and test capsules`.

---

### Task 9: Compile PH-050, PH-060, PH-070

**Files:** `phases/PH050.md`, `PH060.md`, `PH070.md`, machine manifests.

- [ ] PH-050: exact dispatcher anchors, ApprovalBroker algorithm, fake popup first, real transient popup second, timeout/hash/single-use/restart semantics, tests, stop boundary.
- [ ] PH-060: verified reusable AsyncOpenAI client, custom NVIDIA base URL, explicit timeout, `max_retries=0`, streaming/tool parsing, reasoning filtering, fake transport/default no-live-call tests.
- [ ] PH-070: exact deterministic routing order and bounded single logical agent loop; every tool proposal through existing dispatcher/policy.
- [ ] Run fresher scan on every instruction and expand any remaining design choice.
- [ ] Validate + commit `docs(cookbook): compile PH-050 through PH-070`.

---

### Task 10: Compile PH-080, PH-090, PH-100

**Files:** `phases/PH080.md`, `PH090.md`, `PH100.md`, machine manifests.

- [ ] PH-080: audio source/wake abstractions, bounded ring, post-wake capture, VAD, shutdown, no-network proof, wake-engine RSS gate.
- [ ] PH-090: verify current NVIDIA STT model/API before freezing; define audio ownership/release and failure→no execution.
- [ ] PH-100: freeze SNI/D-Bus lifecycle, core callbacks, manual Ubuntu matrix, RSS delta measurement.
- [ ] Validate + commit.

---

### Task 11: Compile PH-110, PH-120

**Files:** `phases/PH110.md`, `PH120.md`, machine manifests.

- [ ] PH-110: protocol version/envelope/auth/framing/size/replay/session behavior; daemon permission + Firefox host permission + current-origin gates.
- [ ] PH-120: Generic/Google/Amazon/ChatGPT/Gemini/Claude adapter contracts, semantic selectors, DOM fixtures, live smoke, outdated failure.
- [ ] Red-team origin/domain/host permission/password field/prompt injection/oversized extraction/stale adapter.
- [ ] Validate + commit.

---

### Task 12: Compile PH-130, PH-140, PH-150

**Files:** `phases/PH130.md`, `PH140.md`, `PH150.md`, machine manifests.

- [ ] PH-130: FastAPI app factory/lifespan ownership, localhost-only, same-origin, no wildcard CORS, CRUD validation, paginated history/audit, bounded events.
- [ ] PH-140: exact static HTML/JS structure, IDs/events/state payloads, local Bootstrap CSS, SVG AI core, reduced motion, hidden-tab pause, performance/accessibility gates; no React/Vite.
- [ ] PH-150: repo registration, git status/diff, VS Code CLI, test commands under policy, edit→test→verify, no auto-commit default.
- [ ] Validate + commit.

---

### Task 13: Compile PH-160, PH-170, PH-180

**Files:** `phases/PH160.md`, `PH170.md`, `PH180.md`, machine manifests.

- [ ] PH-160: exact stress scenario, measurement commands, resident-vs-external accounting, peak RSS/CPU capture, fail procedure; never raise MemoryMax.
- [ ] PH-170: user systemd unit, config install, native-host manifest, extension packaging, first-run, uninstall/rollback, permissions.
- [ ] PH-180: map every V1 requirement to final unit/integration/security/manual/resource/install evidence, including deterministic offline behavior while NVIDIA unavailable.
- [ ] Validate + commit.

---

### Task 14: Build End-to-End Journeys and Master One-Prompt Executor

**Files:**
- Create: `21_END_TO_END_JOURNEYS.md`
- Create: `execution/MASTER_EXECUTION_PROMPT.md`
- Create: `execution/CHECKPOINT_SCHEMA.json`
- Create: `execution/DELTA_CHECK.md`
- Create: `execution/REVIEW_CHECKLIST.md`

- [ ] Trace mandatory journeys through exact symbols/tests.
- [ ] Freeze compact checkpoint schema with phase, cookbook version, SHAs, interfaces, files, tests, CI, memory note, findings, next action; no secrets/transcripts.
- [ ] Write delta-check based on repo/interface fingerprints.
- [ ] Write master executor: one phase packet at a time, no full-cookbook reinjection, RED→GREEN→review→regression→commit/checkpoint, bounded repair, stop conditions, context compaction.
- [ ] Validator requires every phase manifest entry to define reads/create/modify/forbidden/tests/capsules/output interfaces/stop conditions.
- [ ] Commit.

---

### Task 15: Run Four Independent Review Passes and Repair Findings

- [ ] **Architecture review:** placement, dependencies, composition, state/lifetime ownership, undefined interfaces, duplicate responsibility.
- [ ] **Security review:** malicious model/config/browser/file/symlink/provider/popup/native/storage inputs; every attack maps to enforcement + defense + real test.
- [ ] **Fresher review:** assume syntax-only implementer; expand anything requiring design judgment.
- [ ] **Token-efficiency review:** remove repetition/history/duplicate code while preserving signatures, algorithms, bounds, placement, tests, stop conditions.
- [ ] Re-run validator; zero Critical/Important findings required.
- [ ] Commit review repairs.

---

### Task 16: Forward Simulation, Reverse Traceability and Final Freeze

**Files:** update `00_FREEZE_MANIFEST.md` and machine manifests only as defects require.

- [ ] Run forward simulation for deterministic action, approval, coding agent, always-listen voice, browser, restart-pending-approval, provider outage, dashboard config change, packaging startup.
- [ ] Run reverse trace: final acceptance → test → integration → interface → symbol → phase → authority requirement.
- [ ] Run:

```bash
python -m tools.cookbook.validate Docs/ImplementationCookbook
pytest tests/test_cookbook_inventory.py tests/test_cookbook_validation.py -v
```

Expected all mandatory counters = 0.

- [ ] Generate `COOKBOOK_VERSION`, `BASE_SHA`, `INTERFACE_HASH`, `REQUIREMENT_MAP_HASH`, `PHASE_MANIFEST_HASH`.
- [ ] Run full existing regression:

```bash
pytest -v
python -m pip install -e ".[dev]"
git diff --check
```

- [ ] Set `STATUS: FROZEN` only if all counters/reviews pass; otherwise `BLOCKED` with exact unresolved IDs.
- [ ] Commit `docs(cookbook): freeze PH-050 through PH-180 implementation compiler`.

---

## Execution Boundary

This plan ends when the cookbook is `FROZEN` or explicitly `BLOCKED`.

It does **not** begin PH-050 production implementation.

After a successful freeze, execution starts from the generated `execution/MASTER_EXECUTION_PROMPT.md` and `phases/PH050.md` using the delta-check procedure.
