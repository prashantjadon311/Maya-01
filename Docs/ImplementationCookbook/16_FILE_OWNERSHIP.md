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
| `extension/firefox/background.js` | PH110 | PH120 | Background service worker for native host | Native messaging pipe connector | Remote code evaluation |
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
| `app/browser/protocol.py` | PH040 | PH110 | BrowserBridge protocol definition | `BrowserBridge` protocol definition | Direct socket connections, subprocess spawns |
| `tests/test_approval_broker.py` | PH050 | — | ApprovalBroker unit & security test suite | Unit/security tests, timeout assertions | Production code, network calls |
| `tests/fakes/fake_popup.py` | PH050 | — | Test fake for interactive native popup | `FakePopup` class, canned responses | Real GUI windows, subprocesses |
| `tests/test_nvidia_provider.py` | PH060 | — | NvidiaProvider test suite | Unit/streaming tests, mock AsyncOpenAI | Real network calls |
| `tests/fakes/fake_nvidia.py` | PH060 | — | Test fake for OpenAI-compatible endpoint | `FakeOpenAIClient`, chunk streaming | Real network calls |
| `tests/test_command_router.py` | PH070 | — | CommandRouter test suite | Routing tier tests, exact match tests | Subprocess executions, live LLM calls |
| `tests/test_agent_runtime.py` | PH070 | — | AgentRuntime test suite | Step limit tests, loop bound tests | Unbounded loops, direct OS access |
| `tests/test_voice_wake.py` | PH080 | — | AudioSource and WakeDetector test suite | Ring buffer tests, mock wake detection | Network requests, audio persistence |
| `tests/fakes/fake_voice.py` | PH080 | — | Test fake for audio streams & wake | `FakeAudioSource`, synthetic PCM frames | Real soundcard capture |
| `tests/test_stt_adapter.py` | PH090 | — | STTAdapter test suite | Buffer release tests, STT mock tests | Pre-wake STT, audio persistence |
| `tests/fakes/fake_stt.py` | PH090 | — | Test fake for remote STT | `FakeSTTAdapter`, canned responses | Live network calls |
| `tests/test_tray.py` | PH100 | — | StatusNotifierTray test suite | State sync tests, property assertions | Real X11/Wayland window creation |
| `tests/fakes/fake_dbus.py` | PH100 | — | Test fake for D-Bus connection | `FakeDBusBus`, mock registration | Real system bus operations |
| `tests/test_browser_bridge.py` | PH110 | — | NativeMessageBridge test suite | 1MB framing tests, origin security tests | Live browser process spawning |
| `tests/fakes/fake_browser.py` | PH110 | — | Test fake for native messaging pipe | `FakeExtensionPipe`, canned DOM responses | Live network/browser calls |
| `tests/test_site_adapters.py` | PH120 | — | Site adapters test suite | DOM parsing tests, ADAPTER_OUTDATED tests | Live web scraping |
| `tests/test_dashboard_api.py` | PH130 | — | FastAPI dashboard & storage test suite | TestClient requests, same-origin tests | Non-localhost network binding |
| `tests/test_dashboard_frontend.py` | PH140 | — | Static web assets test suite | HTML/CSS tests, reduced motion tests | External CDN dependencies |
| `tests/test_developer_workflows.py` | PH150 | — | Developer tools test suite | DeveloperToolExecutor tests, isolation tests | Auto-commit without policy |
| `tests/test_resource_hardening.py` | PH160 | — | Cgroup & resource stress test suite | Stress runs, memory boundary tests | Modifying cgroup limits |
| `packaging/install.sh` | PH170 | — | User installation script | systemctl user commands, symlinks | Sudo/root execution |
| `packaging/uninstall.sh` | PH170 | — | User uninstallation script | systemctl user disable, cleanup | Sudo/root execution |
| `tests/test_packaging.py` | PH170 | — | Packaging verification test suite | Manifest & service file syntax tests | System-wide modifications |
| `tests/test_offline_determinism.py` | PH180 | — | Offline determinism acceptance suite | Offline test cases | Live external network calls |
| `Docs/Current/PH180_FINAL_ACCEPTANCE_REPORT.md` | PH180 | — | Final V1 acceptance and verification report | Verification tables, test results | Unverified claims |

