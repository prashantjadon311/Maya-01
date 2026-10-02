# Project H V2 — Implementation Tasks

## PH-000 — Repository and Measurement Harness
- [x] Create Python package skeleton (`app/`, `tests/`).
- [x] Add `pytest`, `anyio`.
- [x] Create memory measurement script/test (using `psutil` in test env).
- [x] Add config fixtures.
- [x] Add `.gitignore` for secrets/audio/temp.
- [x] **Acceptance:** Empty daemon starts/stops cleanly, baseline RSS recorded (initial=13.24 MiB, active=15.96 MiB), no heavy dependencies loaded. (Batch 1A verification passed).

## PH-010 — Config and Schemas
- [x] Implement `config.toml` parser/model.
- [x] Implement core models: `AppState`, `CommandRequest`, `ActionRequest`, `ActionResult`.
- [x] Implement JSON action-pack schema validation.
- [x] **Acceptance:** Valid config passes, unknown fields fail (`extra="forbid"`), invalid memory limits fail (memory_max_mb <= 300, memory_high_mb <= memory_max_mb). Schemas use Pydantic v2. `ActionRequest` defines canonical deterministic JSON serialization for hashing (`to_canonical_json` / `to_canonical_bytes`). (Batch 1B verification passed: 22 targeted tests pass).

## PH-020 — Policy Engine
- [x] Implement `PolicyDecision` enum (`ALLOW_PREAPPROVED`, `ASK_USER`, `DENY`).
- [x] Implement `ApprovalRequest` with `ConfigDict(frozen=True)` and strict SHA-256 action hash.
- [x] Implement `PolicyEngine`.
- [x] **Acceptance:** Deterministic `ALLOW_PREAPPROVED` / `ASK_USER` / `DENY` outcomes. `sudo` always asks (`ASK_USER`). Files outside roots deny. Action hash changes invalidate approval. (Batch 2 verification passed: 10 targeted tests pass).

## PH-030 — Deterministic Action Registry
- [x] Implement `ActionDefinition` and `ActionPack` schema (Completed in Foundation Closure).
- [ ] Implement `ActionRegistry` for loading action packs.
- [ ] Implement phrase matching and composite action validation.
- [ ] **Acceptance:** Ambiguous phrase does not execute; disabled action ignored; malformed JSON keeps last valid pack.

## PH-040 — Safe Executors and Action Dispatcher
- [ ] Implement `ActionDispatcher` to wrap Policy + Executors.
- [ ] Implement `ProcessExecutor` (argv only, `shell=False`, cwd roots).
- [ ] Implement `FileExecutor` (canonicalization, root containment, atomic write).
- [ ] Implement `BrowserBridge` interface stub.
- [ ] **Acceptance:** Dispatcher enforces `PolicyEngine` decision. Direct invocation of executors is prevented by design. Symlinks/`..` paths in `FileExecutor` fail.

## PH-050 — Approval Popup
- [ ] Implement `ApprovalBroker`.
- [ ] Implement native/transient UI popup process.
- [ ] **Acceptance:** Timeout denies, wrong hash denies, allow once consumed once. Integration test passes with fake popup.

## PH-060 — NVIDIA Nemotron Provider
- [ ] Implement `AIProvider` base interface.
- [ ] Implement `NvidiaProvider` (reusable async client, custom URL, streaming, tool calls, max_retries=0).
- [ ] **Acceptance:** Client streams content but filters reasoning traces. Fake HTTP provider used for default test suite.

## PH-070 — Command Router + Agent Runtime
- [ ] Implement `CommandRouter` (Registry -> Built-ins -> AI).
- [ ] Implement `AgentRuntime` and `AgentTask`.
- [ ] **Acceptance:** Exact local action causes zero AI calls. Agent respects max steps/budgets and uses `ActionDispatcher` for all tools.

## PH-080 — Voice Wake Pipeline
- [ ] Implement `WakeDetector` (local stream processing).
- [ ] Implement `CommandRecorder` with VAD/end-of-command.
- [ ] **Acceptance:** No network callback before wake. Ring buffer strictly bounded. Pre-wake audio stays local.

## PH-090 — STT Adapter
- [ ] Implement `STTProvider` (NVIDIA multilingual ASR adapter).
- [ ] **Acceptance:** Wake -> Record -> STT flow succeeds. Transcript is normalized, audio buffer released from memory.

## PH-100 — Tray / StatusNotifierItem
- [ ] Implement D-Bus tray item.
- [ ] **Acceptance:** Status changes visible. Push-to-talk, pause, dashboard buttons work. Memory RSS impact measured.

## PH-110 — Firefox Extension + Native Bridge
- [ ] Implement Firefox Native Messaging host using authenticated Unix-domain socket IPC with `project-hd`.
- [ ] Implement extension background and content script registration.
- [ ] **Acceptance:** Unauthenticated local processes cannot invoke the bridge. Unlisted domains denied by daemon policy.

## PH-120 — Site Adapters
- [ ] Implement Google, Amazon, ChatGPT, Gemini, Claude, and Generic adapters.
- [ ] **Acceptance:** Graceful outdated failure. Domain capability enforcement.

## PH-130 — Dashboard Backend
- [ ] Implement FastAPI localhost-only app with static file serving.
- [ ] Add state/event stream and CRUD API.
- [ ] **Acceptance:** No wildcard CORS. Backend owns shared resources via lifespan.

## PH-140 — Dashboard Frontend
- [ ] Implement UI (HTML, local Bootstrap CSS, vanilla JS, SVG AI Core).
- [ ] **Acceptance:** Screens built without heavy frontend frameworks. Keyboard accessible. Responsive mobile fallback.

## PH-150 — Developer Workflows
- [ ] Implement repo registration, git status/diff, and `code` CLI open commands.
- [ ] **Acceptance:** Execute under policy. No auto-commit by default.

## PH-160 — Resource Hardening
- [ ] Perform full stress scenario tests.
- [ ] **Acceptance:** Resident cgroup peak stays `<= 300 MiB`.

## PH-170 — Packaging
- [ ] Create systemd unit, config install, extension packaging.
- [ ] **Acceptance:** Clean install and uninstall tests pass.

## PH-180 — Final Acceptance
- [ ] Final suite verification.
- [ ] **Acceptance:** Full unit/integration tests pass, red-team permission checks pass, voice privacy confirmed.

---

# Current Checkpoint

```text
CURRENT_TASK: PH-030
STATUS: FOUNDATION_CLOSURE_VERIFIED_CI_GREEN_READY_FOR_PH030
ARCHITECTURE_REVIEWED_BY_GEMINI_31_PRO: true
ARCHITECTURE_FROZEN: yes
FIGMA_CREATED: yes
LIVE_PROVIDER: NVIDIA Nemotron 3 Ultra
NEXT_EXACT_ACTION: Codex implements PH-030 Action Registry only
```
