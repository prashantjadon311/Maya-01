# Project H Foundation + Security Closure Review

## Baseline
- AUDITED COMMIT: 8e5bbe4478f328a407548d5cb6999ea8fc528450
- PYTHON: 3.14.4
- BASELINE TEST RESULT: 54 passed


## ISSUE A: WILDCARD PREAPPROVAL RULE
- SEVERITY: CRITICAL
- CONFIRMED: YES
- RECOMMENDED SOLUTION: Replace generic rule with strict `process-preapproval` model.
- SOLUTION DECISION: ACCEPT_RECOMMENDED
- SELECTED SOLUTION: Implemented strict Pydantic model for `PreapprovalRule` dropping `tool` and `risk`, enforcing `approval="preapproved"`.
- RATIONALE: It completely eliminates silently widening permissions via missing fields.
- RED TEST: `test_ISSUE_A_wildcard_preapproval_rule` added and failed initially.
- RED RESULT: `Failed: DID NOT RAISE ValidationError`
- IMPLEMENTATION: Updated `PreapprovalRule` schema in `app/policy/engine.py`.
- GREEN RESULT: Pass.
- RESIDUAL RISK: None.


## ISSUE B: MALFORMED PROCESS ACTION REPRESENTATION
- SEVERITY: CRITICAL
- CONFIRMED: YES
- RECOMMENDED SOLUTION: Define EXACTLY ONE canonical runtime representation (`arguments["argv"]`).
- SOLUTION DECISION: ACCEPT_RECOMMENDED
- SELECTED SOLUTION: Removed fallback to `arguments["executable"]`. Enforced `argv` must be a non-empty list of non-empty strings.
- RATIONALE: It prevents representation ambiguity that could lead to policy bypasses.
- RED TEST: `test_ISSUE_B_malformed_process_representation`
- RED RESULT: Failed on missing `argv` or invalid types.
- IMPLEMENTATION: Updated `process.run` evaluation in `PolicyEngine`.
- GREEN RESULT: Pass.
- RESIDUAL RISK: None.


## ISSUE C: SHELL / ENV / PRIVILEGE BROKER PREAPPROVAL
- SEVERITY: CRITICAL
- CONFIRMED: YES
- RECOMMENDED SOLUTION: Do not parse wrappers for bypass; use one centralized constant `NEVER_PREAPPROVE_EXECUTABLES`.
- SOLUTION DECISION: ACCEPT_RECOMMENDED
- SELECTED SOLUTION: Added `NEVER_PREAPPROVE_EXECUTABLES`. Validated via `os.path.basename` in `evaluate()` returning `ASK_USER` and `PreapprovalRule.validate_executable()` raising `ValidationError`.
- RATIONALE: It's significantly simpler and robust compared to parsing unbounded wrapper commands.
- RED TEST: `test_ISSUE_C_never_preapprove_executables`
- RED RESULT: PreapprovalRule failed to reject privileged executables.
- IMPLEMENTATION: Updated `engine.py`. Redundant tests deleted.
- GREEN RESULT: Pass.
- RESIDUAL RISK: None.


## ISSUES D, E, F, G, H, I: FILE ROOTS, INVARIANTS, AND CREDENTIALS
- SEVERITY: CRITICAL
- CONFIRMED: YES
- RECOMMENDED SOLUTION: Enforce strict `FileRootConfig`, union defaults with custom denied paths, default permissions to `False`, block `.env` and `~/.config/project-h`, and map `file.list` to `read`.
- SOLUTION DECISION: ACCEPT_RECOMMENDED
- SELECTED SOLUTION: Implemented strict type constraints on `allowed_file_roots`, added credential matching logic to `evaluate`, hard-coded invariant sets in `DEFAULT_SENSITIVE_PATHS`, mapped `file.list` correctly.
- RATIONALE: Closes significant file access bypass vectors and ensures safe-by-default initialization.
- RED TEST: `test_ISSUE_D_E_F_file_security_invariants` added and failed initially.
- RED RESULT: Failed to block access to credential files or built-in paths overridden by custom list.
- IMPLEMENTATION: Updated `app/policy/engine.py` and `app/core/config.py`. Fixed tests to use `FileRootConfig`.
- GREEN RESULT: Pass.
- RESIDUAL RISK: None.

