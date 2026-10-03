# PH-040 Safe Executors, Action Dispatcher, and Security Closure Result

## 1. Summary & Status
- **Base Main SHA:** `82735686f2441190bf6b961bc6e5bd015001ab19` (main after premature PR #1 merge)
- **Branch SHA:** `030a8256b848e220fb99978188df937f831cdd33`
- **PR:** #2 (https://github.com/prashantjadon311/Maya-01/pull/2)
- **Status:** PH040_SECURITY_FIX_CI_GREEN_AWAITING_INDEPENDENT_REVIEW
- **Next Exact Action:** Independent PH-040 security/code review of repair PR before merge

## 2. Security Closure Repairs Applied
- **Process Executor Allowlist Hardening:**
  - `ProcessExecutor` now treats an empty `env_allowlist = ()` as rejecting all caller-supplied environment variables.
  - Hard denial for dangerous variables (`LD_PRELOAD`, `PYTHONPATH`, etc.) remains enforced.
  - Defense-in-depth context requirement: `ProcessExecutor` fails closed if called without a valid `ALLOW_PREAPPROVED` `PolicyEvaluation` context containing matched rule and resolved executable.
  - Stream reader tasks cancelled during timeout escalation are explicitly awaited with `asyncio.gather(..., return_exceptions=True)` to prevent unhandled pending task warnings.
  - Explicit `NetworkIsolationBackend` capability abstraction introduced. Offline preapproval rules fail closed when no isolation backend is present.
- **Trusted Executable Resolution:**
  - `resolve_trusted_executable()` enforces strict V1 resolution against configured system directories (`/usr/bin`, `/bin`, `/usr/local/bin`, `/usr/lib`, `/lib`).
  - Absolute paths outside trusted system roots (e.g. `/home/user/bin/git`, `/tmp/malicious_git`) and relative paths with slashes (`./git`, `bin/git`) are rejected.
  - Resolved executables must exist, be regular files, be executable, and canonicalize within trusted system roots.
- **XDG Executor Security:**
  - Removed `shutil.which("xdg-open")` fallback completely. Resolution uses `resolve_trusted_executable("xdg-open")` exclusively.
  - Frozen `xdg-open` to local filesystem targets only; all URI schemes (e.g. `http:`, `https:`, `ftp:`, `mailto:`, `ssh:`, `javascript:`, `data:`, `file:`) are rejected.
  - Target paths are canonicalized, checked for sensitive locations/credentials, and required to pass configured file read root policy before invocation.
- **Preapproval Rule Risk Floor:**
  - `PolicyEngine.evaluate_detailed()` computes `effective_trusted_risk = max(structural_risk, matched_rule_risk)`.
  - Matched preapproval rule risk can only raise effective trusted risk, never lower structural risk.
- **File Executor & Dispatcher Hardening:**
  - `_map_executor_to_tool()` requires explicit valid operations (`read`, `write`, `list`, `delete`). Invalid operations (e.g. `wat`, empty string, missing field) return `None` and fail closed.
  - `file.read` uses `os.open` with `O_RDONLY` and `O_NOFOLLOW` (descriptor-bound I/O and `fstat` validation).
  - `file.list` verifies target directory is not a symlink and inspects entries using `follow_symlinks=False` semantics without following child symlinks.
  - `file.write` checks symlinks before and after atomic `os.replace` temp file creation.
- **Composite Snapshot-Bound Execution:**
  - Carries originating `snapshot_version` throughout composite execution.
  - Verifies `expected_snapshot_version == registry.snapshot_version` before executing each child step. If the registry reloads mid-composite, execution aborts cleanly as stale.
- **Audit Fallback Deque:**
  - `ActionDispatcher` maintains a bounded in-memory `recent_audits` deque (`maxlen=256`).
  - Emits metadata-only events for all decisions (`DENY`, `ASK_USER`, success, failure). If external `audit_sink` is `None` or throws an exception, the internal audit event is retained.

## 3. Test Suite & Verification Results
- **Targeted Tests (`tests/test_executors.py` & `tests/test_dispatcher.py`):** 41 passed.
- **Full Test Suite (`pytest -v`):** 378 passed in 2.87s.
- **Git Diff Hygiene (`git diff --check`):** Clean (no whitespace errors).
- **Installed Import Check:** Verified outside checkout (`python -I`).

## 4. Resident Memory (RSS)
- Active process baseline with daemon and all PH-040 modules: 37.348 MiB.
- Well within memory budget (final memory stress gate remains PH-160).

## 5. Deferred Requirements
- **PH-050:** Interactive human approval UI popup and `ApprovalBroker`.
- **PH-110:** Firefox WebExtension and authenticated Unix socket native messaging bridge.
- **PH-130:** SQLite audit trail persistence.
- **PH-160:** Systemd cgroup memory stress limit verification.
