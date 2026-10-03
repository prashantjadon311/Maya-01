# MAYA / PROJECT H — MASTER PHASE EXECUTION PROMPT

**Role:** Principal Implementation Engineer & Systems Builder  
**Repository:** `prashantjadon311/Maya-01`  
**Execution Charter:** Incrementally implement and verify Maya phases PH-050 through PH-180 in an autonomous, sequential one-shot loop using the frozen implementation cookbook.

---

## EXECUTION LOOP (AUTONOMOUS ONE-SHOT)

You must execute a continuous internal execution loop iterating through phases **PH-050 → PH-060 → PH-070 → PH-080 → PH-090 → PH-100 → PH-110 → PH-120 → PH-130 → PH-140 → PH-150 → PH-160 → PH-170 → PH-180**.

### Pre-requisites & Implementation Safety:
1. **Dedicated Branch:** Create and check out `maya-v1-implementation` branch from exact merged frozen `main`. **NEVER implement directly on main.**
2. **Cookbook Immutability:** `Docs/ImplementationCookbook/**` is strictly read-only during phase implementation. Any discovery of a cookbook defect or missing specification must immediately trigger a hard stop with error code `COOKBOOK_DEFECT_BLOCKER`.
3. **Continuous Progression:** Do NOT stop or ask for user confirmation between successful phases. Once a phase passes all tests, review gates, and checkpoint requirements, immediately and automatically continue to the next phase in the loop.

For each phase `PHxxx`:

1. **MINIMAL TOKEN READS (PHASE ISOLATION):**
   Load only the minimal phase-local context:
   - `Docs/SKILL.md`
   - Phase `required_reads` declared in `Docs/ImplementationCookbook/machine/phase_manifest.json`
   - Relevant interfaces and resource bounds in `Docs/ImplementationCookbook/machine/`
   - Current phase packet: `Docs/ImplementationCookbook/phases/PHxxx.md`
   - Prior phase checkpoint from `.planning/` or checkpoint ledger
   - The exact source files declared in `files_created` or `files_modified`.

2. **PRE-PHASE DELTA-CHECK:**
   Execute the verification steps from `Docs/ImplementationCookbook/execution/DELTA_CHECK.md`:
   - Verify working tree is clean: `git status --short`.
   - Verify canonical interface and manifest fingerprints: `python -m tools.cookbook.fingerprint ... --expect <hash>`.
   - Verify AST source interfaces: `python -m tools.cookbook.verify_source_interfaces Docs/ImplementationCookbook/machine/source_interfaces.json`.
   - Verify cookbook integrity: `PYTHONPATH=. python -m tools.cookbook.validate Docs/ImplementationCookbook`.
   - Verify preceding test baseline is green.

3. **STRICT TEST-DRIVEN DEVELOPMENT (TDD):**
   For each task prescribed in `phases/PHxxx.md`:
   - Write the targeted test in `tests/test_*.py`.
   - Run `pytest` to confirm the test fails with the expected missing symbol or behavioral assertion (RED).
   - Implement the minimal production code adhering strictly to the architecture, types, and reference capsules.
   - Run the targeted test to confirm it passes cleanly (GREEN).

4. **TARGETED TESTS & PYTEST EXECUTION:**
   Run all phase-specific tests declared in `tests.json` / `phase_manifest.json` for `PHxxx`.

5. **MANDATORY FULL REGRESSION:**
   Execute full test suite regression:
   `PYTHONPATH=. pytest tests/ -v`
   All preceding and new tests must pass (100% green).

6. **FOUR-GATE PRE-COMMIT REVIEW:**
   Audit all changes against `Docs/ImplementationCookbook/execution/REVIEW_CHECKLIST.md`:
   - **Gate A (Architecture):** Exact file ownership, lifecycle order, no cyclic dependencies, no unauthorized imports.
   - **Gate B (Security):** Central dispatcher enforcement, single-use atomic grant consumption, no shell execution, secret masking in audit logs.
   - **Gate C (Fresher Implementability):** Explicit error handling, fail-closed timeouts, resource bounding.
   - **Gate D (Token & Memory):** Clean code, no dangling debug code, memory bounds respected.

7. **ATOMIC GIT COMMIT:**
   - Verify changed files strictly match `files_created` and `files_modified` in `phase_manifest.json`.
   - Run `git diff --check` to ensure no whitespace errors or merge conflict markers.
   - Stage modified and created files for the phase:
   `git commit -m "feat(<subsystem>): implement PH-xxx <title>"`

8. **DURABLE CHECKPOINT CREATION:**
   Record a valid checkpoint file matching `Docs/ImplementationCookbook/execution/CHECKPOINT_SCHEMA.json`:
   - Record `memory_status` (`MEASURED` for PH160/PH180 and phases where measured; otherwise `NOT_MEASURED`).
   - Record `memory_rss_mb` and `memory_measurement_method` (or `null` if unmeasured).
   - Document any discoveries or edge-case handling in `findings`.

9. **CONTEXT COMPACTION:**
   Purge intermediate scratch artifacts, discard ephemeral tool outputs, and summarize phase completion in a single compact status line.

10. **AUTOMATIC PROGRESSION:**
    **Proceed immediately to the next phase without waiting for user input.**

---

## HARD STOP CONDITIONS

HALT the execution loop and alert the user ONLY if one of the following unrecoverable blockers occurs:
1. A security assertion or adversarial test fails or cannot pass without bypassing policy.
2. An unexpected full regression failure in existing code that cannot be resolved within phase ownership rules.
3. Consumed interfaces diverge from canonical authority hashes in `Docs/ImplementationCookbook/machine/authority.json`.
4. A circular dependency or unowned file modification is required.
5. Resident daemon memory exceeds `MemoryMax=300M` during measured phases.
6. External network/API failure on required live CI validation.

---

## EXECUTION START
Begin the autonomous loop starting at:
`PHASE: PH-050 — Interactive Approval Broker & Native Popup`
using `Docs/ImplementationCookbook/phases/PH050.md`.
