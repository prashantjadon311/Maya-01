# Maya Implementation Cookbook — Authority Map & Precedence Rules

## 1. Authority Hierarchy

All specifications, architectural designs, security policies, and implementation requirements follow the strict Project H authority hierarchy:

1. **`Docs/DOCS.md`** (`f0661e12eb37d7cb35468fb998d24e3be9ca61a0`): Supreme behavioural reference.
2. **`Docs/SECURITY.md`** (`018eddf2c193818f2e54f38dfe24639aac8af395`): Security architecture, threat models, boundaries, and approval invariants.
3. **`Docs/ARCHITECTURE.md`** (`60c03ec8ef6122409da8c56020896dfe9f26bbd6`): System layout, state machine, subsystem interactions, and concurrency boundaries.
4. **`Docs/CONFIG.md`** (`0df558337f3fe51a90f7eef6369b22218309879f`): Configuration schema, environment variables, defaults, and bounds.
5. **`Docs/UI.md`** (`33599d1fe7c09f3cd558824bcd13826dd958b302`): Web dashboard, tray UI, and visual contracts.
6. **`Docs/PLAN.md`** (`317d8e583903d901310755ca96db5eab8f090399`): Phase roadmap and milestone deliverables.
7. **`Docs/TASKS.md`** (`f2b8f60c28f023946a3e3c4376c0bba14f585902`): Task breakdown and historical checkpoints.
8. **`Docs/EXECUTION.md`** (`4a41e269f1a46146e87b83829560294b85890563`): Phase execution guidelines and gating criteria.

Additionally, `Docs/SKILL.md` (`3ee7bf617703e36bda264096154bc2609950deea`) acts as operational meta-instruction for autonomous agents working within Maya.

---

## 2. Core Conflict Principles

1. **Higher Authority Wins:** A lower document cannot relax, circumvent, or contradict a rule from a higher document.
2. **Behavioral Authority vs Implementation State:**
   - **Behavioral Authority:** Governed strictly by the 8 documents in authority order.
   - **Actual Implementation State:** Governed by Git commit tree, source in `app/`, tests in `tests/`, and merged PRs, which supersede stale task-ledger prose in `TASKS.md`.
3. **No Stealth Refactoring:** Existing PH-000 through PH-040 code must not be refactored during cookbook generation unless an unavoidable blocker is uncovered.

---

## 3. Baselines

- **Cookbook Work Base SHA:** `d367261e617fb96ca2d353871590c0dc616b8fe0`
- **Product Code Base SHA:** `ef00714c86d3d7b5684d693da35aa82595a088d4`
- **CI Run Baseline:** `37107781413`

---

## 4. Comprehensive Authority Coverage (193 Sections)

All 193 specification sections from the authority documents are indexed and audited in `Docs/ImplementationCookbook/machine/authority_coverage.json`:

- **`DOCS.md` (29 sections):** Vision, UX paradigms, hardware tiers, subsystem boundaries, resident memory budget (300MB), offline capabilities, audio pipeline, browser automation, developer workflows, licensing.
- **`SECURITY.md` (18 sections):** Threat model, prompt injection defense, policy engine, approval broker, hash binding, executor isolation, native messaging bridge security, dashboard CORS/CSRF boundaries, audit logging.
- **`ARCHITECTURE.md` (22 sections):** Component hierarchy, composition root, state transitions, async concurrency, queue limits, IPC protocols, extension bridge.
- **`CONFIG.md` (9 sections):** TOML schema, environment variables, validation rules, sensible defaults, configuration reload semantics.
- **`UI.md` (56 sections):** All 10 views (Home, Chat, Tasks/Agents, Browser, Voice, Actions, Permissions, Files/Workspaces, Developer, Settings), top bar, sidebar, composer, SVG AI Core state animations, responsive breakpoints, reduced motion, a11y keyboard focus, SSE contracts.
- **`PLAN.md` (23 sections):** Milestone progression (PH000–PH180), acceptance criteria per phase, dependencies, verification suites.
- **`TASKS.md` (21 sections):** Implementation task progression, phase scope boundaries, and historical checkpoint tracking.
- **`EXECUTION.md` (15 sections):** Micro-order requirements, gate criteria, testing rigor, checkpoint protocols.

Every normative requirement derived from these 193 sections is tracked with zero gaps.

---

## 5. Conflict & Gap Ledger

