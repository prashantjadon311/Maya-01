# Maya Atomic Requirements Ledger

Every requirement in this ledger is derived from the Project H authority hierarchy (`Docs/DOCS.md` > `SECURITY.md` > `ARCHITECTURE.md` > `CONFIG.md` > `UI.md` > `PLAN.md` > `TASKS.md` > `EXECUTION.md`).

Every requirement has an immutable, unique identifier and maps to:
`Requirement ID -> Owning Phase -> Component -> Target File -> Symbol -> Test ID -> Acceptance Evidence`

---

## 1. Master Requirements Matrix (160 Requirements)

| ID | Cat | Source | Phase | Component | File | Symbol | Test ID | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `REQ-PLAN-PH000-001` | core | `Docs/PLAN.md` | PH000 | harness | `tests/test_harness.py` | `test_baseline_process_rss` | `test_baseline_process_rss` | Package skeleton and baseline process RSS measurement harness |
| `REQ-ARCH-SYS-001` | core | `Docs/ARCHITECTURE.md` | PH000 | daemon | `app/main.py` | `Daemon` | `test_daemon_lifecycle` | Modular system architecture with decoupled subsystem boundaries |
| `REQ-ARCH-PROC-001` | core | `Docs/ARCHITECTURE.md` | PH000 | harness | `tests/test_harness.py` | `test_no_credentials_required` | `test_no_credentials_required` | Process execution separation between resident daemon and transient helpers |
| `REQ-ARCH-PROC-RES-001` | core | `Docs/ARCHITECTURE.md` | PH000 | state | `app/core/state.py` | `AppState` | `test_app_state_interface` | Single resident daemon lifecycle and state management |
| `REQ-ARCH-PROC-TRN-001` | core | `Docs/ARCHITECTURE.md` | PH000 | state | `app/core/state.py` | `AppState` | `test_architecture_states` | Transient helper processes adhere to architected status literals |
| `REQ-ARCH-DEP-001` | core | `Docs/ARCHITECTURE.md` | PH000 | state | `app/core/state.py` | `AppState` | `test_state_rejects_unknown_updates` | Acyclic architecture layers reject unknown state updates |
| `REQ-EXEC-RUN-001` | core | `Docs/EXECUTION.md` | PH000 | harness | `tests/test_harness.py` | `test_config_fixture_exists` | `test_config_fixture_exists` | First run configuration fixture validation |
| `REQ-EXEC-EXIST-001` | core | `Docs/EXECUTION.md` | PH000 | state | `app/core/state.py` | `AppState` | `test_state_rejects_coerced_boolean` | Preservation of existing codebase without type coercion defects |
| `REQ-CFG-001` | config | `Docs/CONFIG.md` | PH010 | config | `app/core/config.py` | `Config` | `test_command_request_unknown_field_rejected` | Strict Pydantic configuration schemas and command request validation |
| `REQ-CFG-LOC-001` | config | `Docs/CONFIG.md` | PH010 | config | `app/core/config.py` | `AssistantConfig` | `test_assistant_identity_is_nonempty_and_trimmed` | Assistant identity configuration nonempty and trimmed |
| `REQ-CFG-JSON-001` | config | `Docs/CONFIG.md` | PH010 | config | `app/core/config.py` | `Config` | `test_config_unknown_field_fails` | Strict JSON and TOML parsing rejecting extra forbidden keys |
| `REQ-PLAN-PH010-001` | config | `Docs/PLAN.md` | PH010 | config | `app/core/config.py` | `DashboardConfig` | `test_dashboard_is_ipv4_loopback_only` | Dashboard loopback binding and configuration network safety |
| `REQ-POL-001` | policy | `Docs/SECURITY.md` | PH020 | policy | `app/policy/engine.py` | `PolicyEngine.evaluate` | `test_policy_decision_enum_states` | Policy evaluation states: ALLOW_PREAPPROVED, ASK_USER, DENY |
| `REQ-POL-002` | policy | `Docs/SECURITY.md` | PH020 | policy | `app/actions/schema.py` | `ActionDefinition` | `test_action_definition_high_preapproved_rejected` | High-risk actions can never be preapproved or auto-executed |
| `REQ-POL-RISK-001` | policy | `Docs/SECURITY.md` | PH020 | policy | `app/policy/risk.py` | `classify_risk` | `test_malformed_argv_denied` | Risk classification rejects malformed argv and shell injections |
| `REQ-POL-RISK-LOW-001` | policy | `Docs/SECURITY.md` | PH020 | policy | `app/policy/risk.py` | `classify_risk` | `test_sensitive_defaults_cannot_be_overridden` | Low-risk preapproval cannot override sensitive system defaults |
| `REQ-POL-RISK-MED-001` | policy | `Docs/SECURITY.md` | PH020 | policy | `app/policy/paths.py` | `canonical_path` | `test_file_symlink_and_parent_escape` | File symlink and parent directory traversal escape prevention |
| `REQ-POL-ALWAYS-001` | policy | `Docs/DOCS.md` | PH020 | policy | `app/policy/risk.py` | `classify_risk` | `test_privilege_wrappers_require_approval` | Privilege wrappers like sudo strictly require interactive approval |
| `REQ-POL-DEV-001` | policy | `Docs/CONFIG.md` | PH020 | policy | `app/policy/engine.py` | `PreapprovalRule` | `test_preapproval_contract` | Developer preapproval rules require explicit executable and argv prefixes |
| `REQ-PLAN-PH020-001` | policy | `Docs/PLAN.md` | PH020 | policy | `app/policy/engine.py` | `PolicyEngine` | `test_destructive_executables_never_preapproved` | Destructive executables can never be preapproved |
| `REQ-REG-001` | registry | `Docs/DOCS.md` | PH030 | registry | `app/actions/registry.py` | `ActionRegistry.reload` | `test_symlinked_pack_rejected` | Action packs loaded from disk reject symlinks and path traversals |
| `REQ-REG-002` | registry | `Docs/DOCS.md` | PH030 | matcher | `app/actions/matcher.py` | `substitute_arguments` | `test_strict_argument_substitution` | Strict literal argument slot substitution without shell interpolation |
| `REQ-REG-AMBIG-001` | registry | `Docs/SECURITY.md` | PH030 | registry | `app/actions/registry.py` | `ActionRegistry.resolve` | `test_runtime_ambiguity_never_picks_an_action` | Runtime ambiguity fails closed and never picks an arbitrary action |
| `REQ-REG-PACK-001` | registry | `Docs/CONFIG.md` | PH030 | registry | `app/actions/registry.py` | `ActionRegistry.reload` | `test_max_pack_files_enforced` | Enforce hard bounds on action pack file count (max 64) |
| `REQ-PLAN-PH030-001` | registry | `Docs/PLAN.md` | PH030 | registry | `app/actions/registry.py` | `ActionRegistry.reload` | `test_max_total_actions_enforced` | Enforce total action limit across all packs (max 2048) |
| `REQ-EXEC-001` | executors | `Docs/DOCS.md` | PH040 | executors | `app/executors/process.py` | `ProcessExecutor.execute` | `test_process_args_strict_unknown_fields_and_validation` | Safe process execution with strict argv allowlists and bounded buffers |
| `REQ-EXEC-002` | executors | `Docs/DOCS.md` | PH040 | executors | `app/executors/files.py` | `FileExecutor.execute` | `test_resolve_trusted_executable_strict_v1` | Sandboxed file operations restricted to canonical configured roots |
| `REQ-PLAN-PH040-001` | executors | `Docs/PLAN.md` | PH040 | dispatcher | `app/core/dispatcher.py` | `ActionDispatcher` | `test_rule_risk_raises_trusted_risk` | Execution authorization provenance prevents rule risk lowering |
| `REQ-PLAN-PH040-PROC-001` | executors | `Docs/PLAN.md` | PH040 | executors | `app/executors/process.py` | `ProcessExecutor.execute` | `test_malformed_explicit_cwd_denied` | Process executor timeout and child escalation reaping |
| `REQ-PLAN-PH040-FILE-001` | executors | `Docs/PLAN.md` | PH040 | executors | `app/executors/files.py` | `FileExecutor.execute` | `test_file_operation_permissions` | File operation permissions and root containment enforcement |
| `REQ-PLAN-PH040-XDG-001` | executors | `Docs/PLAN.md` | PH040 | executors | `app/executors/xdg.py` | `XdgExecutor.execute` | `test_canonical_browser_capabilities_accepted` | Desktop launcher xdg-open restricted to validated URIs and apps |
| `REQ-APPR-001` | approval | `Docs/DOCS.md` | PH050 | broker | `app/policy/broker.py` | `ApprovalBroker.request_decision` | `test_approval_popup_transient_display` | Native modal approval popup displayed for ASK_USER decisions |
| `REQ-APPR-002` | approval | `Docs/DOCS.md` | PH050 | broker | `app/policy/broker.py` | `ApprovalBroker.consume_grant` | `test_approval_hash_mismatch_denied` | Single-use approval grant bound to canonical request payload hash |
| `REQ-APPR-003` | approval | `Docs/SECURITY.md` | PH050 | broker | `app/policy/broker.py` | `ApprovalBroker.consume_grant` | `test_approval_single_use_replay_denied` | Approval grant is strictly single-use; replay attempts fail |
| `REQ-PLAN-PH050-001` | approval | `Docs/PLAN.md` | PH050 | broker | `app/policy/broker.py` | `ApprovalBroker.request_decision` | `test_approval_timeout_denies` | Approval request timeout fails closed and mints zero grant |
| `REQ-EXEC-APPR-001` | approval | `Docs/EXECUTION.md` | PH050 | broker | `app/policy/broker.py` | `ApprovalBroker.reset` | `test_daemon_restart_clears_pending_approvals` | Daemon restart clears all pending grants and approval state |
| `REQ-PROV-001` | provider | `Docs/DOCS.md` | PH060 | provider | `app/ai/nvidia.py` | `NvidiaProvider` | `test_nvidia_client_configuration` | Reusable AsyncOpenAI client with max_retries=0 targeting Nemotron |
| `REQ-PROV-004` | provider | `Docs/SECURITY.md` | PH060 | provider | `app/ai/nvidia.py` | `NvidiaProvider.stream_chat` | `test_reasoning_trace_not_leaked` | Streaming reasoning trace sanitized statefully across chunk boundaries |
| `REQ-PROV-BASE-001` | provider | `Docs/ARCHITECTURE.md` | PH060 | provider | `app/ai/base.py` | `AIProvider` | `test_ai_provider_protocol_compliance` | AIProvider Protocol defined in app/ai/base.py decoupled from SDK |
| `REQ-PLAN-PH060-001` | provider | `Docs/PLAN.md` | PH060 | provider | `app/ai/nvidia.py` | `NvidiaProvider.complete` | `test_nvidia_zero_sdk_retries` | Zero automatic retries on side effects or after streamed chunks |
| `REQ-EXEC-NEMO-001` | provider | `Docs/EXECUTION.md` | PH060 | provider | `app/ai/nvidia.py` | `NvidiaProvider.stream_chat` | `test_nvidia_streaming_tool_call_parsing` | Incremental tool call parsing bounded by argument buffer size |
| `REQ-EXEC-API-001` | provider | `Docs/EXECUTION.md` | PH060 | provider | `tests/fakes/fake_nvidia.py` | `FakeOpenAIClient` | `test_provider_tests_offline_no_quota` | Test suite runs completely offline with zero hosted token consumption |
| `REQ-ROUT-001` | router | `Docs/DOCS.md` | PH070 | router | `app/core/command_router.py` | `CommandRouter.route` | `test_command_router_order_of_precedence` | Command router precedence: ActionRegistry -> Builtins -> AI Reasoning |
| `REQ-ROUT-002` | router | `Docs/DOCS.md` | PH070 | router | `app/core/command_router.py` | `CommandRouter.route` | `test_exact_action_zero_ai_calls` | Exact deterministic registered action incurs zero AI provider calls |
| `REQ-ROUT-AI-001` | router | `Docs/ARCHITECTURE.md` | PH070 | router | `app/core/command_router.py` | `CommandRouter.route` | `test_command_router_ai_fallback` | Ambiguous or freeform commands fallback to AI reasoning loop |
| `REQ-AGNT-001` | agents | `Docs/DOCS.md` | PH070 | agents | `app/agents/runtime.py` | `AgentRuntime.run_task` | `test_agent_budget_and_step_limit_enforced` | Single active agent loop bounded by step and API call limits |
| `REQ-AGNT-002` | agents | `Docs/SECURITY.md` | PH070 | agents | `app/agents/runtime.py` | `AgentRuntime.run_task` | `test_agent_cannot_bypass_policy_dispatcher` | Agent proposed tool calls route exclusively through ActionDispatcher |
| `REQ-AGNT-VERIFY-001` | agents | `Docs/PLAN.md` | PH070 | agents | `app/agents/runtime.py` | `AgentVerifier` | `test_agent_verification_step_enforced` | Coding agent tasks require explicit verification step before completion |
| `REQ-TOOL-SCHEMA-001` | agents | `Docs/ARCHITECTURE.md` | PH070 | agents | `app/agents/model.py` | `AgentTask` | `test_agent_tool_schema_validation` | Typed strict tool schema definitions exposed to AI model |
| `REQ-PLAN-PH070-001` | agents | `Docs/PLAN.md` | PH070 | agents | `app/agents/runtime.py` | `AgentRuntime.run_task` | `test_agent_runtime_single_task_lock` | Single active task lock prevents concurrent agent runs |
| `REQ-EXEC-AGENT-001` | agents | `Docs/EXECUTION.md` | PH070 | agents | `app/agents/model.py` | `AgentTaskResult` | `test_agent_task_lifecycle` | Single logical agent task lifecycle management |
| `REQ-VOIC-001` | voice | `Docs/DOCS.md` | PH080 | voice | `app/voice/audio.py` | `AudioSource` | `test_prewake_audio_zero_network_callback` | Zero audio transmitted over network prior to wake word detection |
| `REQ-VOIC-002` | voice | `Docs/DOCS.md` | PH080 | voice | `app/voice/audio.py` | `AudioRingBuffer` | `test_audio_ring_buffer_hard_bound` | Bounded audio ring buffer drops oldest frames enforcing RAM cap |
| `REQ-VOIC-PTT-001` | voice | `Docs/DOCS.md` | PH080 | voice | `app/voice/audio.py` | `AudioSource.start_ptt` | `test_push_to_talk_activation` | Push-to-talk keybind triggers audio capture without wake word |
| `REQ-VOIC-ALW-001` | voice | `Docs/DOCS.md` | PH080 | voice | `app/voice/wake.py` | `WakeDetector` | `test_always_listening_mode_toggle` | Always-listening mode toggle enables local wake detection loop |
| `REQ-VOIC-SM-001` | voice | `Docs/ARCHITECTURE.md` | PH080 | voice | `app/voice/recorder.py` | `CommandRecorder` | `test_voice_state_machine_transitions` | Voice pipeline coordinates state machine transitions |
| `REQ-VOIC-NO-STT-001` | voice | `Docs/PLAN.md` | PH080 | voice | `app/voice/wake.py` | `WakeDetector.process_chunk` | `test_no_stt_before_wake` | No speech-to-text calls permitted before wake word verified |
| `REQ-VOIC-POST-001` | voice | `Docs/PLAN.md` | PH080 | voice | `app/voice/recorder.py` | `CommandRecorder.start_command` | `test_command_segment_begins_after_wake` | Command audio segment begins strictly after wake boundary |
| `REQ-VOIC-CLOSE-001` | voice | `Docs/PLAN.md` | PH080 | voice | `app/voice/audio.py` | `AudioSource.stop` | `test_disabling_listen_closes_audio_stream` | Disabling listening closes audio capture stream immediately |
| `REQ-PLAN-PH080-001` | voice | `Docs/PLAN.md` | PH080 | voice | `app/voice/recorder.py` | `CommandRecorder.record_command` | `test_command_recording_vad_stop` | VAD silence detection stops command recording within configured duration |
| `REQ-STT-001` | stt | `Docs/DOCS.md` | PH090 | stt | `app/voice/stt.py` | `STTAdapter.transcribe` | `test_stt_transcribes_postwake_only` | Remote STT called exclusively for post-wake command segment |
| `REQ-PLAN-PH090-001` | stt | `Docs/PLAN.md` | PH090 | stt | `app/voice/stt.py` | `STTAdapter.transcribe` | `test_audio_buffer_released_after_stt` | Audio buffer released from memory immediately post-transcription |
| `REQ-TRAY-001` | tray | `Docs/DOCS.md` | PH100 | tray | `app/tray/status_notifier.py` | `StatusNotifierTray` | `test_tray_dbus_registration` | System tray indicator registered over D-Bus StatusNotifierItem |
| `REQ-TRAY-002` | tray | `Docs/DOCS.md` | PH100 | tray | `app/tray/status_notifier.py` | `StatusNotifierTray.update_state` | `test_tray_menu_actions_and_state_sync` | Tray menu actions dispatch controls and reflect live daemon state |
| `REQ-PLAN-PH100-001` | tray | `Docs/PLAN.md` | PH100 | tray | `app/tray/status_notifier.py` | `StatusNotifierTray` | `test_tray_injected_control_callbacks` | Tray receives injected control protocol without direct lifecycle coupling |
| `REQ-BROW-001` | browser | `Docs/DOCS.md` | PH110 | browser | `app/browser/native_bridge.py` | `NativeMessageBridge` | `test_native_messaging_framing_and_size_limit` | Resident daemon UDS bridge and transient Firefox Native Messaging host |
| `REQ-BROW-002` | browser | `Docs/DOCS.md` | PH110 | browser | `app/browser/native_bridge.py` | `NativeMessageBridge.send_command` | `test_browser_unlisted_domain_denied` | Browser automation restricted strictly to configured domain allowlist |
| `REQ-BROW-003` | browser | `Docs/SECURITY.md` | PH110 | browser | `extension/firefox/native.js` | `verifyTabOrigin` | `test_browser_origin_mismatch_denied` | Extension verifies immediate active tab origin re-check before dispatch |
| `REQ-BROW-004` | browser | `Docs/SECURITY.md` | PH110 | browser | `extension/firefox/generic.js` | `extractVisibleText` | `test_password_and_secret_fields_not_extracted` | Sensitive fields (passwords, tokens, cookies) never extracted from DOM |
| `REQ-BROW-PERM-001` | browser | `Docs/PLAN.md` | PH110 | browser | `extension/firefox/native.js` | `verifyHostPermission` | `test_browser_ungranted_host_permission_denied` | Commands targeting tabs without explicit host permission fail safely |
| `REQ-PLAN-PH110-001` | browser | `Docs/PLAN.md` | PH110 | browser | `app/browser/native_bridge.py` | `NativeMessageBridge` | `test_browser_bridge_uds_peercred_auth` | Local UDS bridge enforces mode 0600 and SO_PEERCRED UID validation |
| `REQ-EXEC-BROW-001` | browser | `Docs/EXECUTION.md` | PH110 | browser | `extension/firefox/manifest.json` | `manifest` | `test_browser_extension_message_validation` | WebExtension manifest specifies exact native messaging host permissions |
| `REQ-ADPT-001` | adapters | `Docs/DOCS.md` | PH120 | adapters | `extension/firefox/adapters/google.js` | `GoogleAdapter.extract` | `test_site_adapters_semantic_extraction` | JavaScript site adapters extract clean semantic content for top sites |
| `REQ-ADPT-SMOKE-001` | adapters | `Docs/PLAN.md` | PH120 | adapters | `extension/firefox/adapters/base.js` | `BaseAdapter` | `test_site_adapters_live_smoke` | Site adapter live smoke test against local fixture pages |
| `REQ-PLAN-PH120-001` | adapters | `Docs/PLAN.md` | PH120 | adapters | `extension/firefox/adapters/base.js` | `BaseAdapter.extract` | `test_outdated_adapter_fails_safely` | Outdated or broken site selectors fail safely to generic DOM extractor |
| `REQ-DASH-001` | dashboard | `Docs/DOCS.md` | PH130 | dashboard | `app/api/app.py` | `create_dashboard_app` | `test_dashboard_cors_and_localhost_binding` | FastAPI dashboard server binds strictly to 127.0.0.1 with CORS protection |
| `REQ-DASH-002` | dashboard | `Docs/DOCS.md` | PH130 | dashboard | `app/api/routes_config.py` | `update_config` | `test_dashboard_config_crud_transactionality` | Transactional configuration CRUD API validates changes against schema |
| `REQ-DASH-CRUD-001` | dashboard | `Docs/PLAN.md` | PH130 | dashboard | `app/api/routes_actions.py` | `get_actions` | `test_dashboard_action_crud` | Action pack CRUD endpoints allow viewing and updating phrase actions |
| `REQ-DASH-AGNT-001` | dashboard | `Docs/PLAN.md` | PH130 | dashboard | `app/api/routes_agents.py` | `cancel_agent` | `test_dashboard_agent_controls` | Agent control endpoints allow inspecting and cancelling running tasks |
| `REQ-DASH-EVENT-001` | dashboard | `Docs/PLAN.md` | PH130 | dashboard | `app/api/routes_state.py` | `stream_state` | `test_dashboard_event_stream_sse` | Server-Sent Events (SSE) stream emits real-time state transitions |
| `REQ-HIST-001` | dashboard | `Docs/DOCS.md` | PH130 | dashboard | `app/api/routes_audit.py` | `get_audit_log` | `test_dashboard_audit_pagination` | Audit event log pagination with limit and offset query bounds |
| `REQ-STOR-SQLITE-001` | dashboard | `Docs/ARCHITECTURE.md` | PH130 | storage | `app/storage/sqlite.py` | `SQLiteStorage` | `test_sqlite_wal_and_serialized_worker` | SQLite dedicated worker thread with WAL mode and bounded queries |
| `REQ-PLAN-PH130-001` | dashboard | `Docs/PLAN.md` | PH130 | storage | `app/storage/sqlite.py` | `SQLiteStorage` | `test_dashboard_storage_degraded_fallback` | Storage degradation retains bounded in-memory audit metadata |
| `REQ-DASH-003` | ui | `Docs/DOCS.md` | PH140 | ui | `app/web/index.html` | `index.html` | `test_frontend_assets_local_and_no_node_runtime` | Dashboard frontend built with local static assets and zero Node build step |
| `REQ-UI-TECH-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/js/app.js` | `app.js` | `test_ui_vanilla_tech_stack` | Frontend technology strictly vanilla HTML, CSS, and modern JavaScript |
| `REQ-UI-PERF-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/css/app.css` | `app.css` | `test_ui_asset_performance_budget` | Dashboard asset performance budget strictly under 100KB gzipped |
| `REQ-UI-VIS-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/css/app.css` | `:root` | `test_ui_visual_system_tokens` | Visual system defines consistent design tokens and dark aesthetic |
| `REQ-UI-TOKENS-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/css/app.css` | `tokens` | `test_ui_color_tokens` | Semantic color tokens defined for backgrounds, surfaces, and accents |
| `REQ-UI-TYPO-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/css/app.css` | `typography` | `test_ui_typography_stack` | Typography uses clean system font stack with fallback fonts |
| `REQ-UI-BORDER-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/css/app.css` | `borders` | `test_ui_radius_and_border` | Panel border radius and borders follow 14px/8px specification |
| `REQ-UI-BG-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/css/app.css` | `background` | `test_ui_background_gradient` | Subtle CSS radial gradient background replaces photographic wallpaper |
| `REQ-UI-AICORE-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `svg#ai-core` | `test_ui_aicore_animation` | Animated AI Core SVG reacts smoothly to system runtime state changes |
| `REQ-UI-AICORE-IMPL-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/css/app.css` | `ai-core-keyframes` | `test_ui_aicore_svg_keyframes` | AI Core implementation uses single inline SVG and CSS keyframes |
| `REQ-UI-SHELL-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `nav.sidebar` | `test_ui_desktop_shell_layout` | Desktop shell provides sidebar navigation and primary content container |
| `REQ-UI-TOPBAR-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `header.topbar` | `test_ui_global_topbar` | Global top bar displays assistant status pill, title, and quick toggles |
| `REQ-UI-VIEW-HOME-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#screen-home` | `test_ui_view_home` | Screen Home provides at-a-glance status, quick actions, and composer |
| `REQ-UI-HOME-CONTENT-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#home-content` | `test_ui_home_content_panel` | Home left/center content area displays recent actions and activity |
| `REQ-UI-HOME-AICORE-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#home-aicore` | `test_ui_home_aicore_panel` | Home AI Core panel houses central orb visualization |
| `REQ-UI-HOME-COMPOSER-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#home-composer` | `test_ui_home_bottom_composer` | Home bottom composer provides text input and voice toggle controls |
| `REQ-UI-VIEW-CHAT-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#screen-chat` | `test_ui_view_chat` | Screen Chat displays conversational history and streaming tokens |
| `REQ-UI-VIEW-TASKS-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#screen-tasks` | `test_ui_view_tasks_agents` | Screen Tasks/Agents displays active tasks and agent configuration |
| `REQ-UI-TASKS-LIST-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#tasks-list` | `test_ui_tasks_list_component` | Tasks list displays task cards with step progress and status badges |
| `REQ-UI-TASKS-DRAWER-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#agent-drawer` | `test_ui_agent_settings_drawer` | Agent settings drawer configures step limits and execution budgets |
| `REQ-UI-VIEW-BROWSER-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#screen-browser` | `test_ui_view_browser` | Screen Browser displays domain allowlist, bridge status, and site adapters |
| `REQ-UI-BROWSER-DOMAINS-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#domains-table` | `test_ui_browser_domain_table` | Domain allowlist table allows adding and removing allowed domains |
| `REQ-UI-BROWSER-STATUS-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#bridge-status` | `test_ui_browser_bridge_status` | Browser bridge status card indicates Firefox extension connection state |
| `REQ-UI-BROWSER-ADAPTERS-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#adapter-cards` | `test_ui_browser_adapter_cards` | Site adapter cards show status and capabilities of registered adapters |
| `REQ-UI-VIEW-VOICE-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#screen-voice` | `test_ui_view_voice` | Screen Voice provides assistant identity, listening, and privacy controls |
| `REQ-UI-VOICE-IDENTITY-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#voice-identity` | `test_ui_voice_identity` | Voice assistant identity settings configure assistant display name |
| `REQ-UI-VOICE-LISTEN-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#voice-listening` | `test_ui_voice_listening_controls` | Voice listening controls configure always-listen mode and wake word |
| `REQ-UI-VOICE-STT-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#voice-stt` | `test_ui_voice_stt_controls` | Voice STT section displays configured provider and language options |
| `REQ-UI-VOICE-PRIVACY-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#voice-privacy-card` | `test_ui_voice_privacy_card` | Voice privacy card explicitly highlights local wake and zero cloud retention |
| `REQ-UI-VOICE-TTS-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#voice-tts` | `test_ui_voice_tts_controls` | Voice TTS controls provide audio playback toggle and volume setting |
| `REQ-UI-VIEW-ACTIONS-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#screen-actions` | `test_ui_view_actions` | Screen Actions displays action packs and registered phrase bindings |
| `REQ-UI-VIEW-PERMS-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#screen-permissions` | `test_ui_view_permissions` | Screen Permissions manages terminal, files, and browser safety rules |
| `REQ-UI-PERMS-TERM-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#perms-terminal` | `test_ui_perms_terminal` | Terminal permissions panel manages command preapproval rules |
| `REQ-UI-PERMS-FILES-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#perms-files` | `test_ui_perms_files` | Files permissions panel manages allowed filesystem root paths |
| `REQ-UI-PERMS-BROWSER-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#perms-browser` | `test_ui_perms_browser` | Browser permissions panel manages domain allowlist and capability shortcuts |
| `REQ-UI-VIEW-WORKSPACES-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#screen-workspaces` | `test_ui_view_workspaces` | Screen Files/Workspaces configures workspace roots and path containment |
| `REQ-UI-VIEW-DEV-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#screen-developer` | `test_ui_view_developer` | Screen Developer manages coding repositories, VS Code, and agent defaults |
| `REQ-UI-DEV-REPOS-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#dev-repos` | `test_ui_dev_repositories` | Developer Repositories panel lists configured git repositories |
| `REQ-UI-DEV-VSCODE-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#dev-vscode` | `test_ui_dev_vscode` | Developer VS Code panel displays CLI integration and workspace launcher |
| `REQ-UI-DEV-AGENT-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#dev-agent-defaults` | `test_ui_dev_agent_defaults` | Coding agent defaults panel configures auto-commit and step limits |
| `REQ-UI-VIEW-SETTINGS-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#screen-settings` | `test_ui_view_settings` | Screen Settings provides centralized access to all configuration groups |
| `REQ-UI-SETTINGS-GEN-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#settings-general` | `test_ui_settings_general` | General settings panel configures assistant persona and autostart |
| `REQ-UI-SETTINGS-AI-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#settings-ai` | `test_ui_settings_ai` | AI settings panel configures provider, model, base URL, and timeouts |
| `REQ-UI-SETTINGS-VOICE-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#settings-voice-shortcut` | `test_ui_settings_voice` | Voice settings shortcut navigates directly to Voice screen |
| `REQ-UI-SETTINGS-BROWSER-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#settings-browser-shortcut` | `test_ui_settings_browser` | Browser settings shortcut navigates directly to Browser screen |
| `REQ-UI-SETTINGS-ACTIONS-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#settings-actions-shortcut` | `test_ui_settings_actions` | Actions settings shortcut navigates directly to Actions & Permissions |
| `REQ-UI-SETTINGS-PRIVACY-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#settings-privacy` | `test_ui_settings_privacy` | Privacy settings panel configures data retention and audit clearing |
| `REQ-UI-SETTINGS-RES-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#settings-resources` | `test_ui_settings_resources` | Resource limits settings panel displays live memory RSS and budget cap |
| `REQ-UI-SETTINGS-SYS-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/index.html` | `#settings-system` | `test_ui_settings_system` | System settings panel displays daemon version and service restart button |
| `REQ-UI-RESPONSIVE-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/css/app.css` | `media-queries` | `test_ui_responsive_layout` | Responsive layout adapts cleanly to desktop viewports (1366x768 upward) |
| `REQ-UI-A11Y-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/css/app.css` | `accessibility` | `test_ui_accessibility_and_reduced_motion` | Accessibility compliance: keyboard reachable, aria-live, prefers-reduced-motion |
| `REQ-UI-SETTINGS-INV-001` | ui | `Docs/UI.md` | PH140 | ui | `app/web/js/app.js` | `SettingsManager` | `test_ui_settings_inventory_binding` | Dashboard settings inventory binds exhaustively to Pydantic Config fields |
| `REQ-PLAN-PH140-001` | ui | `Docs/PLAN.md` | PH140 | ui | `app/web/js/app.js` | `StateStreamListener` | `test_ui_sse_connection_lifecycle` | Dashboard frontend handles SSE connection drops and automatic reconnection |
| `REQ-EXEC-UI-001` | ui | `Docs/EXECUTION.md` | PH140 | ui | `app/web/index.html` | `index.html` | `test_ui_no_external_cdns` | Dashboard frontend assets strictly local with zero external CDN references |
| `REQ-DEV-001` | developer | `Docs/DOCS.md` | PH150 | developer | `app/executors/developer.py` | `DeveloperWorkflowService` | `test_dev_workflow_git_and_test_under_policy` | Developer workflows (git status/diff, test runner) execute under central policy |
| `REQ-PLAN-PH150-001` | developer | `Docs/PLAN.md` | PH150 | developer | `app/executors/developer.py` | `DeveloperWorkflowService` | `test_auto_commit_disabled_by_default` | Auto-commit remains disabled by default; require explicit user flag |
| `REQ-RES-001` | resource | `Docs/DOCS.md` | PH160 | lifecycle | `app/lifecycle.py` | `LifecycleManager.monitor_memory` | `test_resident_cgroup_memory_stress_compliance` | Resident daemon cgroup memory strictly bounded under 300 MiB stress cap |
| `REQ-RES-CGROUP-001` | resource | `Docs/ARCHITECTURE.md` | PH160 | lifecycle | `app/lifecycle.py` | `LifecycleManager.monitor_memory` | `test_cgroup_memory_accounting_with_children` | Systemd cgroup memory accounting tracks total slice including child workers |
| `REQ-PLAN-PH160-001` | resource | `Docs/PLAN.md` | PH160 | lifecycle | `app/lifecycle.py` | `LifecycleManager.monitor_memory` | `test_resource_monitor_lifecycle` | Resource monitor triggers memory compaction when approaching MemoryHigh |
| `REQ-EXEC-MEM-001` | resource | `Docs/EXECUTION.md` | PH160 | lifecycle | `tests/test_resource_hardening.py` | `test_memory_measurement_protocol` | `test_memory_measurement_protocol` | Memory measurement workflow records accurate RSS deltas for new subsystems |
| `REQ-PKG-EXT-001` | packaging | `Docs/PLAN.md` | PH170 | packaging | `extension/firefox/manifest.json` | `manifest` | `test_packaging_firefox_extension` | Firefox extension packaged and installable via local manifest |
| `REQ-PKG-ICON-001` | packaging | `Docs/PLAN.md` | PH170 | packaging | `packaging/install.sh` | `install.sh` | `test_packaging_desktop_icons` | Application desktop icons packaged under standard XDG icon directories |
| `REQ-PKG-FIRST-001` | packaging | `Docs/PLAN.md` | PH170 | packaging | `packaging/install.sh` | `install.sh` | `test_packaging_first_run_config` | First-run setup wizard creates initial default configuration and directories |
| `REQ-PLAN-PH170-001` | packaging | `Docs/PLAN.md` | PH170 | packaging | `packaging/systemd/maya.service` | `maya.service` | `test_systemd_service_unit_configuration` | Systemd user service unit configured with memory limits and project-hd script |
| `REQ-UPDATE-TRUST-001` | packaging | `Docs/SECURITY.md` | PH170 | packaging | `packaging/uninstall.sh` | `uninstall.sh` | `test_packaging_uninstall_cleanup` | Uninstall script completely removes units, hosts, and temporary runtime files |
| `REQ-EXEC-TERM-001` | packaging | `Docs/EXECUTION.md` | PH170 | packaging | `packaging/systemd/maya.service` | `maya.service` | `test_packaging_safe_api_key_environment` | Safe API key environment strategy without leaking secrets to subprocesses |
| `REQ-ACCP-REDTEAM-001` | acceptance | `Docs/PLAN.md` | PH180 | acceptance | `tests/test_offline_determinism.py` | `test_final_acceptance_permission_red_team` | `test_final_acceptance_permission_red_team` | Permission red-team test suite attempts policy and sandbox escapes |
| `REQ-ACCP-BROWSER-001` | acceptance | `Docs/PLAN.md` | PH180 | acceptance | `tests/test_offline_determinism.py` | `test_final_acceptance_browser_allowlist` | `test_final_acceptance_browser_allowlist` | Browser allowlist acceptance verifies domain barriers under automated attack |
| `REQ-ACCP-VOICE-001` | acceptance | `Docs/PLAN.md` | PH180 | acceptance | `tests/test_offline_determinism.py` | `test_final_acceptance_voice_privacy` | `test_final_acceptance_voice_privacy` | Voice privacy acceptance verifies zero audio leakage under real hardware mock |
| `REQ-ACCP-MEMORY-001` | acceptance | `Docs/PLAN.md` | PH180 | acceptance | `tests/test_offline_determinism.py` | `test_final_acceptance_memory_stress` | `test_final_acceptance_memory_stress` | Memory stress acceptance runs 100 consecutive actions under 300MB cap |
| `REQ-ACCP-INSTALL-001` | acceptance | `Docs/PLAN.md` | PH180 | acceptance | `tests/test_offline_determinism.py` | `test_final_acceptance_clean_install` | `test_final_acceptance_clean_install` | Clean install acceptance verifies fresh installation into isolated environment |
| `REQ-ACCP-AUTOSTART-001` | acceptance | `Docs/PLAN.md` | PH180 | acceptance | `tests/test_offline_determinism.py` | `test_final_acceptance_autostart` | `test_final_acceptance_autostart` | Autostart acceptance verifies systemd service startup on simulated login |
| `REQ-ACCP-PACKAGING-001` | acceptance | `Docs/PLAN.md` | PH180 | acceptance | `tests/test_offline_determinism.py` | `test_final_acceptance_packaging` | `test_final_acceptance_packaging` | Packaging acceptance verifies all files installed with correct permissions |
| `REQ-ACCP-EVIDENCE-001` | acceptance | `Docs/PLAN.md` | PH180 | acceptance | `Docs/Current/PH180_FINAL_ACCEPTANCE_REPORT.md` | `report` | `test_final_acceptance_target_ubuntu_evidence` | Target Ubuntu manual evidence verification checklist completed |
| `REQ-PLAN-PH180-001` | acceptance | `Docs/PLAN.md` | PH180 | acceptance | `tests/test_offline_determinism.py` | `test_offline_deterministic_actions_succeed` | `test_offline_deterministic_actions_succeed` | Offline deterministic actions execute with zero provider network attempts |
| `REQ-ARCH-FAIL-001` | acceptance | `Docs/ARCHITECTURE.md` | PH180 | acceptance | `tests/test_offline_determinism.py` | `test_final_acceptance_failure_fail_closed` | `test_final_acceptance_failure_fail_closed` | Subsystem failure handling fails closed with zero action execution |
| `REQ-EXEC-TDD-001` | acceptance | `Docs/EXECUTION.md` | PH180 | acceptance | `tests/test_offline_determinism.py` | `test_final_acceptance_tdd_compliance` | `test_final_acceptance_tdd_compliance` | TDD compliance verified across all 18 implementation phases |

