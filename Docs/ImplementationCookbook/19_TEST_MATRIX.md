# Maya Comprehensive Test Matrix & Verification Suites

This matrix maps every atomic requirement to its exact verification test. In accordance with Section W:
- Existing phases (`PH000` through `PH040`) map to **ACTUAL current test functions** in `tests/test_*.py` and are marked `VERIFIED`.
- Future phases (`PH050` through `PH180`) specify planned automated tests marked `PLANNED_FUTURE_TEST` or human verification marked `MANUAL_ACCEPTANCE`.

---

## 1. Master Test Suite Matrix (160 Tests)

| Test ID | Phase | Req ID | Test File | Type | Status | Verification Command |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `test_baseline_process_rss` | PH000 | `REQ-PLAN-PH000-001` | `tests/test_policy.py` | resource | **VERIFIED** | `pytest tests/test_policy.py -k test_baseline_process_rss -v` |
| `test_daemon_lifecycle` | PH000 | `REQ-ARCH-SYS-001` | `tests/test_harness.py` | integration | **VERIFIED** | `pytest tests/test_harness.py -k test_daemon_lifecycle -v` |
| `test_no_credentials_required` | PH000 | `REQ-ARCH-PROC-001` | `tests/test_harness.py` | unit | **VERIFIED** | `pytest tests/test_harness.py -k test_no_credentials_required -v` |
| `test_app_state_interface` | PH000 | `REQ-ARCH-PROC-RES-001` | `tests/test_schemas.py` | unit | **VERIFIED** | `pytest tests/test_schemas.py -k test_app_state_interface -v` |
| `test_architecture_states` | PH000 | `REQ-ARCH-PROC-TRN-001` | `tests/test_schemas.py` | unit | **VERIFIED** | `pytest tests/test_schemas.py -k test_architecture_states -v` |
| `test_state_rejects_unknown_updates` | PH000 | `REQ-ARCH-DEP-001` | `tests/test_schemas.py` | security | **VERIFIED** | `pytest tests/test_schemas.py -k test_state_rejects_unknown_updates -v` |
| `test_config_fixture_exists` | PH000 | `REQ-EXEC-RUN-001` | `tests/test_harness.py` | unit | **VERIFIED** | `pytest tests/test_harness.py -k test_config_fixture_exists -v` |
| `test_state_rejects_coerced_boolean` | PH000 | `REQ-EXEC-EXIST-001` | `tests/test_schemas.py` | security | **VERIFIED** | `pytest tests/test_schemas.py -k test_state_rejects_coerced_boolean -v` |
| `test_command_request_unknown_field_rejected` | PH010 | `REQ-CFG-001` | `tests/test_schemas.py` | security | **VERIFIED** | `pytest tests/test_schemas.py -k test_command_request_unknown_field_rejected -v` |
| `test_assistant_identity_is_nonempty_and_trimmed` | PH010 | `REQ-CFG-LOC-001` | `tests/test_config.py` | unit | **VERIFIED** | `pytest tests/test_config.py -k test_assistant_identity_is_nonempty_and_trimmed -v` |
| `test_config_unknown_field_fails` | PH010 | `REQ-CFG-JSON-001` | `tests/test_config.py` | unit | **VERIFIED** | `pytest tests/test_config.py -k test_config_unknown_field_fails -v` |
| `test_dashboard_is_ipv4_loopback_only` | PH010 | `REQ-PLAN-PH010-001` | `tests/test_config.py` | unit | **VERIFIED** | `pytest tests/test_config.py -k test_dashboard_is_ipv4_loopback_only -v` |
| `test_policy_decision_enum_states` | PH020 | `REQ-POL-001` | `tests/test_schemas.py` | unit | **VERIFIED** | `pytest tests/test_schemas.py -k test_policy_decision_enum_states -v` |
| `test_action_definition_high_preapproved_rejected` | PH020 | `REQ-POL-002` | `tests/test_registry.py` | security | **VERIFIED** | `pytest tests/test_registry.py -k test_action_definition_high_preapproved_rejected -v` |
| `test_malformed_argv_denied` | PH020 | `REQ-POL-RISK-001` | `tests/test_policy.py` | security | **VERIFIED** | `pytest tests/test_policy.py -k test_malformed_argv_denied -v` |
| `test_sensitive_defaults_cannot_be_overridden` | PH020 | `REQ-POL-RISK-LOW-001` | `tests/test_policy.py` | unit | **VERIFIED** | `pytest tests/test_policy.py -k test_sensitive_defaults_cannot_be_overridden -v` |
| `test_file_symlink_and_parent_escape` | PH020 | `REQ-POL-RISK-MED-001` | `tests/test_registry.py` | security | **VERIFIED** | `pytest tests/test_registry.py -k test_file_symlink_and_parent_escape -v` |
| `test_privilege_wrappers_require_approval` | PH020 | `REQ-POL-ALWAYS-001` | `tests/test_policy.py` | unit | **VERIFIED** | `pytest tests/test_policy.py -k test_privilege_wrappers_require_approval -v` |
| `test_preapproval_contract` | PH020 | `REQ-POL-DEV-001` | `tests/test_policy_contract.py` | unit | **VERIFIED** | `pytest tests/test_policy_contract.py -k test_preapproval_contract -v` |
| `test_destructive_executables_never_preapproved` | PH020 | `REQ-PLAN-PH020-001` | `tests/test_policy_contract.py` | unit | **VERIFIED** | `pytest tests/test_policy_contract.py -k test_destructive_executables_never_preapproved -v` |
| `test_symlinked_pack_rejected` | PH030 | `REQ-REG-001` | `tests/test_registry.py` | security | **VERIFIED** | `pytest tests/test_registry.py -k test_symlinked_pack_rejected -v` |
| `test_strict_argument_substitution` | PH030 | `REQ-REG-002` | `tests/test_registry.py` | unit | **VERIFIED** | `pytest tests/test_registry.py -k test_strict_argument_substitution -v` |
| `test_runtime_ambiguity_never_picks_an_action` | PH030 | `REQ-REG-AMBIG-001` | `tests/test_registry.py` | unit | **VERIFIED** | `pytest tests/test_registry.py -k test_runtime_ambiguity_never_picks_an_action -v` |
| `test_max_pack_files_enforced` | PH030 | `REQ-REG-PACK-001` | `tests/test_registry.py` | unit | **VERIFIED** | `pytest tests/test_registry.py -k test_max_pack_files_enforced -v` |
| `test_max_total_actions_enforced` | PH030 | `REQ-PLAN-PH030-001` | `tests/test_policy.py` | unit | **VERIFIED** | `pytest tests/test_policy.py -k test_max_total_actions_enforced -v` |
| `test_process_args_strict_unknown_fields_and_validation` | PH040 | `REQ-EXEC-001` | `tests/test_executors.py` | unit | **VERIFIED** | `pytest tests/test_executors.py -k test_process_args_strict_unknown_fields_and_validation -v` |
| `test_resolve_trusted_executable_strict_v1` | PH040 | `REQ-EXEC-002` | `tests/test_executors.py` | unit | **VERIFIED** | `pytest tests/test_executors.py -k test_resolve_trusted_executable_strict_v1 -v` |
| `test_rule_risk_raises_trusted_risk` | PH040 | `REQ-PLAN-PH040-001` | `tests/test_dispatcher.py` | unit | **VERIFIED** | `pytest tests/test_dispatcher.py -k test_rule_risk_raises_trusted_risk -v` |
| `test_malformed_explicit_cwd_denied` | PH040 | `REQ-PLAN-PH040-PROC-001` | `tests/test_policy_contract.py` | security | **VERIFIED** | `pytest tests/test_policy_contract.py -k test_malformed_explicit_cwd_denied -v` |
| `test_file_operation_permissions` | PH040 | `REQ-PLAN-PH040-FILE-001` | `tests/test_policy.py` | unit | **VERIFIED** | `pytest tests/test_policy.py -k test_file_operation_permissions -v` |
| `test_canonical_browser_capabilities_accepted` | PH040 | `REQ-PLAN-PH040-XDG-001` | `tests/test_config.py` | unit | **VERIFIED** | `pytest tests/test_config.py -k test_canonical_browser_capabilities_accepted -v` |
| `test_approval_popup_transient_display` | PH050 | `REQ-APPR-001` | `tests/test_approval_broker.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_approval_broker.py -k test_approval_popup_transient_display -v` |
| `test_approval_hash_mismatch_denied` | PH050 | `REQ-APPR-002` | `tests/test_approval_broker.py` | security | **PLANNED_FUTURE_TEST** | `pytest tests/test_approval_broker.py -k test_approval_hash_mismatch_denied -v` |
| `test_approval_single_use_replay_denied` | PH050 | `REQ-APPR-003` | `tests/test_approval_broker.py` | security | **PLANNED_FUTURE_TEST** | `pytest tests/test_approval_broker.py -k test_approval_single_use_replay_denied -v` |
| `test_approval_timeout_denies` | PH050 | `REQ-PLAN-PH050-001` | `tests/test_approval_broker.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_approval_broker.py -k test_approval_timeout_denies -v` |
| `test_daemon_restart_clears_pending_approvals` | PH050 | `REQ-EXEC-APPR-001` | `tests/test_approval_broker.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_approval_broker.py -k test_daemon_restart_clears_pending_approvals -v` |
| `test_nvidia_client_configuration` | PH060 | `REQ-PROV-001` | `tests/test_nvidia_provider.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_nvidia_provider.py -k test_nvidia_client_configuration -v` |
| `test_reasoning_trace_not_leaked` | PH060 | `REQ-PROV-004` | `tests/test_nvidia_provider.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_nvidia_provider.py -k test_reasoning_trace_not_leaked -v` |
| `test_ai_provider_protocol_compliance` | PH060 | `REQ-PROV-BASE-001` | `tests/test_nvidia_provider.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_nvidia_provider.py -k test_ai_provider_protocol_compliance -v` |
| `test_nvidia_zero_sdk_retries` | PH060 | `REQ-PLAN-PH060-001` | `tests/test_nvidia_provider.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_nvidia_provider.py -k test_nvidia_zero_sdk_retries -v` |
| `test_nvidia_streaming_tool_call_parsing` | PH060 | `REQ-EXEC-NEMO-001` | `tests/test_nvidia_provider.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_nvidia_provider.py -k test_nvidia_streaming_tool_call_parsing -v` |
| `test_provider_tests_offline_no_quota` | PH060 | `REQ-EXEC-API-001` | `tests/test_nvidia_provider.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_nvidia_provider.py -k test_provider_tests_offline_no_quota -v` |
| `test_command_router_order_of_precedence` | PH070 | `REQ-ROUT-001` | `tests/test_command_router.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_command_router.py -k test_command_router_order_of_precedence -v` |
| `test_exact_action_zero_ai_calls` | PH070 | `REQ-ROUT-002` | `tests/test_command_router.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_command_router.py -k test_exact_action_zero_ai_calls -v` |
| `test_command_router_ai_fallback` | PH070 | `REQ-ROUT-AI-001` | `tests/test_command_router.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_command_router.py -k test_command_router_ai_fallback -v` |
| `test_agent_budget_and_step_limit_enforced` | PH070 | `REQ-AGNT-001` | `tests/test_agent_runtime.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_agent_runtime.py -k test_agent_budget_and_step_limit_enforced -v` |
| `test_agent_cannot_bypass_policy_dispatcher` | PH070 | `REQ-AGNT-002` | `tests/test_agent_runtime.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_agent_runtime.py -k test_agent_cannot_bypass_policy_dispatcher -v` |
| `test_agent_verification_step_enforced` | PH070 | `REQ-AGNT-VERIFY-001` | `tests/test_agent_runtime.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_agent_runtime.py -k test_agent_verification_step_enforced -v` |
| `test_agent_tool_schema_validation` | PH070 | `REQ-TOOL-SCHEMA-001` | `tests/test_agent_runtime.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_agent_runtime.py -k test_agent_tool_schema_validation -v` |
| `test_agent_runtime_single_task_lock` | PH070 | `REQ-PLAN-PH070-001` | `tests/test_agent_runtime.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_agent_runtime.py -k test_agent_runtime_single_task_lock -v` |
| `test_agent_task_lifecycle` | PH070 | `REQ-EXEC-AGENT-001` | `tests/test_agent_runtime.py` | integration | **PLANNED_FUTURE_TEST** | `pytest tests/test_agent_runtime.py -k test_agent_task_lifecycle -v` |
| `test_prewake_audio_zero_network_callback` | PH080 | `REQ-VOIC-001` | `tests/test_voice_wake.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_voice_wake.py -k test_prewake_audio_zero_network_callback -v` |
| `test_audio_ring_buffer_hard_bound` | PH080 | `REQ-VOIC-002` | `tests/test_voice_wake.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_voice_wake.py -k test_audio_ring_buffer_hard_bound -v` |
| `test_push_to_talk_activation` | PH080 | `REQ-VOIC-PTT-001` | `tests/test_voice_wake.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_voice_wake.py -k test_push_to_talk_activation -v` |
| `test_always_listening_mode_toggle` | PH080 | `REQ-VOIC-ALW-001` | `tests/test_voice_wake.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_voice_wake.py -k test_always_listening_mode_toggle -v` |
| `test_voice_state_machine_transitions` | PH080 | `REQ-VOIC-SM-001` | `tests/test_voice_wake.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_voice_wake.py -k test_voice_state_machine_transitions -v` |
| `test_no_stt_before_wake` | PH080 | `REQ-VOIC-NO-STT-001` | `tests/test_voice_wake.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_voice_wake.py -k test_no_stt_before_wake -v` |
| `test_command_segment_begins_after_wake` | PH080 | `REQ-VOIC-POST-001` | `tests/test_voice_wake.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_voice_wake.py -k test_command_segment_begins_after_wake -v` |
| `test_disabling_listen_closes_audio_stream` | PH080 | `REQ-VOIC-CLOSE-001` | `tests/test_voice_wake.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_voice_wake.py -k test_disabling_listen_closes_audio_stream -v` |
| `test_command_recording_vad_stop` | PH080 | `REQ-PLAN-PH080-001` | `tests/test_voice_wake.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_voice_wake.py -k test_command_recording_vad_stop -v` |
| `test_stt_transcribes_postwake_only` | PH090 | `REQ-STT-001` | `tests/test_stt_adapter.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_stt_adapter.py -k test_stt_transcribes_postwake_only -v` |
| `test_audio_buffer_released_after_stt` | PH090 | `REQ-PLAN-PH090-001` | `tests/test_stt_adapter.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_stt_adapter.py -k test_audio_buffer_released_after_stt -v` |
| `test_tray_dbus_registration` | PH100 | `REQ-TRAY-001` | `tests/test_tray.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_tray.py -k test_tray_dbus_registration -v` |
| `test_tray_menu_actions_and_state_sync` | PH100 | `REQ-TRAY-002` | `tests/test_tray.py` | integration | **PLANNED_FUTURE_TEST** | `pytest tests/test_tray.py -k test_tray_menu_actions_and_state_sync -v` |
| `test_tray_injected_control_callbacks` | PH100 | `REQ-PLAN-PH100-001` | `tests/test_tray.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_tray.py -k test_tray_injected_control_callbacks -v` |
| `test_native_messaging_framing_and_size_limit` | PH110 | `REQ-BROW-001` | `tests/test_browser_bridge.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_browser_bridge.py -k test_native_messaging_framing_and_size_limit -v` |
| `test_browser_unlisted_domain_denied` | PH110 | `REQ-BROW-002` | `tests/test_browser_bridge.py` | security | **PLANNED_FUTURE_TEST** | `pytest tests/test_browser_bridge.py -k test_browser_unlisted_domain_denied -v` |
| `test_browser_origin_mismatch_denied` | PH110 | `REQ-BROW-003` | `tests/test_browser_bridge.py` | security | **PLANNED_FUTURE_TEST** | `pytest tests/test_browser_bridge.py -k test_browser_origin_mismatch_denied -v` |
| `test_password_and_secret_fields_not_extracted` | PH110 | `REQ-BROW-004` | `tests/test_browser_bridge.py` | security | **PLANNED_FUTURE_TEST** | `pytest tests/test_browser_bridge.py -k test_password_and_secret_fields_not_extracted -v` |
| `test_browser_ungranted_host_permission_denied` | PH110 | `REQ-BROW-PERM-001` | `tests/test_browser_bridge.py` | security | **PLANNED_FUTURE_TEST** | `pytest tests/test_browser_bridge.py -k test_browser_ungranted_host_permission_denied -v` |
| `test_browser_bridge_uds_peercred_auth` | PH110 | `REQ-PLAN-PH110-001` | `tests/test_browser_bridge.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_browser_bridge.py -k test_browser_bridge_uds_peercred_auth -v` |
| `test_browser_extension_message_validation` | PH110 | `REQ-EXEC-BROW-001` | `tests/test_browser_bridge.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_browser_bridge.py -k test_browser_extension_message_validation -v` |
| `test_site_adapters_semantic_extraction` | PH120 | `REQ-ADPT-001` | `tests/test_site_adapters.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_site_adapters.py -k test_site_adapters_semantic_extraction -v` |
| `test_site_adapters_live_smoke` | PH120 | `REQ-ADPT-SMOKE-001` | `tests/test_site_adapters.py` | integration | **PLANNED_FUTURE_TEST** | `pytest tests/test_site_adapters.py -k test_site_adapters_live_smoke -v` |
| `test_outdated_adapter_fails_safely` | PH120 | `REQ-PLAN-PH120-001` | `tests/test_site_adapters.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_site_adapters.py -k test_outdated_adapter_fails_safely -v` |
| `test_dashboard_cors_and_localhost_binding` | PH130 | `REQ-DASH-001` | `tests/test_dashboard_api.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_api.py -k test_dashboard_cors_and_localhost_binding -v` |
| `test_dashboard_config_crud_transactionality` | PH130 | `REQ-DASH-002` | `tests/test_dashboard_api.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_api.py -k test_dashboard_config_crud_transactionality -v` |
| `test_dashboard_action_crud` | PH130 | `REQ-DASH-CRUD-001` | `tests/test_dashboard_api.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_api.py -k test_dashboard_action_crud -v` |
| `test_dashboard_agent_controls` | PH130 | `REQ-DASH-AGNT-001` | `tests/test_dashboard_api.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_api.py -k test_dashboard_agent_controls -v` |
| `test_dashboard_event_stream_sse` | PH130 | `REQ-DASH-EVENT-001` | `tests/test_dashboard_api.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_api.py -k test_dashboard_event_stream_sse -v` |
| `test_dashboard_audit_pagination` | PH130 | `REQ-HIST-001` | `tests/test_dashboard_api.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_api.py -k test_dashboard_audit_pagination -v` |
| `test_sqlite_wal_and_serialized_worker` | PH130 | `REQ-STOR-SQLITE-001` | `tests/test_dashboard_api.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_api.py -k test_sqlite_wal_and_serialized_worker -v` |
| `test_dashboard_storage_degraded_fallback` | PH130 | `REQ-PLAN-PH130-001` | `tests/test_dashboard_api.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_api.py -k test_dashboard_storage_degraded_fallback -v` |
| `test_frontend_assets_local_and_no_node_runtime` | PH140 | `REQ-DASH-003` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_frontend_assets_local_and_no_node_runtime -v` |
| `test_ui_vanilla_tech_stack` | PH140 | `REQ-UI-TECH-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_vanilla_tech_stack -v` |
| `test_ui_asset_performance_budget` | PH140 | `REQ-UI-PERF-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_asset_performance_budget -v` |
| `test_ui_visual_system_tokens` | PH140 | `REQ-UI-VIS-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_visual_system_tokens -v` |
| `test_ui_color_tokens` | PH140 | `REQ-UI-TOKENS-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_color_tokens -v` |
| `test_ui_typography_stack` | PH140 | `REQ-UI-TYPO-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_typography_stack -v` |
| `test_ui_radius_and_border` | PH140 | `REQ-UI-BORDER-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_radius_and_border -v` |
| `test_ui_background_gradient` | PH140 | `REQ-UI-BG-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_background_gradient -v` |
| `test_ui_aicore_animation` | PH140 | `REQ-UI-AICORE-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_aicore_animation -v` |
| `test_ui_aicore_svg_keyframes` | PH140 | `REQ-UI-AICORE-IMPL-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_aicore_svg_keyframes -v` |
| `test_ui_desktop_shell_layout` | PH140 | `REQ-UI-SHELL-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_desktop_shell_layout -v` |
| `test_ui_global_topbar` | PH140 | `REQ-UI-TOPBAR-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_global_topbar -v` |
| `test_ui_view_home` | PH140 | `REQ-UI-VIEW-HOME-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_view_home -v` |
| `test_ui_home_content_panel` | PH140 | `REQ-UI-HOME-CONTENT-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_home_content_panel -v` |
| `test_ui_home_aicore_panel` | PH140 | `REQ-UI-HOME-AICORE-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_home_aicore_panel -v` |
| `test_ui_home_bottom_composer` | PH140 | `REQ-UI-HOME-COMPOSER-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_home_bottom_composer -v` |
| `test_ui_view_chat` | PH140 | `REQ-UI-VIEW-CHAT-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_view_chat -v` |
| `test_ui_view_tasks_agents` | PH140 | `REQ-UI-VIEW-TASKS-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_view_tasks_agents -v` |
| `test_ui_tasks_list_component` | PH140 | `REQ-UI-TASKS-LIST-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_tasks_list_component -v` |
| `test_ui_agent_settings_drawer` | PH140 | `REQ-UI-TASKS-DRAWER-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_agent_settings_drawer -v` |
| `test_ui_view_browser` | PH140 | `REQ-UI-VIEW-BROWSER-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_view_browser -v` |
| `test_ui_browser_domain_table` | PH140 | `REQ-UI-BROWSER-DOMAINS-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_browser_domain_table -v` |
| `test_ui_browser_bridge_status` | PH140 | `REQ-UI-BROWSER-STATUS-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_browser_bridge_status -v` |
| `test_ui_browser_adapter_cards` | PH140 | `REQ-UI-BROWSER-ADAPTERS-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_browser_adapter_cards -v` |
| `test_ui_view_voice` | PH140 | `REQ-UI-VIEW-VOICE-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_view_voice -v` |
| `test_ui_voice_identity` | PH140 | `REQ-UI-VOICE-IDENTITY-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_voice_identity -v` |
| `test_ui_voice_listening_controls` | PH140 | `REQ-UI-VOICE-LISTEN-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_voice_listening_controls -v` |
| `test_ui_voice_stt_controls` | PH140 | `REQ-UI-VOICE-STT-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_voice_stt_controls -v` |
| `test_ui_voice_privacy_card` | PH140 | `REQ-UI-VOICE-PRIVACY-001` | `tests/test_dashboard_frontend.py` | security | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_voice_privacy_card -v` |
| `test_ui_voice_tts_controls` | PH140 | `REQ-UI-VOICE-TTS-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_voice_tts_controls -v` |
| `test_ui_view_actions` | PH140 | `REQ-UI-VIEW-ACTIONS-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_view_actions -v` |
| `test_ui_view_permissions` | PH140 | `REQ-UI-VIEW-PERMS-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_view_permissions -v` |
| `test_ui_perms_terminal` | PH140 | `REQ-UI-PERMS-TERM-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_perms_terminal -v` |
| `test_ui_perms_files` | PH140 | `REQ-UI-PERMS-FILES-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_perms_files -v` |
| `test_ui_perms_browser` | PH140 | `REQ-UI-PERMS-BROWSER-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_perms_browser -v` |
| `test_ui_view_workspaces` | PH140 | `REQ-UI-VIEW-WORKSPACES-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_view_workspaces -v` |
| `test_ui_view_developer` | PH140 | `REQ-UI-VIEW-DEV-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_view_developer -v` |
| `test_ui_dev_repositories` | PH140 | `REQ-UI-DEV-REPOS-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_dev_repositories -v` |
| `test_ui_dev_vscode` | PH140 | `REQ-UI-DEV-VSCODE-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_dev_vscode -v` |
| `test_ui_dev_agent_defaults` | PH140 | `REQ-UI-DEV-AGENT-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_dev_agent_defaults -v` |
| `test_ui_view_settings` | PH140 | `REQ-UI-VIEW-SETTINGS-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_view_settings -v` |
| `test_ui_settings_general` | PH140 | `REQ-UI-SETTINGS-GEN-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_settings_general -v` |
| `test_ui_settings_ai` | PH140 | `REQ-UI-SETTINGS-AI-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_settings_ai -v` |
| `test_ui_settings_voice` | PH140 | `REQ-UI-SETTINGS-VOICE-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_settings_voice -v` |
| `test_ui_settings_browser` | PH140 | `REQ-UI-SETTINGS-BROWSER-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_settings_browser -v` |
| `test_ui_settings_actions` | PH140 | `REQ-UI-SETTINGS-ACTIONS-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_settings_actions -v` |
| `test_ui_settings_privacy` | PH140 | `REQ-UI-SETTINGS-PRIVACY-001` | `tests/test_dashboard_frontend.py` | security | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_settings_privacy -v` |
| `test_ui_settings_resources` | PH140 | `REQ-UI-SETTINGS-RES-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_settings_resources -v` |
| `test_ui_settings_system` | PH140 | `REQ-UI-SETTINGS-SYS-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_settings_system -v` |
| `test_ui_responsive_layout` | PH140 | `REQ-UI-RESPONSIVE-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_responsive_layout -v` |
| `test_ui_accessibility_and_reduced_motion` | PH140 | `REQ-UI-A11Y-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_accessibility_and_reduced_motion -v` |
| `test_ui_settings_inventory_binding` | PH140 | `REQ-UI-SETTINGS-INV-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_settings_inventory_binding -v` |
| `test_ui_sse_connection_lifecycle` | PH140 | `REQ-PLAN-PH140-001` | `tests/test_dashboard_frontend.py` | integration | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_sse_connection_lifecycle -v` |
| `test_ui_no_external_cdns` | PH140 | `REQ-EXEC-UI-001` | `tests/test_dashboard_frontend.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_dashboard_frontend.py -k test_ui_no_external_cdns -v` |
| `test_dev_workflow_git_and_test_under_policy` | PH150 | `REQ-DEV-001` | `tests/test_developer_workflows.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_developer_workflows.py -k test_dev_workflow_git_and_test_under_policy -v` |
| `test_auto_commit_disabled_by_default` | PH150 | `REQ-PLAN-PH150-001` | `tests/test_developer_workflows.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_developer_workflows.py -k test_auto_commit_disabled_by_default -v` |
| `test_resident_cgroup_memory_stress_compliance` | PH160 | `REQ-RES-001` | `tests/test_resource_hardening.py` | resource | **PLANNED_FUTURE_TEST** | `pytest tests/test_resource_hardening.py -k test_resident_cgroup_memory_stress_compliance -v` |
| `test_cgroup_memory_accounting_with_children` | PH160 | `REQ-RES-CGROUP-001` | `tests/test_resource_hardening.py` | resource | **PLANNED_FUTURE_TEST** | `pytest tests/test_resource_hardening.py -k test_cgroup_memory_accounting_with_children -v` |
| `test_resource_monitor_lifecycle` | PH160 | `REQ-PLAN-PH160-001` | `tests/test_resource_hardening.py` | integration | **PLANNED_FUTURE_TEST** | `pytest tests/test_resource_hardening.py -k test_resource_monitor_lifecycle -v` |
| `test_memory_measurement_protocol` | PH160 | `REQ-EXEC-MEM-001` | `tests/test_resource_hardening.py` | resource | **PLANNED_FUTURE_TEST** | `pytest tests/test_resource_hardening.py -k test_memory_measurement_protocol -v` |
| `test_packaging_firefox_extension` | PH170 | `REQ-PKG-EXT-001` | `tests/test_packaging.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_packaging.py -k test_packaging_firefox_extension -v` |
| `test_packaging_desktop_icons` | PH170 | `REQ-PKG-ICON-001` | `tests/test_packaging.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_packaging.py -k test_packaging_desktop_icons -v` |
| `test_packaging_first_run_config` | PH170 | `REQ-PKG-FIRST-001` | `tests/test_packaging.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_packaging.py -k test_packaging_first_run_config -v` |
| `test_systemd_service_unit_configuration` | PH170 | `REQ-PLAN-PH170-001` | `tests/test_packaging.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_packaging.py -k test_systemd_service_unit_configuration -v` |
| `test_packaging_uninstall_cleanup` | PH170 | `REQ-UPDATE-TRUST-001` | `tests/test_packaging.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_packaging.py -k test_packaging_uninstall_cleanup -v` |
| `test_packaging_safe_api_key_environment` | PH170 | `REQ-EXEC-TERM-001` | `tests/test_packaging.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_packaging.py -k test_packaging_safe_api_key_environment -v` |
| `test_final_acceptance_permission_red_team` | PH180 | `REQ-ACCP-REDTEAM-001` | `tests/test_offline_determinism.py` | security | **PLANNED_FUTURE_TEST** | `pytest tests/test_offline_determinism.py -k test_final_acceptance_permission_red_team -v` |
| `test_final_acceptance_browser_allowlist` | PH180 | `REQ-ACCP-BROWSER-001` | `tests/test_offline_determinism.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_offline_determinism.py -k test_final_acceptance_browser_allowlist -v` |
| `test_final_acceptance_voice_privacy` | PH180 | `REQ-ACCP-VOICE-001` | `tests/test_offline_determinism.py` | security | **PLANNED_FUTURE_TEST** | `pytest tests/test_offline_determinism.py -k test_final_acceptance_voice_privacy -v` |
| `test_final_acceptance_memory_stress` | PH180 | `REQ-ACCP-MEMORY-001` | `tests/test_offline_determinism.py` | resource | **PLANNED_FUTURE_TEST** | `pytest tests/test_offline_determinism.py -k test_final_acceptance_memory_stress -v` |
| `test_final_acceptance_clean_install` | PH180 | `REQ-ACCP-INSTALL-001` | `tests/test_offline_determinism.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_offline_determinism.py -k test_final_acceptance_clean_install -v` |
| `test_final_acceptance_autostart` | PH180 | `REQ-ACCP-AUTOSTART-001` | `tests/test_offline_determinism.py` | integration | **PLANNED_FUTURE_TEST** | `pytest tests/test_offline_determinism.py -k test_final_acceptance_autostart -v` |
| `test_final_acceptance_packaging` | PH180 | `REQ-ACCP-PACKAGING-001` | `tests/test_offline_determinism.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_offline_determinism.py -k test_final_acceptance_packaging -v` |
| `test_final_acceptance_target_ubuntu_evidence` | PH180 | `REQ-ACCP-EVIDENCE-001` | `tests/test_offline_determinism.py` | manual | **MANUAL_ACCEPTANCE** | `pytest tests/test_offline_determinism.py -k test_final_acceptance_target_ubuntu_evidence -v` |
| `test_offline_deterministic_actions_succeed` | PH180 | `REQ-PLAN-PH180-001` | `tests/test_offline_determinism.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_offline_determinism.py -k test_offline_deterministic_actions_succeed -v` |
| `test_final_acceptance_failure_fail_closed` | PH180 | `REQ-ARCH-FAIL-001` | `tests/test_offline_determinism.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_offline_determinism.py -k test_final_acceptance_failure_fail_closed -v` |
| `test_final_acceptance_tdd_compliance` | PH180 | `REQ-EXEC-TDD-001` | `tests/test_offline_determinism.py` | unit | **PLANNED_FUTURE_TEST** | `pytest tests/test_offline_determinism.py -k test_final_acceptance_tdd_compliance -v` |

