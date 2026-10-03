# MAYA Implementation Compiler V3 — Design Specification

**Status:** DRAFT FOR USER REVIEW  
**Repository:** `prashantjadon311/Maya-01`  
**Cookbook base SHA:** `ef00714c86d3d7b5684d693da35aa82595a088d4`  
**Base evidence:** GitHub Actions run `37107781413` completed successfully on the base SHA.  
**Scope:** Generate an implementation-complete cookbook for PH-050 through PH-180.  
**Important:** This document defines how the cookbook will be built. It does **not** implement PH-050 or later production code.

---

## 1. Purpose

The cookbook must let a very junior implementation engineer, assumed to know Python syntax but not system design, algorithms, security architecture, concurrency design, or failure-mode reasoning, implement Maya from PH-050 through PH-180 with minimal architectural guessing.

The target implementation model is not expected to invent architecture. Its primary job should be:

1. read a small phase-local packet;
2. translate reference contracts and algorithms into code;
3. run prescribed tests;
4. fix implementation defects without changing architecture;
5. produce evidence;
6. stop at the exact phase boundary.

The cookbook therefore behaves more like a **compiled engineering specification** than ordinary documentation.

---

## 2. Success Criteria

The cookbook may be marked `FROZEN` only when all of the following are true:

- every authority requirement is mapped to a phase, file, symbol, and test;
- every future public interface has one canonical definition;
- every future file has an owner phase;
- every mutable state object has one owner;
- every long-lived object has an explicit lifetime and shutdown owner;
- every non-trivial function has an implementation recipe;
- every security boundary has a primary enforcement point, defense-in-depth point, and adversarial test;
- every queue, buffer, transcript, output stream, history, cache, and agent loop has an explicit bound;
- every external API used by the design is verified against current authoritative documentation;
- every phase has exact entry conditions, implementation steps, tests, verification commands, stop conditions, and output contracts;
- forward PH-050→PH-180 simulation passes;
- reverse PH-180→requirements traceability passes;
- a “fresher simulation” finds no remaining design decision that the implementer must guess;
- token-compression review removes duplication without removing signatures, invariants, algorithms, bounds, or tests.

Freeze counters must satisfy:

```text
UNMAPPED_REQUIREMENTS = 0
UNTESTED_ACCEPTANCE_CRITERIA = 0
UNRESOLVED_PUBLIC_INTERFACES = 0
UNRESOLVED_SECURITY_INTERFACES = 0
UNOWNED_FUTURE_FILES = 0
CIRCULAR_DEPENDENCIES = 0
UNBOUNDED_RESIDENT_STRUCTURES = 0
CRITICAL_GAPS = 0
IMPORTANT_GAPS = 0
GUESS_REQUIRED_IMPLEMENTATION_ITEMS = 0
```

---

## 3. Authority and Evidence Model

### 3.1 Behavioral authority order

Use the existing Project H authority order:

1. `Docs/DOCS.md`
2. `Docs/SECURITY.md`
3. `Docs/ARCHITECTURE.md`
4. `Docs/CONFIG.md`
5. `Docs/UI.md`
6. `Docs/PLAN.md`
7. `Docs/TASKS.md`
8. `Docs/EXECUTION.md`

A lower-authority file must never silently override a higher-authority contract.

### 3.2 Actual repository-state evidence

Behavioral intent and implementation state are different concepts.

The cookbook compiler must determine implementation state from:

1. current Git commit and tree;
2. current source code;
3. current tests;
4. current CI evidence;
5. merged PR/commit evidence;
6. task ledger only after the above.

If `TASKS.md` says a PR is awaiting merge but `main` already contains the merge commit, the repository state wins for **what exists**, while higher-authority documents still win for **what behavior should be**.

### 3.3 Immutable snapshot

The compiler records:

```text
COOKBOOK_BASE_SHA
DOCS_BLOB_SHA
SECURITY_BLOB_SHA
ARCHITECTURE_BLOB_SHA
CONFIG_BLOB_SHA
UI_BLOB_SHA
PLAN_BLOB_SHA
TASKS_BLOB_SHA
EXECUTION_BLOB_SHA
PYTHON_TARGETS
OS_TARGET
```

Implementation must run a delta check against this snapshot before every phase.

---

## 4. Core Design Principle

The cookbook is generated in this order:

