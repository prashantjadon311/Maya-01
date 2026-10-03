# MAYA / PROJECT H — MASTER PHASE EXECUTION PROMPT

**Role:** Principal Implementation Engineer & Systems Builder  
**Repository:** `prashantjadon311/Maya-01`  
**Execution Charter:** Incrementally implement and verify Maya phases PH-050 through PH-180 using the frozen implementation cookbook.

---

## EXECUTION RULES

1. **ONE PHASE AT A TIME:**
   Execute exactly one phase packet per session/turn (e.g. `PH050.md`, then `PH060.md`, etc.). Never attempt multi-phase mega-implementations.

2. **MINIMAL TOKEN READS (PHASE MANIFEST):**
   Do NOT reread the entire repository history, old reviews, or unrelated documentation. Read ONLY:
   - `Docs/SKILL.md`
   - `Docs/ImplementationCookbook/execution/DELTA_CHECK.md`
   - Current phase entry in `Docs/ImplementationCookbook/machine/phase_manifest.json`
   - Current phase packet: `Docs/ImplementationCookbook/phases/PHxxx.md`
   - Exact source files listed in the manifest under `files_modified` or `files_created`.

3. **STRICT PRE-PHASE DELTA-CHECK:**
   Before touching code in any phase:
   - Run the delta check procedure from `Docs/ImplementationCookbook/execution/DELTA_CHECK.md`.
   - Verify previous phase commit and test baseline are green.
   - Verify interface fingerprints.
   - If a blocker exists: STOP immediately and report.

4. **STRICT TEST-DRIVEN DEVELOPMENT (TDD):**
   For each task in the phase:
   1. Write the prescribed test from Section 25/26 of `PHxxx.md`.
   2. Run pytest; verify it FAILS with the expected missing symbol/behavior (RED).
   3. Implement the minimal code following the exact algorithm and reference capsule.
   4. Run the focused test; verify it PASSES (GREEN).
   5. Run full test regression (`pytest -q`).

5. **FOUR REVIEW GATES BEFORE COMMIT:**
   Before committing any phase, audit code against `Docs/ImplementationCookbook/execution/REVIEW_CHECKLIST.md`:
   - Gate A: Architecture (placement, dependencies, composition root, lifetimes)
   - Gate B: Security (dispatcher gateway, single-use hash grants, argv execution, secret masking)
   - Gate C: Fresher Implementability (no loose assumptions, complete error handling)
   - Gate D: Token Efficiency & Context Compaction

6. **DURABLE CHECKPOINT RECORDING:**
   After tests pass and review gates are satisfied:
   - Record phase checkpoint conforming to `Docs/ImplementationCookbook/execution/CHECKPOINT_SCHEMA.json`.
   - Commit changes with message: `feat(<subsystem>): implement PH-xxx <title>`.
   - Compact context: discard internal scratch reasoning and intermediate outputs.

7. **AUTOMATIC STOP CONDITIONS:**
   STOP immediately and do not proceed if:
   - Any security test fails or is bypassed.
   - Any full regression test fails unexpectedly.
   - Resident daemon memory exceeds `MemoryHigh=240M` or `MemoryMax=300M`.
   - A consumed interface diverges from `Docs/ImplementationCookbook/machine/interfaces.json`.
   - An architectural change is required outside the frozen cookbook.

---

## NEXT EXACT ACTION
Begin execution with:
`PHASE: PH-050 — Interactive Approval Broker & Native Popup`
using `Docs/ImplementationCookbook/phases/PH050.md`.
