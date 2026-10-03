# Maya Phase Implementation Delta-Check Procedure

Before starting the implementation of any phase (e.g. `PH050` through `PH180`), the implementing engineer (or subagent) MUST execute this exact delta-check procedure.

---

## 1. Delta-Check Steps

```bash
# Step 1: Verify current branch and base commit
git rev-parse HEAD
git status --short

# Step 2: Compare against expected previous phase commit SHA
# (Check latest entry in .superpowers/sdd/... or phase checkpoint ledger)

# Step 3: Run repository interface fingerprint check against canonical authority
python -m tools.cookbook.fingerprint Docs/ImplementationCookbook/machine/interfaces.json --expect 47cffee38d4c114ba9d503046e73e81d3f3fde34d9c9eab4dd34856db7d50bca
python -m tools.cookbook.fingerprint Docs/ImplementationCookbook/machine/requirements.json --expect 486727cb5949ae2a4c8bac1f581dd97604bc467390a26e7ae48a2a8bd406203c
python -m tools.cookbook.fingerprint Docs/ImplementationCookbook/machine/phase_manifest.json --expect d89006d8feb6d05072a25a2ca076ef930921a2d4bd667d25da4012e6d7d1451a

# Step 4: Run AST source interface verification against live code
python -m tools.cookbook.verify_source_interfaces Docs/ImplementationCookbook/machine/source_interfaces.json

# Step 5: Run cookbook integrity validation
PYTHONPATH=. python -m tools.cookbook.validate Docs/ImplementationCookbook

# Step 6: Run focused regression on previously completed phase
pytest tests/ -q
```

---

## 2. Decision Tree

1. **Clean Baseline:**
   - If working tree is clean, test suite passes, and consumed interfaces match authority fingerprints:
   - **PROCEED** to phase implementation micro-order.

2. **Interface Drift / Incompatibility:**
   - If a consumed interface signature or return type has changed unexpectedly:
   - **DO NOT** attempt to redesign the architecture or hack adjacent files.
   - Record `INTERFACE_MISMATCH_BLOCKER` with exact signature difference.
   - **STOP** and request architectural ruling.

3. **Production Bug Discovered:**
   - If an existing production code bug in `app/` blocks progress:
   - Record `CURRENT_CODE_DEFECT-xxx` with file, symbol, impact, and required repair phase.
   - **DO NOT** fix the bug out of band in the current phase.
