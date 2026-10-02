# Repository recovery implementation plan

**Goal:** Repair the existing foundation, verify remote CI, then implement PH-030 only.
**Spec:** User recovery prompt (2026-10-03), Docs/DOCS.md through Docs/EXECUTION.md in authority order.
**Architecture:** Preserve existing Pydantic models and pure policy interfaces. Add deterministic registry resolution with transactional snapshots after the foundation gate.
**Execution:** Inline TDD with an independent reviewer at each phase; direct main commits/pushes as explicitly requested.

## Constraints

- Python >=3.11; CI 3.11 and 3.14. Only Pydantic as runtime dependency.
- No PH-040 execution, provider, approval UI, branch, PR or history rewriting.
- Stop at any red CI boundary; never infer green CI from local tests.
- Pre-wake privacy and 300 MiB product ceiling remain unchanged and unclaimed.

## Phase A

- [ ] Reproduce clean install failure; restrict discovery to app packages; add package markers. Upgrade only checkout/setup-python and add Python matrix. Install and check imports from /tmp with isolated Python.
- [ ] Add failing config/state/action schema regression tests, then minimally fix the declared constraints. Run targeted module and full suite after each defect.
- [ ] Add trusted RiskLevel and assess_risk; require explicit approval risk. Cover raised hints, blocked executable basenames, strict preapproval contracts, real cwd containment, malformed file paths, hash and metadata binding from valid baselines.
- [ ] Clean policy tests after coverage; remove obsolete tracked scripts; repair README/env/config examples and historical handoff drift.
- [ ] Review diff independently, verify install/imports/tests/RSS/hygiene; commit/push main, wait for successful remote CI. Record gate evidence.

## Phase B (gated; no implementation before green Phase A CI)

- [ ] Tests first for ActionRegistry(directory), reload(), resolve(text), get_definition(id), RegistryMatch and explicit ambiguity. Compile NFKC/whitespace/casefold templates with safe slots and escaped literals.
- [ ] Validate global IDs, placeholder references and composite steps/cycles. Bound each file to 1 MiB; transactional candidate validation; retain prior pack on malformed file and preserve whole snapshot on relationship failure.
- [ ] Verify disabled actions, collisions, malformed initial files, oversized packs, reload atomicity and isolation from subprocess/network/AI/policy.
- [ ] Review independently; record exact tests, install/import checks, RSS delta and deferred PH-040 trust boundary. Commit/push main and verify remote CI.
- [ ] Update checkpoint to PH-040 only after green CI; stop.

## Review focus

Symlink followed by `..`; malformed cwd with privileged commands; valid-baseline approval mutations; snapshot/definition mutability; same-action overlapping slot templates; bounded parsing and regex work.
