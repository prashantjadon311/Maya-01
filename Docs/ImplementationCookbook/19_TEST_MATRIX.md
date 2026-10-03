# Maya Master Test Matrix & Proof-of-Test Specifications

In accordance with the **Proof-of-Test Standard**, test names alone are not evidence. Every security and adversarial test must explicitly perform or simulate the claimed attack, asserting both positive expected outcomes and negative constraints (`assert_not`).

---

## 1. Master Test Suite Matrix (44 Canonical Recipes)

| Test ID | Phase | Req ID | Type | Target Test File | Attack Setup / Fault Injection | Expected Denial / Positive Assertion | Negative Assertion (`assert_not`) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `test_app_state_interface` | PH000 | `REQ-CORE-001` | unit | `tests/test_schemas.py` | None | Initial state is `READY_WAKE` | — |
| `test_command_request_unknown_field_rejected` | PH010 | `REQ-CFG-001` | unit | `tests/test_schemas.py` | Injected unknown JSON key | `pydantic.ValidationError` | — |
| `test_policy_engine_allow_ask_deny` | PH020 | `REQ-POL-001` | unit | `tests/test_policy.py` | None | Returns ALLOW, ASK_USER, or DENY | — |
| `test_action_definition_high_preapproved_rejected` | PH020 | `REQ-POL-002` | security | `tests/test_policy.py` | Create pack with `risk='high'` and `preapproved=True` | `ValidationError` raised | `assert defn.preapproved is False` |
| `test_symlinked_pack_rejected` | PH030 | `REQ-REG-001` | security | `tests/test_registry.py` | Create symlink to `/etc/passwd` in `actions.d/` | Pack load rejected | `assert 'passwd' not in registry` |
| `test_strict_argument_substitution` | PH030 | `REQ-REG-002` | security | `tests/test_registry.py` | Inject `; rm -rf /` in slot value | Strict argument substitution | `assert 'rm' not in argv[0]` |
| `test_process_executor_argv_only` | PH040 | `REQ-EXEC-001` | security | `tests/test_executors.py` | Command string with pipes e.g. `ls \| cat` | Execution fails or error returned | `assert Path('/tmp/out').exists() is False` |
| `test_file_executor_root_boundary` | PH040 | `REQ-EXEC-002` | security | `tests/test_executors.py` | Path traversal `../../../../etc/shadow` | `PathTraversalError` raised | `assert shadow_bytes not returned` |
| `test_approval_popup_transient_display` | PH050 | `REQ-APPR-001` | integration | `tests/test_approval_broker.py` | None | Popup dialog spawned | — |
| `test_approval_hash_mismatch_denied` | PH050 | `REQ-APPR-002` | security | `tests/test_approval_broker.py` | Mutate action parameters while reusing token | `verify_grant` returns `False` | `assert consume_grant() is False` |
| `test_approval_single_use_replay_denied` | PH050 | `REQ-APPR-003` | security | `tests/test_approval_broker.py` | Consume token once, attempt second consume | First is `True`, second is `False` | `assert second_consume is not True` |
| `test_approval_timeout_denies` | PH050 | `REQ-APPR-004` | security | `tests/test_approval_broker.py` | Advance fake clock past 60s timeout | Status resolves to `EXPIRED` | `assert status != 'GRANTED'` |
| `test_daemon_restart_clears_pending_approvals` | PH050 | `REQ-APPR-005` | security | `tests/test_approval_broker.py` | Re-initialize broker while approvals pending | New broker returns `False` for token | `assert old_token not in new_broker` |
| `test_nvidia_client_configuration` | PH060 | `REQ-PROV-001` | unit | `tests/test_nvidia_provider.py` | None | Base URL is NVIDIA endpoint | — |
| `test_nvidia_zero_sdk_retries` | PH060 | `REQ-PROV-002` | unit | `tests/test_nvidia_provider.py` | None | `max_retries == 0` | — |
| `test_nvidia_streaming_tool_call_parsing` | PH060 | `REQ-PROV-003` | integration | `tests/test_nvidia_provider.py` | None | Yields parsed tool calls from SSE | — |
| `test_reasoning_trace_not_leaked` | PH060 | `REQ-PROV-004` | security | `tests/test_nvidia_provider.py` | Inject `<think>secret thoughts</think>` in SSE | Content returned to caller | `assert 'secret thoughts' not in resp` |
| `test_provider_tests_offline_no_quota` | PH060 | `REQ-PROV-005` | unit | `tests/test_nvidia_provider.py` | None | Default tests use fakes | `assert outbound_network_calls == 0` |
| `test_command_router_order_of_precedence` | PH070 | `REQ-ROUT-001` | unit | `tests/test_command_router.py` | None | Exact match takes precedence | — |
| `test_exact_action_zero_ai_calls` | PH070 | `REQ-ROUT-002` | security | `tests/test_command_router.py` | Issue registered command e.g. 'open terminal'| Action executed locally | `assert fake_ai.call_count == 0` |
| `test_agent_budget_and_step_limit_enforced` | PH070 | `REQ-AGNT-001` | resource | `tests/test_agent_runtime.py` | Infinite loop of tool proposals | Halts at step 15 | — |
| `test_agent_cannot_bypass_policy_dispatcher` | PH070 | `REQ-AGNT-002` | security | `tests/test_agent_runtime.py` | Agent proposes unapproved high-risk command | Dispatched through PolicyEngine | `assert direct_exec_invoked is False` |
| `test_prewake_audio_zero_network_callback` | PH080 | `REQ-VOIC-001` | security | `tests/test_voice_wake.py` | Continuous pre-wake microphone streaming | Wake engine evaluates locally | `assert outbound_network_bytes == 0` |
| `test_audio_ring_buffer_hard_bound` | PH080 | `REQ-VOIC-002` | resource | `tests/test_voice_wake.py` | Feed 10s of audio without draining | Buffer capped at 96,000 bytes | — |
| `test_command_recording_vad_stop` | PH080 | `REQ-VOIC-003` | unit | `tests/test_voice_wake.py` | None | VAD stops recording | — |
| `test_stt_transcribes_postwake_only` | PH090 | `REQ-STT-001` | security | `tests/test_stt_adapter.py` | Attempt STT on pre-wake audio frames | `SecurityViolationError` raised | `assert stt.http_calls == 0` |
| `test_audio_buffer_released_after_stt` | PH090 | `REQ-STT-002` | resource | `tests/test_stt_adapter.py` | None | Audio memory freed post-STT | — |
| `test_stt_failure_prevents_execution` | PH090 | `REQ-STT-003` | security | `tests/test_stt_adapter.py` | Network drop during STT request | System transitions to `ERROR` | `assert dispatcher.calls == 0` |
| `test_tray_dbus_registration` | PH100 | `REQ-TRAY-001` | unit | `tests/test_tray.py` | None | D-Bus SNI object registered | — |
| `test_tray_menu_actions_and_state_sync` | PH100 | `REQ-TRAY-002` | integration | `tests/test_tray.py` | None | Tray icon mirrors daemon state | — |
| `test_native_messaging_framing_and_size_limit` | PH110 | `REQ-BROW-001` | unit | `tests/test_browser_bridge.py` | None | 4-byte length prefix parsed | — |
| `test_browser_unlisted_domain_denied` | PH110 | `REQ-BROW-002` | security | `tests/test_browser_bridge.py` | Issue command to unlisted domain `evil.com` | `DomainNotAllowedError` raised | `assert browser_executed is False` |
| `test_browser_origin_mismatch_denied` | PH110 | `REQ-BROW-003` | security | `tests/test_browser_bridge.py` | Tab navigated to phishing URL after command | Origin mismatch detected | `assert action_executed is False` |
| `test_password_and_secret_fields_not_extracted` | PH110 | `REQ-BROW-004` | security | `tests/test_browser_bridge.py` | Inject `<input type='password' value='s3cr3t'>`| Visible text extracted | `assert 's3cr3t' not in text` |
| `test_site_adapters_semantic_extraction` | PH120 | `REQ-ADPT-001` | integration | `tests/test_site_adapters.py` | None | Returns structured search items | — |
| `test_outdated_adapter_fails_safely` | PH120 | `REQ-ADPT-002` | security | `tests/test_site_adapters.py` | Scramble HTML DOM classes | Status `ADAPTER_OUTDATED` | `assert raw_dom_not_dumped is True` |
| `test_dashboard_cors_and_localhost_binding` | PH130 | `REQ-DASH-001` | security | `tests/test_dashboard_api.py` | Send request with Origin: `http://evil.com` | Access-Control-Allow-Origin != `*` | `assert 'evil.com' not in cors_header` |
| `test_dashboard_config_crud_transactionality` | PH130 | `REQ-DASH-002` | integration | `tests/test_dashboard_api.py` | None | Config updated transactionally | — |
| `test_frontend_assets_local_and_no_node_runtime` | PH140 | `REQ-DASH-003` | unit | `tests/test_dashboard_frontend.py` | None | Assets local, no Node packages | — |
| `test_dev_workflow_git_and_test_under_policy` | PH150 | `REQ-DEV-001` | integration | `tests/test_developer_workflows.py` | None | Status/diff returned | — |
| `test_auto_commit_disabled_by_default` | PH150 | `REQ-DEV-002` | security | `tests/test_developer_workflows.py` | Agent proposes commit without verification | Policy evaluates to `ASK_USER` | `assert res.auto_committed is False` |
| `test_resident_cgroup_memory_stress_compliance` | PH160 | `REQ-RES-001` | resource | `tests/test_resource_hardening.py` | Full stress scenario | Peak RSS <= 300 MiB | — |
| `test_systemd_service_unit_configuration` | PH170 | `REQ-PKG-001` | unit | `tests/test_packaging.py` | None | MemoryHigh & Max configured | — |
| `test_offline_deterministic_actions_succeed` | PH180 | `REQ-ACCP-001` | integration | `tests/test_offline_determinism.py` | Disable outbound network / AI API key | Local action executes cleanly | — |
