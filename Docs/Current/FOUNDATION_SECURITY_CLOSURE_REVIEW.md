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


## ISSUE J: APPSTATE STATUS MUTABILITY
- SEVERITY: IMPORTANT
- CONFIRMED: YES
- RECOMMENDED SOLUTION: Use `Literal` for status and set default to `"DISABLED"`. Enable `validate_assignment=True`.
- SOLUTION DECISION: ACCEPT_RECOMMENDED
- SELECTED SOLUTION: Implemented strict Literal assignment in `AppState`.
- RATIONALE: It ensures that no unknown state can be introduced via runtime updates, preventing invalid UI transitions.
- RED TEST: `test_ISSUE_J_app_state_mutability` added.
- RED RESULT: `AppState` status allowed `"THINKING"` or random string. Default was `"READY"`.
- IMPLEMENTATION: Updated `app/core/state.py` and `tests/test_schemas.py`.
- GREEN RESULT: Pass.
- RESIDUAL RISK: None.


## ISSUE K: MISSING SEMANTIC SECURITY ON CONFIG MODELS
- SEVERITY: IMPORTANT
- CONFIRMED: YES
- RECOMMENDED SOLUTION: Use strict Pydantic bounds for memory, ports, timeouts, etc.
- SOLUTION DECISION: ACCEPT_RECOMMENDED
- SELECTED SOLUTION: Added strict `ge` and `le` bounds on `DashboardConfig`, `ResourcesConfig`, and `BrowserDomainConfig`. Hardcoded semantic Literal capabilities for the browser.
- RATIONALE: Fails config parsing completely instead of allowing runtime bounds failures or malicious limits (like `memory_max_mb=-10` or `port=99999`).
- RED TEST: `test_ISSUE_K_config_model_constraints` added.
- RED RESULT: Configuration successfully parsed invalid logical values.
- IMPLEMENTATION: Updated `app/core/config.py`.
- GREEN RESULT: Pass.
- RESIDUAL RISK: None.


## ISSUE L: CANONICAL JSON TYPES FOR ACTION ARGUMENTS
- SEVERITY: IMPORTANT
- CONFIRMED: YES
- RECOMMENDED SOLUTION: Enforce strictly recursive canonical JSON types. Ensure `float` is not NaN or Infinity.
- SOLUTION DECISION: ACCEPT_RECOMMENDED
- SELECTED SOLUTION: Added `validate_canonical_json` recursion in `app/actions/schema.py` triggered by `ActionRequest`'s `@model_validator`. Rejected `NaN` and `Infinity`, and ensured dict keys are strings. 
- RATIONALE: It prevents bypasses of policy hashing that relies on `json.dumps` by ensuring only structurally pure JSON is loaded.
- RED TEST: `test_ISSUE_L_canonical_json_types` added.
- RED RESULT: Configuration successfully parsed `bytes`, `NaN`, and `Infinity` into arguments.
- IMPLEMENTATION: Updated `app/actions/schema.py`.
- GREEN RESULT: Pass.
- RESIDUAL RISK: None.


## ISSUE M: ACTION DEFINITION/PACK SCHEMA WEAKNESS
- SEVERITY: IMPORTANT
- CONFIRMED: YES
- RECOMMENDED SOLUTION: Enforce strict constraints on pack schema version, ID patterns, and timeouts.
- SOLUTION DECISION: ACCEPT_RECOMMENDED
- SELECTED SOLUTION: `schema_version: Literal[1]`, regex pattern for IDs, `timeout_seconds` > 0.
- RATIONALE: It prevents future parsing ambiguity and ensures actions can never hang indefinitely due to negative/zero timeouts.
- RED TEST: `test_ISSUE_M_action_pack_weaknesses` added.
- RED RESULT: Configuration successfully parsed invalid IDs and 0 timeout.
- IMPLEMENTATION: Updated `app/actions/schema.py`.
- GREEN RESULT: Pass.
- RESIDUAL RISK: None.


## ISSUE N: APPROVAL_REQUEST TEST WEAKNESS
- SEVERITY: IMPORTANT
- CONFIRMED: YES
- RECOMMENDED SOLUTION: Use a valid baseline helper to avoid false-positive test passes.
- SOLUTION DECISION: ACCEPT_RECOMMENDED
- SELECTED SOLUTION: Re-wrote `test_approval_request_digest_validation` to build fully valid kwargs first, then mutate exactly the target field.
- RATIONALE: False positive security tests provide dangerous false confidence.
- RED TEST: Re-written test failed initially because `action_snapshot` was entirely missing in the original test!
- RED RESULT: `ValidationError` for missing `action_snapshot`, rather than invalid hash format.
- IMPLEMENTATION: Updated `tests/test_policy.py`.
- GREEN RESULT: Pass.
- RESIDUAL RISK: None.

