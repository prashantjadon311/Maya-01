# Gemini 3.1 Pro High Security Review
## Batch 2 (PH-020: Policy Engine)

### 1. Scope
Targeted security review and contract validation for Batch 2 (Policy Engine).
The focus areas evaluated:
- A. Preapproval Rule Validation
- B. Trusted Risk Classification
- C. Sudo / Privilege Bypass Forms
- D. Path Normalization
- E. Working Directory Preapproval
- F. File Root Operation Permissions
- G. Approval Display/Hash Binding
- H. Hash Verification
- I. Timestamp Validation
- J. Action Argument Canonicalization
- K. Security Defaults

### 2. Findings & Exploits (Before Fix)
During the adversarial testing, the following vulnerabilities and incomplete contract implementations were found:
*   **B & C - Privilege Escalation Bypass:** `apt`, `systemctl`, `pkexec`, `env sudo` could bypass the prompt if an admin incorrectly configured them in `preapproved_rules`. The `engine.py` lacked a robust containment invariant against elevated process environments.
*   **A - Malformed Preapproval Rules:** `PreapprovalRule` typing was missing, allowing malformed dictionary objects to pass silently through initialization.
*   **D & E - Path Traversals:** `..` traversal sequences in `path` or `cwd` could escape the `allowed_file_roots` or `working_roots` lexically if not `os.path.normpath`'d.
*   **F - Missing File Operations Booleans:** The `FileRootConfig.read / write / delete` booleans were ignored by the engine, which blindly allowed all sub-operations if a path was in the root.
*   **G - Approval Binding:** `ApprovalRequest.from_action` factory was missing; requiring manual creation of the approval requests.
*   **H - Digest Constant-Time Comparison:** The engine compared digests using `==`, vulnerable to timing attacks.
*   **I & J - NaN/Infinity Injection:** Non-finite floats like `NaN` and `Infinity` could be submitted in JSON payloads to corrupt timestamp expiration (`expires_at`) or break canonical serialization.

### 3. Tests Added
We added 11 RED failing tests corresponding to Focus Areas A-K in `tests/test_policy.py`. 
These tests adversarially checked:
*   ImportError for `PreapprovalRule`.
*   Assertion failures on bypass actions (`pkexec`, `apt`, `su`).
*   Assertion failures for `..` traversals.
*   Exceptions on NaN/inf ingestion into timestamps and JSON.
*   Missing `from_action` factory.

### 4. Fixes Applied
*   **Strict Models:** Introduced `PreapprovalRule` in `engine.py` with strict Pydantic extra-forbid.
*   **Privileged Escalation Guard:** Hardcoded a `privileged` invariant containing `sudo`, `su`, `doas`, `pkexec`, `apt`, `systemctl`, `dpkg`, `dnf`, `yum`. Bound it to both standalone execution and `env`-wrapped execution to always force `ASK_USER`.
*   **Path Normalization:** Enforced `os.path.normpath` on all target paths, working roots, and allowed roots prior to containment checks.
*   **Boolean Enforcement:** Evaluated `.read`, `.write`, `.delete` directly from `FileRootConfig`.
*   **Hash Operations:** Moved to `hmac.compare_digest` for constant-time comparison in `verify_action`. Added `from_action` factory to automatically bundle requests.
*   **Canonical Safety:** Configured `allow_nan=False` in `ActionRequest.to_canonical_json` and added finite math validators in `ApprovalRequest`.

### 5. Go/No-Go Decision
**Decision:** GO for PH-030 (Batch 3)
**Rationale:** All 11 targeted security flaws were explicitly tested (RED) and mitigated (GREEN). The full test suite of 47 tests is now passing.

The repository is secure enough to proceed to the Action Registry and Executor boundaries.

## Second-Pass Findings

During a second-pass adversarial review, several critical configuration bypasses and missing validation steps were identified and repaired.

*   **Defect A (Approval Field Enforcement):** (Important) Preapproval rules with `approval="ask_user"` or `"deny"` were incorrectly allowing preapproval because the engine did not respect the `approval` string. *Fix:* Updated engine to strictly map rule approval to PolicyDecision outcomes.
*   **Defect B (Broad Rules):** (Important) Missing constraints in `process.run` could silently grant wildcard execution authority. *Fix:* Implemented a strict contract in `PreapprovalRule` requiring `executable` and `argv_prefix` whenever `approval="preapproved"` is requested.
*   **Defect C & D (Privileged Bypass & Env Wrapper):** (Critical) Although basic privilege escalation (e.g. `sudo`) was guarded, absolute paths (`/usr/bin/sudo`, `/usr/bin/pkexec`) and `env` wrappers with flags (`env -i sudo`) were not properly identified. *Fix:* Enforced robust `os.path.basename` inspection over executables and safe deterministic traversal of `env` invocations.
*   **Defect E & Canonical Binding (Approval Metadata Bind):** (Critical) `ApprovalRequest` permitted arbitrary, independently supplied metadata (`action_id`, `tool`, `reason`, etc.) to accompany a valid `action_hash`. A malicious constructor could display benign text while authorizing a destructive action. *Fix:* Redesigned `ApprovalRequest` to store the raw canonical `action_snapshot` and intrinsically validate every single duplicate metadata field (like `action_id`) against the parsed snapshot.
*   **Defect F & G (Strict Types & Malformed rules):** (Important) `PreapprovalRule` allowed arbitrary strings for risk and approval, and the engine silently caught initialization exceptions. *Fix:* Upgraded to strict Pydantic literals and forced fail-closed `ValidationError`s to crash initialization rather than swallowing configuration issues.
*   **Defect H (Raw File Roots):** (Important) Raw string paths passed to `allowed_file_roots` were silently granting excessive permissions in tests. *Fix:* Constrained raw string compatibility to purely `file.read` operations.

**Second-Pass Outcome:** 
RED Tests added: 7 specific vulnerability regression tests
Result: PASS
Full Regression Result: 54 tests PASS.
Status: GO for PH-030.
