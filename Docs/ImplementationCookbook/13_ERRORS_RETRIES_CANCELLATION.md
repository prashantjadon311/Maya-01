# Maya Error Taxonomy, Retries, and Cancellation Semantics

## 1. Unified Error Taxonomy

All Maya exceptions inherit from `MayaBaseError` and define structured attributes for audit logging and user messaging:

| Exception Class | Category | Retryable | Audit Severity | User Notification |
| :--- | :--- | :--- | :--- | :--- |
| `SecurityViolationError` | Security | **NO** | `CRITICAL` | "Action blocked by security policy" |
| `ApprovalDeniedError` | Security | **NO** | `INFO` | "Action denied by user" |
| `ApprovalTimeoutError` | Security | **NO** | `WARNING` | "Approval request timed out" |
| `InvalidGrantError` | Security | **NO** | `CRITICAL` | "Invalid or replayed approval grant" |
| `PathTraversalError` | Security | **NO** | `CRITICAL` | "Access outside allowed paths blocked" |
| `ProviderAPIError` | External AI | **NO** (fail-fast) | `WARNING` | "AI provider temporarily unavailable" |
| `ProviderTimeoutError` | External AI | **YES** (max 1 retry) | `WARNING` | "AI reasoning timed out" |
| `STTRecognitionError` | Voice | **NO** | `INFO` | "Could not understand voice command" |
| `BrowserBridgeError` | Browser | **NO** | `WARNING` | "Firefox extension disconnected" |
| `AgentStepLimitError` | Resource | **NO** | `WARNING` | "Agent task reached maximum step limit" |
| `MemoryLimitExceededError`| Resource | **NO** | `CRITICAL` | "System memory threshold exceeded" |

---

## 2. Retry Policy & Idempotency Rules

1. **ZERO RETRIES ON SIDE EFFECTS:** Any operation that creates files, deletes files, modifies filesystem state, spawns subprocesses, or submits web forms is strictly **non-idempotent** and must **NEVER** be automatically retried upon failure.
2. **SDK RETRIES DISABLED:** As mandated by `DOCS.md`, the OpenAI SDK's built-in automatic retries are disabled (`max_retries=0`). Maya maintains complete ownership of the retry loop.
3. **READ-ONLY RETRY BUDGET:** Transient network failures on read-only queries (e.g. initial AI completion request) may retry once after a 1.0s backoff.

---

## 3. Cancellation Semantics & Subprocess Cleanup

When an asyncio task is cancelled (via `task.cancel()`):

```python
async def execute_with_cancellation_cleanup(proc: asyncio.subprocess.Process, timeout: float):
    try:
        async with asyncio.timeout(timeout):
            stdout, stderr = await proc.communicate()
            return stdout, stderr
    except (asyncio.CancelledError, TimeoutError):
        # 1. Graceful SIGTERM
        if proc.returncode is None:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=0.5)
            except TimeoutError:
                # 2. Forceful SIGKILL escalation
                proc.kill()
                await proc.wait()
        raise
```

- Every task awaiting an external process or HTTP stream must handle `asyncio.CancelledError` and explicitly terminate child resources before re-raising.