```text
CURRENT REPOSITORY TRUTH
        +
AUTHORITY REQUIREMENTS
        +
CURRENT EXTERNAL API DOCUMENTATION
        ↓
FINAL PH-180 SYSTEM MODEL
        ↓
TRUST / STATE / LIFETIME / COMPOSITION MODEL
        ↓
PUBLIC + INTERNAL INTERFACE FREEZE
        ↓
ALGORITHM + FAILURE + CONCURRENCY FREEZE
        ↓
FILE / SYMBOL OWNERSHIP
        ↓
REFERENCE CODE + TEST BLUEPRINTS
        ↓
PHASE PACKETS PH-050 → PH-180
        ↓
FORWARD + REVERSE + SECURITY + FRESHER AUDITS
        ↓
TOKEN-COMPRESSION PASS
        ↓
FROZEN COOKBOOK
```

The final architecture is designed first and then divided into phases. Phases must not accidentally invent the final architecture while being implemented.

---

## 5. Compiler Pipeline

### Stage 0 — Pin the repository snapshot
Record the exact base SHA, authority blob SHAs, test baseline, CI baseline, supported Python versions, and target Ubuntu environment.

### Stage 1 — Atomic requirement compilation
Convert every authority statement into atomic IDs and map each requirement to source, phase, component, file, symbol, test, and acceptance evidence.

### Stage 2 — Current-code reverse engineering
Inventory relevant existing symbols with signature, callers, callees, owned state, dependencies, side effects, security role, resource ownership, tests, and status (`KEEP`, `EXTEND`, `REFACTOR_IN_PLACE`, `REPLACE_LATER`, `DEPRECATED`, `DO_NOT_TOUCH`).

### Stage 3 — Conflict and gap ledger
Record every authority/code/test/task-ledger conflict with an explicit decision, reason, affected phases, and required repair. Security-relevant conflicts cannot remain unresolved at freeze.

### Stage 4 — Final PH-180 system model
Build the complete end-state architecture before individual phases. Every architectural edge must map to a declared interface.

### Stage 5 — Trust-boundary model
Classify every input/state source and define validation, authorization, bounds, sanitization, audit, and failure behavior.

### Stage 6 — State-ownership model
Every mutable state item gets exactly one owner, with mutators, readers, persistence, synchronization, lifetime, and reset conditions.

### Stage 7 — Object-lifetime model
Classify important objects as daemon/session/task/command/request/transient lifetime. Specify creator and closer.

### Stage 8 — Composition-root and shutdown freeze
Define exact application assembly, dependency injection, construction order, and shutdown order. Shared services may not be recreated opportunistically.

### Stage 9 — Public-interface freeze
Every public symbol gets exact signature, caller, inputs, trust level, preconditions, outputs, postconditions, side effects, timeout, cancellation, idempotency, concurrency, audit, errors, and bounds.

### Stage 10 — Internal schema freeze
Freeze Pydantic/dataclass/enums/events/HTTP/native-messaging/UDS/browser/audit/SQLite/config/checkpoint schemas, including unknown-field behavior, bounds, defaults, serialization, and versioning.

Security-sensitive Pydantic schemas must explicitly decide strictness and extra-field handling. `frozen=True` must not be treated as deep immutability because nested mutable objects remain mutable.

### Stage 11 — Algorithm freeze
Every non-trivial function receives deterministic step-by-step logic. The implementation model does not invent routing, retries, approval semantics, trimming, queue policy, or state transitions.

### Stage 12 — State-machine freeze
Stateful subsystems get explicit FROM/EVENT/TO/ACTION/CLEANUP/ILLEGAL transition tables.

### Stage 13 — Concurrency model
Specify task creator/owner/canceller/awaiter, locks, semaphores, bounded queues, backpressure, and shutdown behavior.

### Stage 14 — Cancellation, timeout, retry, idempotency
Every network/subprocess/approval/STT/browser/agent/storage operation defines timeout ownership, cleanup, cancellation, retryability, idempotency, and duplicate-execution prevention.

### Stage 15 — Error taxonomy
Freeze canonical error categories and define raiser, catcher, user-facing category, audit code, retryability, and state transition.

### Stage 16 — Resource ownership and cleanup
Every fd, subprocess, socket, HTTP client, microphone stream, SQLite connection, temp file, D-Bus object, and asyncio task has acquisition/owner/cleanup/failure cleanup.

### Stage 17 — Privacy / secret / retention model
For each sensitive data type define RAM, disk, logging, remote transmission, retention, and redaction rules.

