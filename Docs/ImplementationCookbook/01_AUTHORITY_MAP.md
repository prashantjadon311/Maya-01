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

1. **Higher Authority Wins:** A lower document cannot relax, circumvent, or contradict a rule from a higher document. For example, if `PLAN.md` suggests an open endpoint or loose check, but `SECURITY.md` demands strict approval or origin validation, `SECURITY.md` strictly governs.
2. **Behavioral Authority vs Implementation State:**
   - **Behavioral Authority:** What the system *must* do is dictated strictly by the authority order above.
   - **Actual Implementation State:** What *currently exists* in code is determined by Git tree, source code in `app/`, automated tests in `tests/`, and merged pull requests, superseding stale task-ledger prose in `TASKS.md`.
3. **No Stealth Refactoring:** The existing PH-000 through PH-040 code must not be refactored during cookbook generation unless an unavoidable blocker is uncovered and recorded.

---

## 3. Baselines

- **Cookbook Generation Work Base:** `d603173624ddc9285b32ee00f33c10be2ecc9b58`
- **Product Code Base (PH-000 to PH-040):** `ef00714c86d3d7b5684d693da35aa82595a088d4`
- **CI Run Baseline:** `37107781413`