| Conflict ID | Higher Authority | Lower Source / State | Conflict Description | Ruling & Decision | Affected Phases | Required Action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `CONF-001` | `Git Tree` | `Docs/TASKS.md` | `TASKS.md` checkpoint prose may state PR #3 is pending review/merge, whereas Git `main` has merged `ef00714` with CI pass. | Git repository truth wins for implementation state. PH-040 is fully merged and verified. | All (PH-050..180) | Anchor all phase packets starting from PH-050 onwards; do not replay PH-040. |
| `CONF-002` | `Docs/DOCS.md` | Casual STT proposals | Some ecosystem notes suggest Vosk for local offline STT. | `DOCS.md` Section 3.4 explicitly forbids Vosk as default resident STT due to ~300MB RAM requirement. Remote STT (NVIDIA Parakeet) is used after wake only. | PH-080, PH-090 | Freeze architecture to remote STT post-wake only. |
| `CONF-003` | `Docs/UI.md` / `DOCS.md` | Web frameworks | Common web practice uses React/Vue/Node. | `UI.md` and `DOCS.md` strictly forbid Node/React/Vue runtimes. Static HTML, local Bootstrap 5.3 CSS, vanilla JS, SVG AI Core served via FastAPI localhost. | PH-130, PH-140 | Enforce zero-Node frontend architecture in contracts and tests. |
| `CONF-004` | `Docs/SECURITY.md` | Shell execution | Subprocess execution could tempt `shell=True` for convenience. | `SECURITY.md` strictly forbids `shell=True`. All executions must use `asyncio.create_subprocess_exec` with explicit argv lists. | PH-040, PH-050, PH-150 | Enforce argv execution across all executors. |
| `CONF-005` | `Docs/SECURITY.md` | UI location of approval | Approval requests could tempt web dashboard modal. | `SECURITY.md` Section 5 and `DOCS.md` Section 1 require an independent native approval popup that functions even if dashboard is closed. | PH-050 | Build independent transient popup protocol and broker. |
| `CONF-006` | `Docs/DOCS.md` | Cgroup limits | Memory limits could tempt loosening during development. | `MemoryHigh=240M`, `MemoryMax=300M` are hard invariants. Silent limit increases are forbidden. | PH-160, PH-170 | Design strict bounds, bounded queues, and memory monitoring. |
| `CONF-007` | `Docs/SECURITY.md` | `ProcessExecutor` contract | PH040 ProcessExecutor requires `PolicyEvaluation(decision=ALLOW_PREAPPROVED)` context, blocking human-approved actions. | Do not fake human approval as `ALLOW_PREAPPROVED`. Introduce typed `ExecutionAuthorization` supporting both `PREAPPROVED` and `HUMAN_ALLOW_ONCE` with explicit `ProcessExecutionConstraints`. | PH-040, PH-050 | Extend executor context in PH050 to accept `ExecutionAuthorization`. |
| `CONF-008` | `Docs/SECURITY.md` | Pre-wake audio buffer | Prepending 500ms of pre-wake ring buffer to command audio risks transmitting ambient room audio. | Pre-wake ring buffer data is wake-detector-only and must NEVER enter remote STT payload. Post-wake audio begins strictly after wake boundary. | PH-080, PH-090 | Remove pre-wake audio prepend; enforce strict post-wake provenance via `CommandAudioSegment`. |
| `CONF-009` | `Docs/ARCHITECTURE.md`| Lifecycle composition | PH100 tray previously called a `LifecycleManager` scheduled for creation in PH160. | `app/lifecycle.py` must be created in an earlier integration phase (PH050) as foundation, then hardened with cgroup controls in PH160. Tray receives injected shutdown callback. | PH-050, PH-100, PH-160 | Create `app/lifecycle.py` in PH050. |
| `CONF-010` | `Docs/CONFIG.md` / NVIDIA | STT endpoint protocol | Casual proposals assume OpenAI-compatible `/v1/audio/transcriptions` for Parakeet ASR. | `STTConfig.model` (`nvidia/parakeet-1_1b-rnnt-multilingual-asr`) is an NVIDIA Riva model using Riva gRPC service (`grpc.nvcf.nvidia.com:443`) or local Riva NIM container (port 9000). | PH-090 | Freeze authoritative Riva gRPC / NIM protocol for STTAdapter. |
