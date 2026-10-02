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

