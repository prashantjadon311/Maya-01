# Maya End-to-End Architectural Journeys (Forward Simulation)

Every critical user workflow through Maya is traced herein across actual declared symbols, interfaces, and automated test recipes.

---

## Journey 1: Deterministic Local Command Execution
*Scenario: User issues exact command "open terminal" via text CLI or voice.*

```text
User text/audio ("open terminal")
  ➔ InputGateway.handle_text_command() (app/core/gateway.py)
  ➔ CommandRouter.route() (app/core/command_router.py)
  ➔ ActionRegistry.find_exact_match() [Confidence = 1.0] (app/actions/registry.py)
  ➔ ActionRequest constructed: {"action_id": "core.open_terminal"}
  ➔ ActionDispatcher.dispatch_action_request() (app/core/dispatcher.py)
  ➔ PolicyEngine.evaluate() [Pre-approved ➔ ALLOW] (app/policy/engine.py)
  ➔ ProcessExecutor.execute(["gnome-terminal"]) (app/executors/process.py)
  ➔ SQLiteStorage.record_audit_event() (app/storage/sqlite.py)
  ➔ Result returned to user: SUCCESS (Zero external AI calls made)
```
- **Test:** `test_exact_action_zero_ai_calls`

---

## Journey 2: Sensitive AI Proposed Action with Interactive Approval
*Scenario: Model proposes deleting temporary build directory (`rm -rf /home/user/tmp`).*

```text
User prompt ("clean build directory")
  ➔ CommandRouter.route() ➔ NvidiaProvider.complete() (app/ai/nvidia.py)
  ➔ Model returns ToolCall: "file.delete", path="/home/user/tmp"
  ➔ AgentRuntime.dispatch_tool() (app/agents/runtime.py)
  ➔ ActionDispatcher.dispatch_action_request() (app/core/dispatcher.py)
  ➔ PolicyEngine.evaluate() [Destructive action ➔ PolicyDecision.ASK_USER]
  ➔ ApprovalBroker.request_approval() (app/policy/broker.py)
      - Computes action_hash = SHA-256(canonical_json(req))
      - Registers grant_id in memory (status=PENDING, 60s timeout)
      - Spawns transient Native Approval Popup
  ➔ User inspects dialog on Ubuntu desktop, clicks "Allow Once"
  ➔ ApprovalBroker issues grant confirmation
  ➔ ActionDispatcher verifies grant:
      - ApprovalBroker.verify_grant(grant_id, action_hash) [MATCH]
      - ApprovalBroker.consume_grant(grant_id, action_hash) [ATOMICALLY DELETED]
  ➔ FileExecutor.delete("/home/user/tmp") (app/executors/files.py)
  ➔ SQLiteStorage.record_audit_event("SEC-APPR-CONSUMED") (app/storage/sqlite.py)
```
- **Tests:** `test_approval_popup_transient_display`, `test_approval_single_use_replay_denied`

---

## Journey 3: Autonomous Coding Agent Loop
*Scenario: User requests "Fix broken test in repo /home/user/Projects/Demo".*

```text
User prompt ➔ CommandRouter ➔ AgentRuntime.run_task() (app/agents/runtime.py)
  ➔ AgentRuntime acquires single active task lock
  ➔ Step 1: Query Git status ➔ ActionDispatcher ➔ DeveloperToolExecutor.git_status()
  ➔ Step 2: Read test file ➔ ActionDispatcher ➔ FileExecutor.read()
  ➔ Step 3: Propose code edit ➔ ActionDispatcher ➔ PolicyEngine (Medium Risk) ➔ FileExecutor.write()
  ➔ Step 4: Run tests ➔ ActionDispatcher ➔ DeveloperToolExecutor.run_tests(["pytest"])
  ➔ Step 5: Tests pass ➔ Model produces final answer with evidence
  ➔ AgentRuntime halts (Step count = 5 <= 15 limit)
  ➔ Lock released, final summary returned to user
```
- **Tests:** `test_agent_budget_and_step_limit_enforced`, `test_agent_cannot_bypass_policy_dispatcher`

---

## Journey 4: Always-Listening Voice Pipeline
*Scenario: Assistant listens in background, wakes on "Maya", and transcribes command.*

