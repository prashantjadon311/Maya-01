# Maya Trust Boundaries & Security Model

## 1. Input Trust Classification

Maya treats almost all runtime inputs as inherently untrusted or potentially hostile. No subsystem accepts external data without schema validation, authorization, and sanitization.

| Input Source | Trust Level | Threat Vectors | Primary Enforcement Point | Defense in Depth | Failure Mode |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **AI Model Output** | `UNTRUSTED` | Prompt injection, unauthorized tool execution, malicious argv | Strict Pydantic parsing into `ActionRequest`, PolicyEngine | ApprovalBroker / user confirmation | Reject action, fail-closed to DENY |
| **Browser DOM / Text** | `UNTRUSTED` | DOM-based XSS, secret extraction, malicious page redirects | Site Adapters with explicit selector allowlists | Origin verification in content script (`verifyTabOrigin`) | Empty extraction, safe abort |
| **Native IPC (Firefox)** | `UNTRUSTED` | Malicious extension impersonation, message replay | Length-prefixed protocol framing, domain permission checks | Daemon domain allowlist + origin check | Close pipe, reject message |
| **Voice Audio** | `SENSITIVE` | Ambient eavesdropping, audio leakage over network | Local-only wake detector, memory-only ring buffer | Zero network calls before wake detection | Buffer drop, zero STT |
| **Web Dashboard (HTTP)** | `LOCAL_AUTH` | CSRF, DNS rebinding, unauthorized API calls | Bind strictly to `127.0.0.1`, same-origin checks, no CORS | Pydantic payload validation | HTTP 403 Forbidden |
| **Action Packs (JSON)** | `CONFIG` | Malicious command injection, path traversal via symlinks | `ActionRegistry` JSON validation, strict symlink rejection | Subprocess execution allowlists | Discard invalid pack, retain LKG |
| **File Paths & Symlinks**| `UNTRUSTED` | Path traversal (`../`), symlink swap (TOCTOU), `/etc` overwrite | `FileExecutor` canonical `Path.resolve()` check within roots | Separate delete authorization policy | Raise `PathTraversalError`, DENY |
| **Subprocess Output** | `UNTRUSTED` | Terminal escape injection, unbounded memory exhaustion | Bounded stream reader (64KB cap), non-shell execution | Sanitization before audit logging | Truncate output at 64KB |

---

## 2. Central Invariants

1. **NO EXECUTOR BYPASS:** Every action proposed by model, router, agent, or web UI must pass through `ActionDispatcher.dispatch_action_request`.
2. **CRYPTOGRAPHIC APPROVAL BINDING:** An approval grant issued by the `ApprovalBroker` is bound to `SHA-256(canonical_json(action_payload))`. Any alteration of arguments or command invalidates the grant immediately.
3. **SINGLE-USE GRANTS:** Approval grants are consumed atomically upon first verification and cannot be replayed.
4. **FAIL-CLOSED POLICY:** Any validation failure, timeout, unhandled error, or missing permission immediately resolves to `DENY`.