---

## 2. Test Breakdown by Phase & Status

| Phase | Total Tests | Verified Existing | Planned Future | Manual Acceptance |
| :--- | :--- | :--- | :--- | :--- |
| `PH000` | 8 | 8 | 0 | 0 |
| `PH010` | 4 | 4 | 0 | 0 |
| `PH020` | 8 | 8 | 0 | 0 |
| `PH030` | 5 | 5 | 0 | 0 |
| `PH040` | 6 | 6 | 0 | 0 |
| `PH050` | 5 | 0 | 5 | 0 |
| `PH060` | 6 | 0 | 6 | 0 |
| `PH070` | 9 | 0 | 9 | 0 |
| `PH080` | 9 | 0 | 9 | 0 |
| `PH090` | 2 | 0 | 2 | 0 |
| `PH100` | 3 | 0 | 3 | 0 |
| `PH110` | 7 | 0 | 7 | 0 |
| `PH120` | 3 | 0 | 3 | 0 |
| `PH130` | 8 | 0 | 8 | 0 |
| `PH140` | 54 | 0 | 54 | 0 |
| `PH150` | 2 | 0 | 2 | 0 |
| `PH160` | 4 | 0 | 4 | 0 |
| `PH170` | 6 | 0 | 6 | 0 |
| `PH180` | 11 | 0 | 10 | 1 |
