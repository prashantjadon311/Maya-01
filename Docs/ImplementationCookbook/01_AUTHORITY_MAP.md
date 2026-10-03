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

- **Cookbook Work Base SHA:** `d603173624ddc9285b32ee00f33c10be2ecc9b58`
- **Product Code Base SHA:** `ef00714c86d3d7b5684d693da35aa82595a088d4`
- **CI Run Baseline:** `37107781413`

---

## 4. Conflict & Gap Ledger

| Conflict ID | Higher Authority | Lower Source / State | Conflict Description | Ruling & Decision | Affected Phases | Required Action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `CONF-001` | `Git Tree` | `Docs/TASKS.md` | `TASKS.md` checkpoint prose may state PR #3 is pending review/merge, whereas Git `main` has merged `ef00714` with CI pass. | Git repository truth wins for implementation state. PH-040 is fully merged and verified. | All (PH-050..180) | Anchor all phase packets starting from PH-050 onwards; do not replay PH-040. |
| `CONF-002` | `Docs/DOCS.md` | Casual STT proposals | Some ecosystem notes suggest Vosk for local offline STT. | `DOCS.md` Section 3.4 explicitly forbids Vosk as default resident STT due to ~300MB RAM requirement. Remote STT (NVIDIA Parakeet) is used after wake only. | PH-080, PH-090 | Freeze architecture to remote STT post-wake only. |
| `CONF-003` | `Docs/UI.md` / `DOCS.md` | Web frameworks | Common web practice uses React/Vue/Node. | `UI.md` and `DOCS.md` strictly forbid Node/React/Vue runtimes. Static HTML, local Bootstrap 5.3 CSS, vanilla JS, SVG AI Core served via FastAPI localhost. | PH-130, PH-140 | Enforce zero-Node frontend architecture in contracts and tests. |
| `CONF-004` | `Docs/SECURITY.md` | Shell execution | Subprocess execution could tempt `shell=True` for convenience. | `SECURITY.md` strictly forbids `shell=True`. All executions must use `asyncio.create_subprocess_exec` with explicit argv lists. | PH-040, PH-050, PH-150 | Enforce argv execution across all executors. |
| `CONF-005` | `Docs/SECURITY.md` | UI location of approval | Approval requests could tempt web dashboard modal. | `SECURITY.md` Section 5 and `DOCS.md` Section 1 require an independent native approval popup that functions even if dashboard is closed. | PH-050 | Build independent transient popup protocol and broker. |
| `CONF-006` | `Docs/DOCS.md` | Cgroup limits | Memory limits could tempt loosening during development. | `MemoryHigh=240M`, `MemoryMax=300M` are hard invariants. Silent limit increases are forbidden. | PH-160, PH-170 | Design strict bounds, bounded queues, and memory monitoring. |
