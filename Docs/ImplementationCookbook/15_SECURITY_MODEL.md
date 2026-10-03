# Maya Security Model, Adversarial Defense & External API Ledger

## 1. Adversarial Security Matrix

| Asset / Boundary | Attacker / Vector | Threat Description | Primary Enforcement | Defense in Depth | Adversarial Negative Test | Phase |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Approval Grants** | Malicious Actor | Replay previously granted approval token | `ApprovalBroker.consume_grant` (atomically deleted) | Timestamp expiry check (60s) | `test_approval_single_use_replay_denied` | PH050 |
| **Approval Payload**| Malicious Actor | Modify action parameters after approval granted | `ApprovalBroker.verify_grant` checks `action_hash` | Pydantic immutable model serialization | `test_approval_hash_mismatch_denied` | PH050 |
| **Pending Approvals**| Restart / Crash | Execute unapproved actions after daemon reboot | In-memory grant store (zero disk persistence) | Initial state starts in `READY_WAKE` with empty dict | `test_daemon_restart_clears_pending_approvals`| PH050 |
| **Model Output** | Prompt Injection | Model instructs arbitrary command execution | `ActionDispatcher` routes all requests to `PolicyEngine` | User popup confirmation on `ASK_USER` | `test_model_id_does_not_grant_preapproval` | PH060 |
| **AI Reasoning** | Eavesdropping | Leakage of private reasoning thoughts in logs | `NvidiaProvider.filter_reasoning` strips traces | Storage layer omits raw reasoning fields | `test_reasoning_trace_not_leaked` | PH060 |
| **Voice Audio** | Network Snooper| Transmitting ambient room audio to cloud STT | Local-only wake detector; zero network sockets | Disabling listening closes audio stream | `test_prewake_audio_zero_network_callback`| PH080 |
| **Browser DOM** | Malicious Page | Untrusted webpage executes commands via extension | Origin verification check in content script | Daemon domain allowlist enforcement | `test_browser_origin_mismatch_denied` | PH110 |
| **Credentials** | Web Scraper | Exfiltrating passwords or auth tokens from DOM | Element selector filters out password & auth fields | Generic adapter rejects input/textarea values | `test_password_and_secret_fields_not_extracted`| PH110 |
| **Local Dashboard** | Web Attacker | CSRF / DNS rebinding against control API | Bind strictly to `127.0.0.1`, same-origin checks | Disallow wildcard CORS in FastAPI middleware | `test_dashboard_cors_and_localhost_binding` | PH130 |
| **Filesystem** | Malicious Path | Symlink swap (TOCTOU) or path traversal (`../`) | Canonical `Path.resolve()` check within allowed roots | Read-only mode where write not requested | `test_file_executor_root_boundary` | PH040 |
| **OS Processes** | Shell Injection| Command injection via shell metacharacters (`;`, `\|`) | `asyncio.create_subprocess_exec` (strictly no shell) | Binary allowlists and argument prefix matching | `test_process_executor_argv_only` | PH040 |

---

## 2. Authoritative External API Verification Ledger

All external APIs used across Maya have been verified against current documentation as of **October 2026**:

| Library / Subsystem | Current Upstream Version | Verification Date | Authoritative API Surface Verified | Consuming Phases |
| :--- | :--- | :--- | :--- | :--- |
| **Pydantic v2** | `2.12.5` | 2026-10-03 | `BaseModel`, `ConfigDict(strict=True, extra="forbid")`, `Field`, `model_validate` | All phases |
| **FastAPI** | `0.115+` | 2026-10-03 | `FastAPI(lifespan=...)`, `StaticFiles(directory=...)`, `HTTPException`, `CORSMiddleware` | PH130 |
| **OpenAI Python SDK** | `1.50+` | 2026-10-03 | `AsyncOpenAI(base_url=..., api_key=..., max_retries=0, timeout=30.0)`, `chat.completions.create(stream=True)` | PH060 |
| **NVIDIA API Endpoint**| `v1` (OpenAI-compat)| 2026-10-03 | `https://integrate.api.nvidia.com/v1`, model `nvidia/nemotron-3-ultra-550b-a55b`, `force_nonempty_content` template kwargs | PH060 |
| **openWakeWord** | `0.6+` | 2026-10-03 | `openwakeword.model.Model(wakeword_models=[...])`, `predict(frame)` on 1280-byte 16kHz PCM chunks | PH080 |
| **Firefox Native Host**| WebExtension V2/V3 | 2026-10-03 | 4-byte native endian unsigned int length framing, stdin/stdout JSON streaming, `manifest.json` declaration | PH110, PH170 |
| **systemd User Service**| `systemd 255+` | 2026-10-03 | `systemd --user`, `MemoryHigh=240M`, `MemoryMax=300M`, `Restart=on-failure`, unit file placement in `~/.config/systemd/user/` | PH160, PH170 |
| **D-Bus / SNI** | `D-Bus 1.14+` | 2026-10-03 | `org.kde.StatusNotifierItem`, service name `org.freedesktop.StatusNotifierItem-{PID}-1`, standard property signals | PH100 |
| **SQLite (Python stdlib)**| Python 3.11+ stdlib| 2026-10-03 | `import sqlite3`, `PRAGMA journal_mode=WAL;`, `PRAGMA synchronous=NORMAL;`, parameter binding `?` | PH130 |
| **Python Asyncio** | Python 3.11+ stdlib| 2026-10-03 | `asyncio.create_subprocess_exec`, `asyncio.timeout`, `asyncio.Lock`, `asyncio.CancelledError` escalation | PH040, PH050, PH160 |