### Stage 18 — Dependency-selection record
Every runtime dependency records why required, version/range, resident/lazy behavior, memory effect, alternatives, initialization, and closing.

### Stage 19 — External API verification lane
Verify implementation-sensitive APIs against current authoritative docs during cookbook generation and immediately before execution. Record source, date, version, exact API surface, and consuming phases.

### Stage 20 — File ownership map
Every future file gets one primary owner phase, secondary modifiers, purpose, public symbols, allowed contents, and forbidden contents.

### Stage 21 — Symbol-level modification anchors
Each phase identifies exact symbols to modify and exact adjacent behavior that must remain unchanged. Use symbols/hashes, not fragile line numbers.

### Stage 22 — Reference-code tiers
- **Tier A, 70–95% reference implementation:** security-critical/logic-heavy code.
- **Tier B:** complete signatures + detailed algorithm + critical branches for ordinary infrastructure.
- **Tier C:** declarative structure for straightforward UI/packaging where full code would waste context.

### Stage 23 — Forbidden-code blocks
Each phase explicitly lists shortcuts and architectures that must not be introduced.

### Stage 24 — Exact test cookbook
Every test specifies requirement ID, file, fixture, Arrange, fault injection, Act, Assert, Assert-NOT, and cleanup. Cover happy path, malformed input, security negatives, boundaries, concurrency, cancellation, timeout, restart, resource exhaustion, dependency failure, stale state, TOCTOU, and secret non-disclosure.

### Stage 25 — Reusable fake/fixture architecture
Freeze shared fakes such as `FakeAIProvider`, `FakeSTTProvider`, `FakePopupBackend`, `FakeBrowserBridge`, `FakeAudioSource`, `FakeWakeDetector`, `FakeClock`, `FakeAuditSink`, and `FakeExecutor`. Default tests must not burn hosted API quota.

### Stage 26 — Proof-of-test rule
A security test counts only if it actually performs or deterministically simulates the claimed attack. Comments are not evidence.

### Stage 27 — Phase micro-implementation order
Each phase becomes small steps with allowed files, expected RED, implementation action, expected GREEN, and regression subset.

### Stage 28 — Debugging decision tree
Packets define what to do when expected RED does not fail, implementation fails, unrelated regression appears, authority/test disagree, external API changes, or memory shifts.

### Stage 29 — Phase input contract
Every phase lists exactly what the coding model reads and what it must not read by default. This is a primary token-saving mechanism.

### Stage 30 — Machine-readable phase manifest
Every phase gets JSON metadata for required reads, creates, modifications, tests, capsules, dependencies, and expected outputs.

### Stage 31 — Context-budget design
Ordinary phase packet target: ~3k–8k tokens plus exact source snippets. Security-heavy packet: ~10k–15k where needed. Never inject the full master cookbook into every phase.

### Stage 32 — One-prompt multi-phase execution architecture
The master prompt iterates phase manifests: delta check → implement → targeted tests → review → required regression → commit/checkpoint → compact context → next phase. Fresh phase contexts are preferred where the executor supports them.

### Stage 33 — Automatic stop conditions
Stop on authority conflict, unresolved security failure, unclear full regression failure, bounded CI repair failure, external API divergence, memory-budget violation, cookbook/interface mismatch, unexpected repo divergence, or human-only decision. Do not stop for ordinary syntax/implementation fixes.

### Stage 34 — Git/checkpoint strategy
Each phase records base SHA, changes, tests, review evidence, commit SHA, CI, interfaces produced, limitations, and next action. No PH-050→PH-180 mega-commit.

### Stage 35 — Forward end-to-end simulation
Trace deterministic command, approved process, coding agent, always-listening voice, browser action, daemon restart, and provider outage journeys through actual declared symbols.

### Stage 36 — Reverse PH-180 traceability
Every final acceptance item must trace backward through test → integration → interface → symbol → phase → authority requirement.

### Stage 37 — Fresher-simulation audit
For every instruction ask whether a syntax-only junior could choose the wrong file/class, duplicate state, invent unsafe logic, miss cleanup/bounds, trust input, misuse network/retries, create a false-positive test, use an incompatible API, or broaden permissions. Any `yes` means more detail is required.

### Stage 38 — Adversarial security audit
Assume malicious model output, action pack, config, browser page, native client, file path, symlink, subprocess output, popup response, provider response, and persisted state. Map every abuse case to primary enforcement, defense-in-depth, and test.

