# Maya Atomic Requirements Ledger

Every requirement in this ledger is derived from the Project H authority hierarchy (`Docs/DOCS.md` > `SECURITY.md` > `ARCHITECTURE.md` > `CONFIG.md` > `UI.md` > `PLAN.md` > `TASKS.md` > `EXECUTION.md`).

Every requirement has an immutable, unique identifier and maps to:
`Requirement ID → Owning Phase → Component → Target File → Symbol → Test ID → Acceptance Evidence`

---

## 1. Master Requirements Matrix

| ID | Cat | Source | Phase | Component | File | Symbol | Test ID | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `REQ-CORE-001` | core | `DOCS.md` | PH000 | core | `app/core/state.py` | `AppState` | `test_app_state_interface` | Python package skeleton with async loop and strict types |
| `REQ-CFG-001` | config | `CONFIG.md` | PH010 | config | `app/core/config.py` | `AppConfig` | `test_command_request_unknown_field_rejected` | Config schema validation rejecting unknown keys |
| `REQ-POL-001` | policy | `SECURITY.md` | PH020 | policy | `app/policy/engine.py` | `PolicyEngine.evaluate` | `test_policy_engine_allow_ask_deny` | Deterministic policy: ALLOW, ASK_USER, DENY |
| `REQ-POL-002` | policy | `SECURITY.md` | PH020 | policy | `app/policy/risk.py` | `RiskClassifier.classify` | `test_action_definition_high_preapproved_rejected` | High-risk actions cannot be silently preapproved |
| `REQ-REG-001` | registry | `DOCS.md` | PH030 | registry | `app/actions/registry.py` | `ActionRegistry.load_pack` | `test_symlinked_pack_rejected` | Action pack loading rejecting symlinks and duplicate IDs |
| `REQ-REG-002` | registry | `DOCS.md` | PH030 | registry | `app/actions/matcher.py` | `substitute_arguments` | `test_strict_argument_substitution` | Deterministic phrase matching with strict slot substitution |
| `REQ-EXEC-001` | processes | `SECURITY.md` | PH040 | executors | `app/executors/process.py` | `ProcessExecutor.execute` | `test_process_executor_argv_only` | Subprocess argv array only, no shell, 64KB bounded output |
| `REQ-EXEC-002` | files | `SECURITY.md` | PH040 | executors | `app/executors/files.py` | `FileExecutor.read` | `test_file_executor_root_boundary` | File canonical path check, root containment, symlink prevention |
| `REQ-APPR-001` | approval | `SECURITY.md` | PH050 | approval_broker | `app/policy/broker.py` | `ApprovalBroker.request_approval` | `test_approval_popup_transient_display` | Native popup outside web dashboard for sensitive actions |
| `REQ-APPR-002` | approval | `SECURITY.md` | PH050 | approval_broker | `app/policy/broker.py` | `ApprovalBroker.verify_grant` | `test_approval_hash_mismatch_denied` | Approval token cryptographically bound to action hash |
| `REQ-APPR-003` | approval | `SECURITY.md` | PH050 | approval_broker | `app/policy/broker.py` | `ApprovalBroker.consume_grant` | `test_approval_single_use_replay_denied` | Approval token is single-use and consumed upon verification |
| `REQ-APPR-004` | approval | `SECURITY.md` | PH050 | approval_broker | `app/policy/broker.py` | `ApprovalBroker.wait_for_decision` | `test_approval_timeout_denies` | Approval request expires after timeout, failing closed to DENY |
| `REQ-APPR-005` | approval | `SECURITY.md` | PH050 | approval_broker | `app/policy/broker.py` | `ApprovalBroker.reset` | `test_daemon_restart_clears_pending_approvals` | Daemon restart immediately invalidates pending approvals |
| `REQ-PROV-001` | provider | `DOCS.md` | PH060 | ai_provider | `app/ai/nvidia.py` | `NvidiaProvider.create_client` | `test_nvidia_client_configuration` | Reusable AsyncOpenAI client for NVIDIA endpoint |
| `REQ-PROV-002` | provider | `DOCS.md` | PH060 | ai_provider | `app/ai/nvidia.py` | `NvidiaProvider.complete` | `test_nvidia_zero_sdk_retries` | SDK retries disabled (max_retries=0), explicit timeouts |
| `REQ-PROV-003` | provider | `DOCS.md` | PH060 | ai_provider | `app/ai/nvidia.py` | `NvidiaProvider.stream_chat` | `test_nvidia_streaming_tool_call_parsing` | Streaming completion with incremental tool argument parsing |
| `REQ-PROV-004` | provider | `DOCS.md` | PH060 | ai_provider | `app/ai/nvidia.py` | `NvidiaProvider.filter_reasoning` | `test_reasoning_trace_not_leaked` | Model reasoning traces filtered from public return/logging |
| `REQ-PROV-005` | provider | `DOCS.md` | PH060 | ai_provider | `tests/fakes/fake_nvidia.py` | `FakeNvidiaTransport` | `test_provider_tests_offline_no_quota` | Default test suite uses fakes, no live quota consumption |
| `REQ-ROUT-001` | router | `DOCS.md` | PH070 | command_router | `app/core/command_router.py` | `CommandRouter.route` | `test_command_router_order_of_precedence` | Order: exact match -> built-ins -> structured -> AI reasoning |
| `REQ-ROUT-002` | router | `DOCS.md` | PH070 | command_router | `app/core/command_router.py` | `CommandRouter.route` | `test_exact_action_zero_ai_calls` | Exact local action produces zero external AI provider calls |
| `REQ-AGNT-001` | agent | `DOCS.md` | PH070 | agent_runtime | `app/agents/runtime.py` | `AgentRuntime.run_task` | `test_agent_budget_and_step_limit_enforced` | Single active agent task with bounded steps and budget |
| `REQ-AGNT-002` | agent | `SECURITY.md` | PH070 | agent_runtime | `app/agents/runtime.py` | `AgentRuntime.dispatch_tool` | `test_agent_cannot_bypass_policy_dispatcher` | Agent tool proposals routed through ActionDispatcher & policy |
| `REQ-VOIC-001` | voice | `SECURITY.md` | PH080 | voice_wake | `app/voice/wake.py` | `WakeDetector.process_chunk` | `test_prewake_audio_zero_network_callback` | Pre-wake audio memory-only in local ring, zero network |
| `REQ-VOIC-002` | voice | `DOCS.md` | PH080 | voice_wake | `app/voice/audio.py` | `AudioSource.read_frames` | `test_audio_ring_buffer_hard_bound` | openWakeWord 1 thread, bounded ring buffer in RAM |
| `REQ-VOIC-003` | voice | `DOCS.md` | PH080 | voice_wake | `app/voice/recorder.py` | `CommandRecorder.record_command` | `test_command_recording_vad_stop` | Recording starts post-wake, terminates by VAD or timeout |
| `REQ-STT-001` | stt | `DOCS.md` | PH090 | stt | `app/voice/stt.py` | `STTAdapter.transcribe` | `test_stt_transcribes_postwake_only` | NVIDIA multilingual STT called only for post-wake audio |
| `REQ-STT-002` | stt | `DOCS.md` | PH090 | stt | `app/voice/stt.py` | `STTAdapter.release_buffer` | `test_audio_buffer_released_after_stt` | Audio buffer released from memory immediately post-STT |
| `REQ-STT-003` | stt | `DOCS.md` | PH090 | stt | `app/voice/stt.py` | `STTAdapter.handle_error` | `test_stt_failure_prevents_execution` | STT failure fails closed, zero downstream execution |
| `REQ-TRAY-001` | tray | `DOCS.md` | PH100 | tray | `app/tray/status_notifier.py` | `StatusNotifierTray.register` | `test_tray_dbus_registration` | Freedesktop StatusNotifierItem via D-Bus, no GUI window |
| `REQ-TRAY-002` | tray | `DOCS.md` | PH100 | tray | `app/tray/status_notifier.py` | `StatusNotifierTray.update_state` | `test_tray_menu_actions_and_state_sync` | Tray syncs core state; Push-to-Talk, Listen, Dashboard, Quit |
| `REQ-BROW-001` | browser | `SECURITY.md` | PH110 | browser_bridge | `app/browser/native_bridge.py` | `NativeMessageBridge.receive_message` | `test_native_messaging_framing_and_size_limit` | Firefox Native Messaging host with length-prefixed protocol |
| `REQ-BROW-002` | browser | `SECURITY.md` | PH110 | browser_bridge | `app/browser/native_bridge.py` | `NativeMessageBridge.verify_domain_permission` | `test_browser_unlisted_domain_denied` | Double gate: daemon domain allowlist + browser host permission |
| `REQ-BROW-003` | browser | `SECURITY.md` | PH110 | browser_bridge | `extension/firefox/native.js` | `verifyTabOrigin` | `test_browser_origin_mismatch_denied` | Content script checks location.origin immediately before action |
| `REQ-BROW-004` | browser | `SECURITY.md` | PH110 | browser_bridge | `extension/firefox/generic.js` | `extractVisibleText` | `test_password_and_secret_fields_not_extracted` | Passwords, credentials, and cookies excluded from extraction |
| `REQ-ADPT-001` | browser | `DOCS.md` | PH120 | browser_adapters | `extension/firefox/adapters/google.js` | `GoogleAdapter.extract` | `test_site_adapters_semantic_extraction` | Semantic adapters for Google, Amazon, ChatGPT, Claude, Gemini |
| `REQ-ADPT-002` | browser | `DOCS.md` | PH120 | browser_adapters | `extension/firefox/adapters/base.js` | `BaseAdapter.handle_outdated_dom` | `test_outdated_adapter_fails_safely` | Outdated DOM handled safely without granting arbitrary access |
| `REQ-DASH-001` | dashboard | `DOCS.md` | PH130 | dashboard_api | `app/api/app.py` | `create_dashboard_app` | `test_dashboard_cors_and_localhost_binding` | FastAPI 127.0.0.1 localhost only, same-origin, no wildcards |
| `REQ-DASH-002` | dashboard | `DOCS.md` | PH130 | dashboard_api | `app/api/routes_config.py` | `update_config_endpoint` | `test_dashboard_config_crud_transactionality` | Transactional config CRUD and paginated audit log queries |
| `REQ-DASH-003` | dashboard | `UI.md` | PH140 | dashboard_ui | `app/web/index.html` | `MayaDashboardUI` | `test_frontend_assets_local_and_no_node_runtime` | Vanilla JS, local Bootstrap 5.3 CSS, SVG AI Core, zero Node |
| `REQ-DEV-001` | developer | `DOCS.md` | PH150 | developer_tools | `app/executors/developer.py` | `DeveloperToolExecutor.run_workflow` | `test_dev_workflow_git_and_test_under_policy` | Repo registration, git diff, test runner, code CLI open |
| `REQ-DEV-002` | developer | `DOCS.md` | PH150 | developer_tools | `app/executors/developer.py` | `DeveloperToolExecutor.verify_before_commit` | `test_auto_commit_disabled_by_default` | Edits require verification loop; auto-commit disabled by default |
| `REQ-RES-001` | memory | `DOCS.md` | PH160 | resource_monitor | `app/core/lifecycle.py` | `LifecycleManager.monitor_memory` | `test_resident_cgroup_memory_stress_compliance` | Resident cgroup <= 300 MiB under full stress scenario |
| `REQ-PKG-001` | packaging | `DOCS.md` | PH170 | packaging | `packaging/systemd/maya.service` | `maya.service` | `test_systemd_service_unit_configuration` | User systemd unit with MemoryHigh=240M, MemoryMax=300M |
| `REQ-ACCP-001` | acceptance | `DOCS.md` | PH180 | core | `tests/test_offline_determinism.py` | `test_offline_deterministic_actions_succeed` | `test_offline_deterministic_actions_succeed` | Deterministic local actions work when NVIDIA unavailable |