```text
Microphone Audio Stream (16kHz 16-bit mono)
  ➔ AudioSource.write_frames() [Bounded 3.0s circular RAM ring buffer]
  ➔ WakeDetector.process_chunk() [openWakeWord 1 CPU thread, zero network calls]
  ➔ Wake detected (confidence >= 0.70)
  ➔ AppState transitions: READY_WAKE ➔ WAKE_DETECTED ➔ RECORDING
  ➔ CommandRecorder records incoming command audio until VAD detects 1.2s silence
  ➔ AppState transitions: RECORDING ➔ TRANSCRIBING
  ➔ STTAdapter.transcribe() [Sends post-wake audio segment to NVIDIA Parakeet ASR]
  ➔ Audio PCM buffer explicitly freed from RAM via del & gc
  ➔ Transcript returned: "open browser"
  ➔ CommandRouter.route("open browser") ➔ Dispatcher executes command
  ➔ AppState transitions: EXECUTING ➔ READY_WAKE
```
- **Tests:** `test_prewake_audio_zero_network_callback`, `test_stt_transcribes_postwake_only`

---

## Journey 5: Browser Automation via Native Messaging
*Scenario: User asks assistant to search Google for "Ubuntu 24.04 release notes".*

```text
User command ➔ CommandRouter ➔ ActionDispatcher
  ➔ NativeMessageBridge.verify_domain_permission("https://google.com") [ALLOWLISTED]
  ➔ NativeMessageBridge.send_command(BrowserCommand(target_url="https://google.com", command_type="READ"))
  ➔ 4-byte length prefix + JSON payload written to Firefox native messaging pipe
  ➔ Firefox background.js receives message, forwards to tab content script
  ➔ Content script native.js executes verifyTabOrigin() [Asserts origin === "https://www.google.com"]
  ➔ GoogleAdapter.extract() parses top 5 search results from semantic DOM elements
  ➔ Passwords and auth tokens filtered out by generic filter
  ➔ JSON response returned through native pipe to NativeMessageBridge
  ➔ Structured search titles and snippets displayed on dashboard / spoken
```
- **Tests:** `test_browser_unlisted_domain_denied`, `test_browser_origin_mismatch_denied`

---

## Journey 6: Daemon Restart During Pending Approval
*Scenario: System reboot occurs while user has an unhandled approval dialog open.*

```text
Approval pending in memory (grant_id="abc-123", status=PENDING)
  ➔ Host reboots or daemon terminates unexpectedly
  ➔ Systemd starts fresh project-hd instance
  ➔ Composition root initializes ApprovalBroker with empty RAM dictionary
  ➔ Malicious process attempts to replay grant "abc-123":
      - ApprovalBroker.verify_grant("abc-123", hash) ➔ returns False
  ➔ Action is strictly denied; zero unauthorized post-reboot execution
```
- **Test:** `test_daemon_restart_clears_pending_approvals`

---

## Journey 7: NVIDIA Outage & Offline Determinism
*Scenario: Internet connection is severed or NVIDIA API returns HTTP 503.*

```text
Outbound internet offline / cable unplugged
  ➔ User issues command: "open terminal"
  ➔ CommandRouter.route() resolves to Tier 1 exact match in local action registry
  ➔ ActionDispatcher executes ProcessExecutor(["gnome-terminal"])
  ➔ Terminal opens instantly; zero network latency, zero error
  ➔ User issues command: "explain quantum physics"
  ➔ CommandRouter routes to Tier 4 AI Reasoning
  ➔ NvidiaProvider catches ConnectError / Timeout
  ➔ Returns clean user notification: "AI reasoning is temporarily offline; local actions remain active."
  ➔ Daemon continues running normally without hanging or crashing
```
- **Test:** `test_offline_deterministic_actions_succeed`

---

## Journey 8: Dashboard Configuration Update & Transactional Reload
*Scenario: User modifies preapproved commands in settings tab of local web dashboard.*

```text
User modifies config on http://127.0.0.1:8765/settings
  ➔ Web UI sends PUT /api/v1/config to FastAPI localhost server
  ➔ AppConfig.model_validate(payload) strictly verifies types and forbidden keys
  ➔ Config written atomically via temporary file and atomic rename
  ➔ ConfigStore triggers transactional reload:
      - PolicyEngine reloads rules snapshot
      - ActionRegistry validates packs
  ➔ SQLiteStorage logs audit event "CONFIG_UPDATE"
  ➔ HTTP 200 OK returned; new policy takes effect immediately without daemon restart
```
- **Test:** `test_dashboard_config_crud_transactionality`