---

## 2. Requirements Summary by Phase

| Phase | Title | Requirement Count | Components Covered |
| :--- | :--- | :--- | :--- |
| `PH000` | Repository Skeleton & Typing | 8 | daemon, harness, state |
| `PH010` | Configuration System | 4 | config |
| `PH020` | Security Policy Engine | 8 | policy |
| `PH030` | Deterministic Action Registry | 5 | matcher, registry |
| `PH040` | Secure Execution Sandboxes | 6 | dispatcher, executors |
| `PH050` | Interactive Approval Broker & Native Popup | 5 | broker |
| `PH060` | NVIDIA AI Provider & Streaming Parser | 6 | provider |
| `PH070` | Command Router & Bounded Agent Runtime | 9 | agents, router |
| `PH080` | Voice Wake Pipeline & Audio Ring Buffer | 9 | voice |
| `PH090` | STT Adapter & Audio Buffer Release | 2 | stt |
| `PH100` | D-Bus / SNI System Tray Subsystem | 3 | tray |
| `PH110` | Firefox Extension & Native Messaging Host | 7 | browser |
| `PH120` | Semantic Web Adapters & DOM Extraction | 3 | adapters |
| `PH130` | Local Dashboard Backend & SQLite Storage | 8 | dashboard, storage |
| `PH140` | Vanilla Dashboard Frontend & SVG AI Core | 54 | ui |
| `PH150` | Developer Tooling & Git Workflows | 2 | developer |
| `PH160` | Lifecycle Hardening & Cgroup Guardrails | 4 | lifecycle |
| `PH170` | System Packaging & Systemd User Service | 6 | packaging |
| `PH180` | End-to-End System Verification & Acceptance | 11 | acceptance |
