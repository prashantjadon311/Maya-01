# Maya Implementation Review Checklist (4 Mandatory Gates)

Every phase implementation MUST pass these four formal review gates before a commit is created and the phase is marked complete.

---

## Gate A: Architecture Review
- [ ] **Placement:** Every new class/function is placed in its declared file according to `16_FILE_OWNERSHIP.md`.
- [ ] **Dependency Direction:** No forbidden edges exist (e.g. AI provider never calls executors directly; agents route through `ActionDispatcher`).
- [ ] **Composition Root:** Shared services are instantiated once in `app/lifecycle.py`; no ad-hoc singleton or shared service instantiation in request handlers.
- [ ] **State Ownership:** Every mutable dictionary/list has exactly one declared owner class.
- [ ] **Object Lifetimes:** Daemon, session, and command lifetimes are strictly observed; cleanup methods (`close()`, `aclose()`, `reset()`) implemented.
- [ ] **Interface Conformance:** Public methods match the exact frozen signatures in `09_PUBLIC_INTERFACES.md`.

---

## Gate B: Security Review
- [ ] **Central Dispatcher Gateway:** All actions pass through `ActionDispatcher.dispatch_action_request`; zero executor bypasses.
- [ ] **Cryptographic Hash Binding:** Approval grants verify `SHA-256(canonical_json(req))` using `hmac.compare_digest`.
- [ ] **Single-Use Tokens:** Approval tokens are consumed and deleted atomically; cannot be replayed.
- [ ] **Fail-Closed Policy:** Every missing permission, timeout, or validation exception resolves strictly to `DENY`.
- [ ] **Subprocess Isolation:** All process calls use `asyncio.create_subprocess_exec` with explicit argv; `shell=True` is forbidden.
- [ ] **Path Sandboxing:** Filesystem operations resolve canonical paths via `Path.resolve()` and verify containment in allowed roots.
- [ ] **Voice Privacy:** Pre-wake audio is memory-only; zero network calls occur before wake detection.
- [ ] **Browser Double Gate:** Daemon domain allowlist AND browser host permission AND content script origin verification enforced.
- [ ] **Secret Exclusion:** Passwords, credentials, and API keys are never stored in SQLite, logged in audits, or sent in model prompts.

---

## Gate C: Fresher Implementability Review
- [ ] **Zero Guesswork:** Does the instruction specify exact File, Symbol, Signature, Inputs, Algorithm, Outputs, Bounds, and Error handling?
- [ ] **No Vagueness:** Are words like "handle properly", "as needed", or "securely validate" completely eliminated and replaced with explicit code?
- [ ] **Test Blueprint:** Is every test provided with Arrange, Act, Assert, and Assert-NOT recipes?

---

## Gate D: Token Efficiency & Context Economy
- [ ] **Phase Locality:** Does the phase require reading only its own `PHxxx.md` packet and direct dependencies?
- [ ] **No Narrative Duplication:** Historical narratives, superseded discussions, and duplicate rationale removed.
- [ ] **Preserved Contracts:** No essential signatures, bounds, or security invariants were removed during compression.
