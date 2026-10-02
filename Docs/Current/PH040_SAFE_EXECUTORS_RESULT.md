# PH-040 Safe Executors and Action Dispatcher Result

## 1. Summary & Status
- **Base SHA:** `9205eaeb38e0d535d9e3aabb231b75b0e1d52afd`
- **Branch SHA:** TBD (set upon commit)
- **PR:** TBD (set upon pull request creation)
- **Status:** PH040_IMPLEMENTED_CI_GREEN_AWAITING_SECURITY_REVIEW
- **Next Exact Action:** Independent PH-040 security/code review before merge

## 2. Modified & Created Files
- `app/actions/schema.py`: Added `strict=True` to `ActionDefinition` and `ActionPack` Pydantic models.
- `app/actions/matcher.py`: Added post-normalization phrase length check; strict substitution failing closed on missing slots.
- `app/actions/registry.py`: Deeply immutable `RegistryMatch` and `RegistryAmbiguity`; freshness-bound `snapshot_version`; non-overwriting phrase matches by `(action_id, slot_values)`; duplicate JSON key rejection hook; bounded chunked file reading; transactional LKG; total phrases ceiling (`MAX_TOTAL_PHRASES = 4096`); composite disabled child rejection.
- `app/policy/engine.py`: Added `PolicyEvaluation` data structure, `evaluate_detailed()` returning matched rule and resolved executable, `resolve_trusted_executable()` preventing ambient PATH hijacking.
- `app/core/dispatcher.py`: Central `ActionDispatcher` enforcing schema -> materialization -> policy -> definition floor -> executor constraints pipeline. Supports separated `dispatch_request` and `dispatch_match` routes, composite step isolation, and metadata audit sink.
- `app/executors/base.py`: Base protocol and strict argument models (`ProcessArgs`, `FileReadArgs`, `FileListArgs`, `FileWriteArgs`, `FileDeleteArgs`, `XdgOpenArgs`).
- `app/executors/process.py`: Subprocess executor enforcing argv-only (`shell=False`), controlled cwd with pre-spawn containment revalidation, minimal controlled env, bounded output capture, kill escalation on timeout, and fail-closed network isolation.
- `app/executors/files.py`: Contained file executor enforcing canonicalization, sensitive path rejection, root containment, capability checks, atomic write with fsync, symlink protection, and non-execution of delete.
- `app/executors/xdg.py`: XDG executor for local files and apps; strictly forbids HTTP/HTTPS URLs to prevent bypassing browser domain policy.
- `app/browser/protocol.py`: Protocol stub for browser bridge in PH-040. Browser tool executions without bridge fail closed.
- `tests/test_registry.py`: 10 new regression tests for PH-030 post-review repairs.
- `tests/test_executors.py`: 16 comprehensive executor security tests.
- `tests/test_dispatcher.py`: 13 dispatcher and policy contract tests.
- `.github/workflows/tests.yml`: Updated outside-checkout import verification to include all PH-040 modules across Python 3.11 and 3.14.
- `Docs/TASKS.md`: Updated checklist and checkpoint.
- `Docs/Current/PH030_ACTION_REGISTRY_RESULT.md`: Corrected RSS wording.

## 3. Exact Policy & Approval Semantics
- **PolicyEngine Integration:** `evaluate_detailed()` produces `PolicyEvaluation` with decision, structural risk, matched `PreapprovalRule`, and resolved binary path.
- **Definition Approval/Risk Floor:** Stricter-wins semantics:
  - Definition `deny` overrides lower policy decisions.
  - Definition `always_ask` or `ask_user` overrides policy `ALLOW_PREAPPROVED`.
  - Definition `preapproved` does not grant execution alone; requires `ALLOW_PREAPPROVED` from PolicyEngine.
  - Definition risk only raises effective risk. High/critical effective risk always requires approval.
  - Model-supplied `ActionRequest.id` matching a registered action ID grants zero extra trust.
- **ApprovalRequest Rule:**
  - `ApprovalRequest` represents an action awaiting human approval, NOT an authorization grant.
  - A manually created `ApprovalRequest` cannot authorize execution.
  - In PH-040, `ASK_USER` actions never execute and return an approval-required state.

## 4. Executor Constraints & Security Invariants
- **Process Executor:**
  - Only `asyncio.create_subprocess_exec` (no shell).
  - No ambient PATH trust for preapproved executables: resolved against fixed trusted system paths.
  - Controlled cwd revalidated immediately before spawn.
  - Minimal controlled environment; dangerous vars (`LD_PRELOAD`, etc.) forbidden; variables restricted to rule allowlist.
  - Bounded stdout/stderr streaming (1 MiB ceiling).
  - Escalation on timeout: terminate -> wait -> kill -> reap (no zombies).
  - `network_allowed=False` fails closed because no isolation backend is present in PH-040.
- **File Executor:**
  - Full canonicalization and root containment checked immediately before I/O.
  - Sensitive paths (`/etc`, `/root`, `~/.ssh`, `~/.gnupg`, etc.) and `.env` credentials permanently blocked.
  - Read capped at 10 MiB; directory listing capped at 1024 entries.
  - Atomic write via temporary file in same parent directory + `os.fsync` + pre-replace TOCTOU revalidation.
  - Target path symlinks strictly rejected on write.
  - `file.delete` does not auto-execute.
- **XDG Executor:**
  - Rejects HTTP/HTTPS schemes so browser URLs cannot bypass browser domain policy.
  - Executes local apps/files via argv without shell.
- **Browser Bridge:**
  - Protocol stub only. Any browser request without a connected native messaging bridge fails closed.
- **Composite Execution:**
  - Sequentially dispatches child actions through central dispatcher.
  - Every child passes policy independently. Parent approval never authorizes child.
  - Bounded recursion depth (<= 5) and steps (<= 32).
  - Stops immediately on any child denial, approval requirement, or execution error.
  - Disabled child actions rejected during candidate registry validation and re-checked at runtime.

## 5. Audit Metadata Emission
- Injected `audit_sink` callback emits metadata events:
  `timestamp`, `request_id`, `actor`, `tool`, `policy_decision`, `target`, `result_code`, `duration`, `error`.
- Never logs sensitive file contents, credentials, API keys, or raw prompts.

## 6. Test Suite & Verification Results
- `tests/test_registry.py` & `tests/test_schemas.py`: 106 passed.
- `tests/test_policy.py` & `tests/test_policy_contract.py`: 189 passed.
- `tests/test_executors.py` & `tests/test_dispatcher.py`: 29 passed.
- **Full test suite (`pytest -v`):** 366 passed in 3.13s.
- **Installed outside-checkout verification (`python -I`):** PASSED.
- **Git diff check (`git diff --check`):** Clean (no whitespace errors).

## 7. Resident Memory (RSS)
- Initial empty Python process: 13.836 MiB.
- Active process with daemon and all PH-040 modules imported: 37.348 MiB.
- Well within memory budget (final memory stress gate remains PH-160).

## 8. Deferred Requirements
- **PH-050:** Interactive human approval UI popup and `ApprovalBroker`.
- **PH-110:** Firefox WebExtension and authenticated Unix socket native messaging bridge.
- **PH-130:** SQLite audit trail persistence.
- **PH-160:** Systemd cgroup memory stress limit verification.
