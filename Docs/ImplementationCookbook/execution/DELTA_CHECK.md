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

# Step 3: Run repository interface fingerprint check
python -m tools.cookbook.fingerprint Docs/ImplementationCookbook/machine/interfaces.json

# Step 4: Run focused regression on previously completed phase
pytest tests/ -q
```

---

## 2. Decision Tree

1. **Clean Baseline:**
   - If working tree is clean, test suite passes, and consumed interfaces match fingerprints:
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
