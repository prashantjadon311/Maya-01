# Maya File Ownership & Responsibility Matrix

Every file in the Maya repository (both existing PH-000..PH-040 files and future PH-050..PH-180 files) has **exactly one primary owner phase**. Secondary phases may only modify files if explicitly declared in `secondary_modifiers`. Any modification outside these declared boundaries is strictly forbidden.

---

## 1. Master File Ownership Table

| File Path | Owner Phase | Secondary Modifiers | Purpose | Allowed Contents | Forbidden Contents |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `app/core/dispatcher.py` | PH040 | PH050, PH070 | Central action dispatching and security boundary enforcement | ActionDispatcher class; dispatch logic; executor invocation | direct OS subprocess calls without executor; policy bypass |
| `app/core/state.py` | PH000 | PH080, PH100 | Application runtime state machine and event dispatch | AppState class; SystemState enum; transition methods | business logic; executor calls |
| `app/core/config.py` | PH010 | PH060, PH080, PH130, PH090 | Configuration schemas and TOML loading | Pydantic config models; load_config function | runtime state mutation |
| `app/policy/engine.py` | PH020 | PH050 | Pure policy evaluation against preapprovals and rules | PolicyEngine class; PolicyEvaluation; PolicyDecision | executor invocation; subprocess calls |
| `app/actions/registry.py` | PH030 | PH150 | Action pack loading, schema validation, and phrase lookup table | ActionRegistry class; ActionPack loading | arbitrary code execution; symlink following |
| `app/executors/process.py` | PH040 | PH050 | Safe process execution with argv allowlists and bounded buffers | ProcessExecutor class; subprocess exec | shell=True; unbounded output capture |
| `app/executors/files.py` | PH040 | PH050 | Sandboxed file operations with canonical path validation | FileExecutor class; path validation | path traversal escape; arbitrary root overwrite |
| `app/executors/xdg.py` | PH040 | PH050 | Desktop launcher using xdg-open for validated URLs and files | XdgExecutor class; URL validation | arbitrary command execution |
| `app/policy/broker.py` | PH050 | — | Interactive approval broker, cryptographic hash binding, and popup dispatch | ApprovalBroker class; ApprovalGrant; popup spawning | persistent grant storage; multi-use grants |
| `app/ai/nvidia.py` | PH060 | — | NVIDIA Nemotron AsyncOpenAI client adapter with streaming and tool parsing | NvidiaProvider class; ChatMessage; ToolCall parsing | direct OS execution; leaking raw reasoning traces |
| `app/core/command_router.py` | PH070 | — | 4-tier command classification and routing pipeline | CommandRouter class; CommandRoutingDecision | direct executor calls bypassing dispatcher |
| `app/agents/runtime.py` | PH070 | — | Bounded single logical agent execution loop with step limits | AgentRuntime class; step loop; transcript management | parallel unconstrained swarms; policy bypass |
| `app/agents/model.py` | PH070 | — | Agent task and step Pydantic data schemas | AgentTask; AgentTaskResult; AgentStep | runtime execution logic |
| `app/voice/audio.py` | PH080 | — | Audio stream capture and bounded circular ring buffer | AudioSource class; ring buffer reading/writing | network socket calls; disk writing of pre-wake audio |
| `app/voice/wake.py` | PH080 | — | Local wake word detection using openWakeWord 1-thread engine | WakeDetector class; frame inference | network transmission; remote STT calls |
| `app/voice/recorder.py` | PH080 | — | Post-wake command audio recording bounded by VAD and duration | CommandRecorder class; VAD silence detection | pre-wake buffer retention |
| `app/voice/stt.py` | PH090 | — | Remote STT adapter for post-wake command audio transcription | STTAdapter class; audio buffer release logic | pre-wake audio transcription; disk persistence of audio |
| `app/tray/status_notifier.py` | PH100 | — | Freedesktop StatusNotifierItem over session D-Bus | StatusNotifierTray class; D-Bus property updates | heavyweight GUI window creation |
| `app/browser/native_bridge.py` | PH110 | — | Length-prefixed native messaging host communicating with Firefox | NativeMessageBridge class; message framing; domain checks | unrestricted DOM access; bypassing domain allowlist |
| `extension/firefox/manifest.json` | PH110 | — | Firefox WebExtension manifest declaring permissions and native messaging host | manifest metadata; permissions declarations | broad wildcard permissions without user prompt |
| `extension/firefox/background.js` | PH110 | PH120 | Extension background service worker connecting native messaging pipe to content scripts | browser.runtime.connectNative; tab routing | direct remote script evaluation |
| `extension/firefox/native.js` | PH110 | — | Native messaging framing and tab origin validation routines | verifyTabOrigin function; message dispatch | origin mismatch execution |
| `extension/firefox/generic.js` | PH110 | — | Generic DOM text extraction excluding passwords and sensitive elements | extractVisibleText function; sensitive field filters | reading password inputs; scraping cookies |
| `extension/firefox/adapters/base.js` | PH120 | — | Base site adapter interface and graceful outdated DOM failure handler | BaseAdapter class; handle_outdated_dom | silent failure; arbitrary selector injection |
| `extension/firefox/adapters/google.js` | PH120 | — | Dedicated semantic adapter for Google Search result extraction | GoogleAdapter class; result parsing | ad clicking; capturing user cookies |
| `extension/firefox/adapters/amazon.js` | PH120 | — | Dedicated semantic adapter for Amazon product search results | AmazonAdapter class; product title/price extraction | automatic checkout; one-click purchase |
| `extension/firefox/adapters/chatgpt.js` | PH120 | — | Dedicated semantic adapter for ChatGPT interface response extraction | ChatGPTAdapter class; response turn extraction | account settings modification |
| `extension/firefox/adapters/claude.js` | PH120 | — | Dedicated semantic adapter for Claude.ai response extraction | ClaudeAdapter class; response turn extraction | account settings modification |
| `extension/firefox/adapters/gemini.js` | PH120 | — | Dedicated semantic adapter for Gemini web interface response extraction | GeminiAdapter class; response turn extraction | account settings modification |
| `app/api/app.py` | PH130 | — | FastAPI localhost application factory and lifespan management | create_dashboard_app function; route mounting | wildcard CORS; binding to 0.0.0.0 |
| `app/api/routes_config.py` | PH130 | — | Configuration CRUD endpoints with strict validation | config GET/POST/PUT endpoints | unvalidated config overwrites |
| `app/api/routes_audit.py` | PH130 | — | Paginated audit event log query endpoints | audit log GET endpoints with limit/offset | unbounded log dumps |
| `app/storage/sqlite.py` | PH130 | — | Local SQLite storage layer with WAL mode and connection pooling | SQLiteStorage class; schema migration; audit inserts | storing plaintext secrets/API keys |
| `app/web/index.html` | PH140 | — | Single-page static dashboard HTML shell | semantic HTML structure; tab views; SVG AI Core markup | inline javascript; CDN script tags |
| `app/web/css/app.css` | PH140 | — | Custom CSS layout and AI Core pulse animations | CSS styling; reduced motion media queries | remote @import rules |
| `app/web/js/app.js` | PH140 | — | Vanilla JavaScript dashboard state controller and SSE consumer | EventSource listener; DOM updates; fetch calls | Node dependencies; frontend build steps |
| `app/executors/developer.py` | PH150 | — | Developer workflows: git status/diff, test runner, code CLI launcher | DeveloperToolExecutor class; git/test helpers | auto-commit without verification |
| `app/lifecycle.py` | PH050 | PH100, PH160 | Daemon lifecycle manager, composition root, and graceful shutdown coordinator | LifecycleManager class; monitor_memory function | raising MemoryMax limit |
| `packaging/systemd/maya.service` | PH170 | — | User systemd unit definition with cgroup resource limits | systemd unit file; MemoryHigh=240M; MemoryMax=300M | root service installation |
| `packaging/native-manifest/project_h_firefox.json` | PH170 | — | Firefox native messaging host registration manifest | native messaging host path; allowed_extensions | executable scripts directly |
| `tests/test_offline_determinism.py` | PH180 | — | End-to-end verification of deterministic actions when remote AI is offline | test_offline_deterministic_actions_succeed test case | live API network calls |
| `app/browser/protocol.py` | PH040 | PH110 | BrowserBridge protocol definition and runtime_checkable interface | BrowserBridge protocol definition; execute signature | direct socket connections; subprocess spawns |
| `tests/test_approval_broker.py` | PH050 | — | Unit and security test suite for ApprovalBroker and grant validation | ApprovalBroker unit/security tests; timeout assertions; mock popup | production code; network calls |
| `tests/fakes/fake_popup.py` | PH050 | — | Test fake simulating interactive native approval popup | FakePopup class; canned responses (APPROVE/DENY/TIMEOUT) | real GUI windows; subprocess execution |
| `tests/test_nvidia_provider.py` | PH060 | — | Unit and security test suite for NvidiaProvider and AsyncOpenAI streaming | NvidiaProvider tests; mock AsyncOpenAI client; tool call validation | real network requests to external API endpoints |
| `tests/fakes/fake_nvidia.py` | PH060 | — | Test fake simulating OpenAI-compatible streaming API responses | FakeOpenAIClient; chunk streaming; canned tool calls | real network calls |
| `tests/test_command_router.py` | PH070 | — | Unit tests for CommandRouter 4-tier routing and classification | CommandRouter tests; exact phrase matching; tier precedence checks | subprocess executions; live LLM calls |
| `tests/test_agent_runtime.py` | PH070 | — | Integration and bounds test suite for AgentRuntime step loop | AgentRuntime tests; step limits; tool execution assertions | unbounded loops; direct OS access bypassing ActionDispatcher |
| `tests/test_voice_wake.py` | PH080 | — | Unit and privacy test suite for AudioSource and WakeDetector | AudioSource tests; ring buffer bounds; mock openWakeWord; privacy asserts | network requests; disk audio persistence |
| `tests/fakes/fake_voice.py` | PH080 | — | Test fake simulating audio streams and wake word detections | FakeAudioSource; synthetic PCM frames | real soundcard capture; microphone access |
| `tests/test_stt_adapter.py` | PH090 | — | Unit and security test suite for NVIDIA STT adapter and buffer release | STTAdapter tests; ephemeral buffer release assertions; error handling | pre-wake audio transmission; persistent audio files |
| `tests/fakes/fake_stt.py` | PH090 | — | Test fake simulating remote STT transcription responses | FakeSTTAdapter; canned transcriptions; simulated network errors | live network calls |
| `tests/test_tray.py` | PH100 | — | Unit tests for StatusNotifierItem tray and state transitions | StatusNotifierTray tests; property export assertions; signal emission | heavyweight X11/Wayland window creation |
| `tests/fakes/fake_dbus.py` | PH100 | — | Test fake simulating D-Bus connection and StatusNotifierWatcher | FakeDBusBus; mock object registration; signal capture | real system bus operations |
| `tests/test_browser_bridge.py` | PH110 | — | Unit and security test suite for Firefox Native Message bridge | NativeMessageBridge tests; 1MB framing limit; tab origin security tests | live browser process spawning |
| `tests/fakes/fake_browser.py` | PH110 | — | Test fake simulating browser extension native messaging pipe | FakeExtensionPipe; canned DOM responses; origin headers | live network/browser calls |
| `tests/test_site_adapters.py` | PH120 | — | Unit tests for semantic site adapters and selector degradation | Site adapter DOM parsing tests; ADAPTER_OUTDATED assertions | live web scraping; network calls |
| `tests/test_dashboard_api.py` | PH130 | — | Unit and security test suite for FastAPI dashboard and SQLite storage | FastAPI TestClient requests; same-origin tests; CRUD validation | non-localhost network binding |
| `tests/test_dashboard_frontend.py` | PH140 | — | Unit tests for static web assets, CSS compliance, and JS event handlers | HTML/CSS structure tests; accessibility/reduced-motion assertions | external CDN dependencies; Node build pipelines |
| `tests/test_developer_workflows.py` | PH150 | — | Integration tests for git status, diff, test execution, and code edit tools | DeveloperToolExecutor tests; temp git repo isolation; policy gates | production repository modifications; auto-commit without policy |
| `tests/test_resource_hardening.py` | PH160 | — | Stress and memory boundary test suite for cgroup compliance | Bounded structure tests; memory monitoring assertions; stress runs | modifying cgroup limits; raising MemoryMax |
| `packaging/install.sh` | PH170 | — | User installation script for Maya daemon and browser manifests | systemctl --user commands; manifest symlinks; permission checks | sudo/root execution; system-wide directory modifications |
| `packaging/uninstall.sh` | PH170 | — | Clean uninstallation script for Maya user service and artifacts | systemctl --user stop/disable; manifest removal; user state cleanup | sudo/root execution; deleting arbitrary user files |
| `tests/test_packaging.py` | PH170 | — | Packaging and installation verification test suite | Manifest syntax validation; service file parsing; permission checks | executing system-wide modifications |
| `Docs/Current/PH180_FINAL_ACCEPTANCE_REPORT.md` | PH180 | — | Final V1 acceptance and verification report | Verification results; requirement mapping table; test run outputs | unverified claims; modifying production requirements |
| `app/actions/matcher.py` | PH030 | — | Template matching and regex phrase slot extraction | PhraseMatcher class; regex compilation; slot extraction | arbitrary execution; file modification |
| `app/actions/schema.py` | PH030 | — | Action pack Pydantic schemas and models | ActionPack; ActionDefinition; ArgumentDefinition | runtime execution; state mutation |
| `app/core/events.py` | PH000 | — | Application event types and bus definitions | Event; EventType enum; EventBus | blocking I/O; subprocess calls |
| `app/executors/base.py` | PH040 | PH050 | Base abstract interface for action executors | BaseExecutor abstract class; execute abstractmethod | direct process execution |
| `app/main.py` | PH000 | PH170 | Daemon CLI entrypoint and signal handling | main function; CLI argument parsing; daemon bootstrap | business logic; unbounded execution |
| `app/policy/approvals.py` | PH020 | — | Approval rule definitions and classification | ApprovalRequirement; ApprovalType enum | persistent state |
| `app/policy/paths.py` | PH020 | — | Path policy evaluation and sandboxing helper | validate_path; is_within_allowed_roots | direct filesystem mutations |
| `app/policy/risk.py` | PH020 | — | Risk assessment schemas and risk level classifications | RiskLevel enum; RiskAssessment model | subprocess calls |
| `pyproject.toml` | PH000 | PH060, PH080, PH090, PH100, PH130 | Python project metadata, dependencies, and build configuration | project dependencies; optional-dependencies; scripts table | unpinned non-standard build backends |
| `app/ai/base.py` | PH060 | — | AI provider protocol and model interaction base definitions | AIProvider Protocol; ProviderResponse; Message models | Nvidia SDK imports; live API network calls |
| `app/api/routes_state.py` | PH130 | — | Dashboard routes_state.py API endpoint implementation | FastAPI route handlers; Pydantic models | direct SQL execution bypassing storage; wildcard CORS |
| `app/api/routes_actions.py` | PH130 | — | Dashboard routes_actions.py API endpoint implementation | FastAPI route handlers; Pydantic models | direct SQL execution bypassing storage; wildcard CORS |
| `app/api/routes_agents.py` | PH130 | — | Dashboard routes_agents.py API endpoint implementation | FastAPI route handlers; Pydantic models | direct SQL execution bypassing storage; wildcard CORS |
| `app/api/schemas.py` | PH130 | — | Dashboard schemas.py API endpoint implementation | FastAPI route handlers; Pydantic models | direct SQL execution bypassing storage; wildcard CORS |

---

## 2. Invariant Modification Rules

1. **Strict Ownership:** A phase implementation agent may only create files where `owner_phase == current_phase`, or modify files where `current_phase in secondary_modifiers`.
2. **Zero Modification of Unlisted Files:** Under no circumstances may a phase touch files not declared in its `files_created` or `files_modified` manifest.
3. **Dependency Modifiers:** Phases adding runtime dependencies (PH060, PH080, PH090, PH100, PH130) modify `pyproject.toml` per their secondary modifier declaration.
4. **Zero Production Changes During Cookbook Freeze:** During cookbook generation/repair, `git diff origin/main...HEAD -- app/` must remain strictly empty.
