# Maya File Ownership & Responsibility Matrix

Every file in the Maya repository (both existing PH-000..PH-040 files and future PH-050..PH-180 files) has **exactly one primary owner phase**. Secondary phases may only modify files if explicitly declared in `secondary_modifiers`. Any modification outside these declared boundaries is strictly forbidden.

---

## 1. Master File Ownership Table

| File Path | Owner Phase | Secondary Modifiers | Purpose | Allowed Contents | Forbidden Contents |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `app/core/dispatcher.py` | PH040 | PH050, PH070 | Central action dispatching & policy gateway | `ActionDispatcher` class, execution routing | Direct OS execution bypassing executors |
| `app/core/state.py` | PH000 | PH080, PH100 | System runtime state machine | `AppState`, `SystemState` enum | Business logic, executor calls |
| `app/core/config.py` | PH010 | PH060, PH080, PH130 | Configuration schemas & TOML loader | Pydantic config models, validation | Runtime state mutation |
| `app/policy/engine.py` | PH020 | PH050 | Policy evaluation (ALLOW, ASK, DENY) | `PolicyEngine`, `PolicyEvaluation` | Subprocess calls, executor logic |
| `app/actions/registry.py` | PH030 | PH150 | Action pack loading and phrase table | `ActionRegistry`, pack parsing | Arbitrary code execution, symlinks |
| `app/executors/process.py` | PH040 | — | Safe process execution with argv allowlists | `ProcessExecutor`, bounded capture | `shell=True`, unbounded buffers |
| `app/executors/files.py` | PH040 | — | Sandboxed file operations | `FileExecutor`, canonical path checks | Path traversal escape (`../`) |
| `app/executors/xdg.py` | PH040 | — | Desktop launcher using xdg-open | `XdgExecutor`, URL validation | Arbitrary command execution |
| `app/policy/broker.py` | PH050 | — | Interactive approval broker & hash binding | `ApprovalBroker`, `ApprovalGrant` | Persistent disk grant storage |
| `app/ai/nvidia.py` | PH060 | — | NVIDIA Nemotron AsyncOpenAI adapter | `NvidiaProvider`, streaming, tools | Direct OS execution, reasoning leakage |
| `app/core/command_router.py` | PH070 | — | 4-tier command classification & routing | `CommandRouter`, routing decisions | Direct executor bypass |
| `app/agents/runtime.py` | PH070 | — | Bounded single logical agent loop | `AgentRuntime`, step loop, transcript | Unbounded agent swarms, policy bypass |
| `app/agents/model.py` | PH070 | — | Agent task & step data schemas | `AgentTask`, `AgentTaskResult` | Runtime execution logic |
| `app/voice/audio.py` | PH080 | — | Audio stream capture & ring buffer | `AudioSource`, circular buffer | Network sockets, disk audio writes |
| `app/voice/wake.py` | PH080 | — | Local wake word detector (openWakeWord) | `WakeDetector`, 1-thread inference | Network calls, cloud STT |
| `app/voice/recorder.py` | PH080 | — | Post-wake command audio recording | `CommandRecorder`, VAD silence stop | Pre-wake audio retention |
| `app/voice/stt.py` | PH090 | — | Remote STT adapter for command audio | `STTAdapter`, buffer release logic | Pre-wake STT, audio persistence |
| `app/tray/status_notifier.py` | PH100 | — | StatusNotifierItem over D-Bus | `StatusNotifierTray`, property signals | Heavyweight GUI window creation |
| `app/browser/native_bridge.py` | PH110 | — | Firefox Native Messaging bridge host | `NativeMessageBridge`, framing | Unrestricted DOM access |
| `extension/firefox/manifest.json` | PH110 | — | Firefox WebExtension manifest | Manifest metadata & permissions | Broad wildcards without user prompt |
| `extension/firefox/background.js` | PH110 | — | Background service worker for native host | Native messaging pipe connector | Remote code evaluation |
| `extension/firefox/native.js` | PH110 | — | Tab origin validation & message dispatch | `verifyTabOrigin` function | Origin mismatch execution |
| `extension/firefox/generic.js` | PH110 | — | Generic DOM text extraction | `extractVisibleText`, password filter | Reading password inputs, cookies |
| `extension/firefox/adapters/base.js` | PH120 | — | Base site adapter interface | `BaseAdapter`, outdated DOM handler | Silent failure, selector injection |
| `extension/firefox/adapters/google.js` | PH120 | — | Semantic adapter for Google Search | `GoogleAdapter` class | Ad clicking, cookie exfiltration |
| `extension/firefox/adapters/amazon.js` | PH120 | — | Semantic adapter for Amazon Search | `AmazonAdapter` class | Automatic checkout, purchasing |
| `extension/firefox/adapters/chatgpt.js` | PH120 | — | Semantic adapter for ChatGPT web UI | `ChatGPTAdapter` class | Account settings modification |
| `extension/firefox/adapters/claude.js` | PH120 | — | Semantic adapter for Claude.ai | `ClaudeAdapter` class | Account settings modification |
| `extension/firefox/adapters/gemini.js` | PH120 | — | Semantic adapter for Gemini web UI | `GeminiAdapter` class | Account settings modification |
| `app/api/app.py` | PH130 | — | FastAPI dashboard application factory | `create_dashboard_app` function | Wildcard CORS, binding to 0.0.0.0 |
| `app/api/routes_config.py` | PH130 | — | Configuration CRUD endpoints | Config API routes with validation | Unvalidated config overwrites |
| `app/api/routes_audit.py` | PH130 | — | Paginated audit event log query routes | Audit GET routes (limit/offset) | Unbounded audit log dumps |
| `app/storage/sqlite.py` | PH130 | — | Local SQLite storage layer | `SQLiteStorage`, WAL mode queries | Plaintext secret storage |
| `app/web/index.html` | PH140 | — | Static single-page dashboard shell | Semantic HTML, SVG AI Core markup | Inline javascript, CDN scripts |
| `app/web/css/app.css` | PH140 | — | Custom dashboard styling & animations | CSS styling, reduced motion rules | Remote @import rules |
| `app/web/js/app.js` | PH140 | — | Vanilla JS dashboard controller | EventSource listener, DOM updates | Node dependencies, frontend builds |
| `app/executors/developer.py` | PH150 | — | Developer git/test workflow executors | `DeveloperToolExecutor` class | Auto-commit without verification |
| `app/core/lifecycle.py` | PH160 | — | Daemon lifecycle & memory monitoring | `LifecycleManager`, memory monitor | Raising MemoryMax limit |
| `packaging/systemd/maya.service` | PH170 | — | User systemd unit file | systemd unit definition | Root service configuration |
| `packaging/native-manifest/project_h_firefox.json` | PH170 | — | Native messaging host manifest | Native host binary path | Executable scripts directly |
| `tests/test_offline_determinism.py` | PH180 | — | Offline determinism acceptance suite | Offline test cases | Live external network calls |