### Stage 39 — Resource audit
For every list/dict/deque/queue/buffer/transcript/message/DOM/audio/output structure define maximum size, enforcer, behavior at limit, and resident/lazy/ephemeral status.

### Stage 40 — Token-efficiency compression pass
After correctness freezes, remove repeated prose/code and replace repetition with stable capsule/interface references. Never compress away signatures, trust, invariants, algorithms, bounds, tests, placement, lifecycle, or stop conditions.

### Stage 41 — Machine consistency checks
Verify referenced symbols, ownership, requirement/test mapping, dependency direction, canonical signatures, file ownership, bounds, and security-test coverage.

### Stage 42 — Freeze fingerprints
Generate `COOKBOOK_VERSION`, `BASE_SHA`, `INTERFACE_HASH`, `REQUIREMENT_MAP_HASH`, and `PHASE_MANIFEST_HASH`.

---

## 6. Required Cookbook Artifact Tree

```text
Docs/ImplementationCookbook/
00_FREEZE_MANIFEST.md
01_AUTHORITY_MAP.md
02_REQUIREMENTS.md
03_CURRENT_CODE_MODEL.md
04_FINAL_SYSTEM_ARCHITECTURE.md
05_TRUST_BOUNDARIES.md
06_STATE_OWNERSHIP.md
07_OBJECT_LIFETIMES.md
08_COMPOSITION_ROOT.md
09_PUBLIC_INTERFACES.md
10_DATA_SCHEMAS.md
11_STATE_MACHINES.md
12_CONCURRENCY.md
13_ERRORS_RETRIES_CANCELLATION.md
14_RESOURCE_BUDGET.md
15_SECURITY_MODEL.md
16_FILE_OWNERSHIP.md
17_REFERENCE_CODE_CAPSULES.md
18_TEST_FIXTURES.md
19_TEST_MATRIX.md
20_FAILURE_MATRIX.md
21_END_TO_END_JOURNEYS.md
phases/PH050.md ... PH180.md
machine/authority.json
machine/requirements.json
machine/symbols.json
machine/interfaces.json
machine/file_owners.json
machine/phase_manifest.json
machine/tests.json
machine/dependencies.json
execution/MASTER_EXECUTION_PROMPT.md
execution/CHECKPOINT_SCHEMA.json
execution/DELTA_CHECK.md
execution/REVIEW_CHECKLIST.md
```

Markdown is human-readable authority. JSON exists for consistency checks and low-token context selection.

---

## 7. Mandatory Per-Phase Packet Schema

Every phase file contains, in order:

1. Purpose
2. Entry conditions
3. Required input context
4. Existing symbols reused
5. Files created
6. Files modified
7. Files forbidden to modify
8. Dependencies
9. State owned
10. Object lifetime
11. Public interfaces produced
12. Internal schemas
13. Exact algorithms
14. Reference implementation
15. Concurrency model
16. Cancellation behavior
17. Timeout behavior
18. Retry/idempotency behavior
19. Error behavior
20. Security invariants
21. Resource limits
22. Secrets/privacy behavior
23. Failure cases
24. Fakes/fixtures
25. Exact tests
26. Adversarial tests
27. Manual/live checks
28. Implementation micro-order
29. Expected RED/GREEN points
30. Verification commands
31. Memory measurement
32. Git/checkpoint rules
33. Output contract
34. Next-phase contract
35. Forbidden behavior
36. Stop conditions

No `TBD` is allowed at freeze.

---

## 8. Mandatory Non-Trivial Function Recipe

Every important function/method specifies:

```text
SYMBOL
FILE
PURPOSE
SIGNATURE
CALLED_BY
CALLS
INPUTS + TRUST LEVEL
PRECONDITIONS
ALGORITHM
OUTPUT
POSTCONDITIONS
SIDE EFFECTS
STATE MUTATION
ASYNC BEHAVIOR
LOCKING
TIMEOUT
CANCELLATION
RETRY
IDEMPOTENCY
ERRORS
SECURITY INVARIANTS
RESOURCE BOUNDS
CLEANUP
AUDIT
REFERENCE CODE
UNIT TESTS
NEGATIVE TESTS
DO NOT
```

---

## 9. Fresher-Safe Rules

The cookbook explicitly prevents these common implementation failures:

