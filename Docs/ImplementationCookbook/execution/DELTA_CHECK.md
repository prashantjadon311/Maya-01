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
python -m tools.cookbook.fingerprint Docs/ImplementationCookbook/machine/interfaces.json --expect d5b9c4168389560357308b1d5b42fac213138fe279b11397f65c887b5d054da9
python -m tools.cookbook.fingerprint Docs/ImplementationCookbook/machine/requirements.json --expect 34514838096946b92258061d314c54ac285d9079f3de13886c2579bc40a157de
python -m tools.cookbook.fingerprint Docs/ImplementationCookbook/machine/phase_manifest.json --expect e496f3b7ead4c1bd679664bce10e09e54d7d68f435188a556be6f03c7cd65747

# Step 4: Run cookbook integrity validation
PYTHONPATH=. python -m tools.cookbook.validate Docs/ImplementationCookbook

# Step 5: Run focused regression on previously completed phase
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