- creating new shared services inside request handlers;
- global mutable state outside declared owners;
- unbounded queues/history/output;
- broad exception swallowing without translation/cleanup;
- retries on non-idempotent side effects;
- trusting model/browser/provider/config/persisted data merely because it parsed;
- rewriting expected security behavior to make tests green;
- adding heavy dependencies for trivial functionality;
- duplicating existing schemas/interfaces;
- thread/process per logical agent;
- network I/O before wake;
- replacing the Firefox/native-messaging architecture with unrestricted automation;
- broadening file/domain/process permissions to make a workflow pass;
- claiming final memory acceptance before PH-160 stress measurement;
- advancing phases while a stop condition is active.

---

## 10. Token-Minimizing Execution Contract

Per phase, the implementation model receives only:

```text
Docs/SKILL.md
relevant freeze-manifest fields
relevant public-interface sections
relevant code capsules
current PHxxx.md
machine/phase_manifest entry
exact source files named by the manifest
latest compact checkpoint
```

It must not reread all project docs or prior phases unless delta-check escalation requires it.

---

## 11. Delta-Check Contract

Before each phase:

1. fetch current main;
2. compare SHA with expected previous-phase output;
3. verify consumed-interface fingerprints;
4. inspect only changed relevant files;
5. continue if compatible;
6. if incompatible, patch only affected cookbook sections/manifests;
7. rerun relevant consistency checks;
8. never regenerate the whole cookbook for one local interface change.

---

## 12. Mandatory Review Gates

### A. Architecture review
Check dependency direction, ownership, composition, interfaces, placement, duplicate responsibility, and final-system completeness.

### B. Security review
Check authorization, forged trust, TOCTOU, IPC authentication, model/prompt trust, secrets, browser policy, file/process boundaries, fail-open behavior, and resource exhaustion.

### C. Implementability/fresher review
Assume the coder knows syntax but cannot choose architecture/algorithms safely. Any design judgment left to the coder must be expanded.

### D. Token-efficiency review
Remove repetition while preserving implementation-critical detail.

---

## 13. Final Re-Audit Checklist

Before freeze, re-run from scratch:

```text
[ ] Base SHA and authority hashes recorded
[ ] Current-code model matches pinned tree
[ ] Every requirement mapped
[ ] Every final acceptance criterion test-mapped
[ ] Every public interface canonicalized
[ ] Every mutable state has one owner
[ ] Every long-lived object has creator + closer
[ ] Composition root constructs each shared service once
[ ] Every non-trivial function has exact algorithm
[ ] Every async task has owner/cancel/await behavior
[ ] Every queue/buffer/history has a hard bound
[ ] Every retry is safe/idempotent
[ ] Every required security failure is fail-closed
[ ] Every security test actually exercises its claim
[ ] Every external API dependency is doc-verified
[ ] Every future file has owner phase
[ ] Every phase has read/create/modify/forbidden lists
[ ] Every phase has micro-order + RED/GREEN checkpoints
[ ] Every phase defines memory measurement
[ ] Forward PH-050→PH-180 simulation passes
[ ] Reverse PH-180→requirements trace passes
[ ] Fresher simulation has zero guess-required items
[ ] Security review has zero Critical/Important gaps
[ ] Token compression preserved required contracts
[ ] Machine manifests and Markdown agree
[ ] Freeze hashes generated
```

Any failure blocks freeze.

---

## 14. Non-Goals

The cookbook compiler must not:

- implement PH-050–PH-180 production code while building the cookbook;
- redesign PH-000–PH-040 without a concrete future-blocking defect;
- treat chat summaries as code authority;
- treat test count alone as security proof;
- replace the current policy/executor architecture with a parallel design;
- add speculative post-V1 features;
- optimize tokens by deleting lifecycle/security detail;
- declare external APIs from memory when current docs are available.

---

## 15. Cookbook-Generation Definition of Done

The cookbook-generation task completes only when it produces:

1. the full artifact tree in Section 6;
2. all mandatory freeze counters at zero;
3. architecture, security, implementability, and token-efficiency review results;
4. cookbook version and fingerprints;
5. `execution/MASTER_EXECUTION_PROMPT.md` that drives PH-050→PH-180 phase-by-phase;
6. `BLOCKED`, not fake completion, if any freeze gate remains unresolved.

After freeze, the next activity is execution of PH-050 using its frozen packet and delta-check procedure, not free-form implementation.
