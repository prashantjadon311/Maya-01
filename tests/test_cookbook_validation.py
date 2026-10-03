from pathlib import Path
import json
import pytest
from tools.cookbook.model import (
    CookbookModel,
    ValidationIssue,
    load_cookbook,
    ResourceBoundItem,
    ResourceBoundsModel,
)
from tools.cookbook.validate import (
    validate_cookbook,
    PacketSection,
    PacketContract,
    parse_packet_contract,
    parse_numbered_sections,
    compare_packet_to_manifest,
    validate_section_content,
    positive_phase_text,
    parse_packet,
    extract_capsule_python,
    verify_existing_test_collectability,
    compute_artifact_hashes,
    compute_artifact_bundle_hash,
    BASE_SHA_PIN_RE,
)
from tools.cookbook.fingerprint import fingerprint_json, canonical_json_bytes

REPO_ROOT = Path(__file__).resolve().parent.parent
COOKBOOK_ROOT = REPO_ROOT / "Docs" / "ImplementationCookbook"
FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures" / "cookbook"


def test_cookbook_skeleton_and_authority_metadata_exists():
    authority_json = COOKBOOK_ROOT / "machine" / "authority.json"
    freeze_manifest = COOKBOOK_ROOT / "00_FREEZE_MANIFEST.md"
    authority_map = COOKBOOK_ROOT / "01_AUTHORITY_MAP.md"

    assert authority_json.exists(), f"Missing {authority_json}"
    assert freeze_manifest.exists(), f"Missing {freeze_manifest}"
    assert authority_map.exists(), f"Missing {authority_map}"

    with open(authority_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["cookbook_work_base_sha"] == "d603173624ddc9285b32ee00f33c10be2ecc9b58"
    assert data["product_code_base_sha"] == "ef00714c86d3d7b5684d693da35aa82595a088d4"
    assert data["base_sha"] == "ef00714c86d3d7b5684d693da35aa82595a088d4"
    assert data["status"] in ("DRAFT", "FROZEN", "BLOCKED")
    assert data["python_floor"] == ">=3.11"
    assert data["target_os"] == "Ubuntu"

    expected_order = [
        "Docs/DOCS.md",
        "Docs/SECURITY.md",
        "Docs/ARCHITECTURE.md",
        "Docs/CONFIG.md",
        "Docs/UI.md",
        "Docs/PLAN.md",
        "Docs/TASKS.md",
        "Docs/EXECUTION.md",
    ]
    assert data["authority_order"] == expected_order


def test_fingerprint_canonical_determinism(tmp_path):
    d1 = {"b": 2, "a": 1, "nested": {"z": 10, "y": 20}}
    d2 = {"nested": {"y": 20, "z": 10}, "a": 1, "b": 2}

    p1 = tmp_path / "f1.json"
    p2 = tmp_path / "f2.json"
    p1.write_text(json.dumps(d1, indent=4), encoding="utf-8")
    p2.write_text(json.dumps(d2), encoding="utf-8")

    fp1 = fingerprint_json(p1)
    fp2 = fingerprint_json(p2)
    assert fp1 == fp2
    assert len(fp1) == 64
    assert canonical_json_bytes(d1) == canonical_json_bytes(d2)


def test_validator_passes_on_valid_minimal():
    valid_dir = FIXTURES_ROOT / "valid_minimal"
    model = load_cookbook(valid_dir)
    issues = validate_cookbook(model)
    critical_or_important = [i for i in issues if i.severity in ("critical", "important")]
    assert critical_or_important == [], f"Unexpected issues in valid fixture: {critical_or_important}"


def test_validator_catches_duplicate_interface_owner():
    valid_dir = FIXTURES_ROOT / "valid_minimal"
    model = load_cookbook(valid_dir)
    # duplicate interface with different or same owner
    if model.interfaces.interfaces:
        dup = model.interfaces.interfaces[0].model_copy()
        model.interfaces.interfaces.append(dup)
        issues = validate_cookbook(model)
        codes = [i.code for i in issues]
        assert "DUPLICATE_INTERFACE" in codes


def test_validator_catches_unmapped_requirement():
    valid_dir = FIXTURES_ROOT / "valid_minimal"
    model = load_cookbook(valid_dir)
    if model.requirements.requirements:
        model.requirements.requirements[0].phase = ""
        model.requirements.requirements[0].out_of_v1_rationale = None
        issues = validate_cookbook(model)
        codes = [i.code for i in issues]
        assert "UNMAPPED_REQUIREMENT" in codes


def test_validator_catches_acceptance_without_test():
    valid_dir = FIXTURES_ROOT / "valid_minimal"
    model = load_cookbook(valid_dir)
    # empty tests
    model.tests.tests.clear()
    issues = validate_cookbook(model)
    codes = [i.code for i in issues]
    assert "UNTESTED_ACCEPTANCE" in codes or "MISSING_TEST" in codes


def test_validator_catches_file_without_owner():
    valid_dir = FIXTURES_ROOT / "valid_minimal"
    model = load_cookbook(valid_dir)
    if model.file_owners.files:
        model.file_owners.files[0].owner_phase = ""
        issues = validate_cookbook(model)
        codes = [i.code for i in issues]
        assert "UNOWNED_FILE" in codes


def test_validator_catches_circular_dependency():
    valid_dir = FIXTURES_ROOT / "valid_minimal"
    model = load_cookbook(valid_dir)
    # Add circular dependency in dependencies
    model.dependencies.edges.append({"from": "B", "to": "A"})
    model.dependencies.edges.append({"from": "A", "to": "B"})
    issues = validate_cookbook(model)
    codes = [i.code for i in issues]
    assert "CIRCULAR_DEPENDENCY" in codes


def test_validator_catches_resource_without_bound():
    valid_dir = FIXTURES_ROOT / "valid_minimal"
    model = load_cookbook(valid_dir)
    if model.interfaces.interfaces:
        model.interfaces.interfaces[0].bounds = None
        issues = validate_cookbook(model)
        codes = [i.code for i in issues]
        assert "UNBOUNDED_RESOURCE" in codes


def test_validator_catches_security_invariant_without_test():
    valid_dir = FIXTURES_ROOT / "valid_minimal"
    model = load_cookbook(valid_dir)
    # create security interface without matching security test
    if model.interfaces.interfaces:
        model.interfaces.interfaces[0].is_security_boundary = True
        model.interfaces.interfaces[0].security_test_id = "NON_EXISTENT_TEST"
        issues = validate_cookbook(model)
        codes = [i.code for i in issues]
        assert "SECURITY_TEST_MISSING" in codes


def test_validator_rejects_frozen_with_nonzero_counters():
    valid_dir = FIXTURES_ROOT / "valid_minimal"
    model = load_cookbook(valid_dir)
    model.authority.status = "FROZEN"
    model.requirements.requirements[0].phase = ""  # introduces an issue
    issues = validate_cookbook(model)
    codes = [i.code for i in issues]
    assert "FROZEN_WITH_OPEN_ISSUES" in codes or "UNMAPPED_REQUIREMENT" in codes


def test_validator_catches_phase_created_file_unowned():
    valid_dir = FIXTURES_ROOT / "valid_minimal"
    model = load_cookbook(valid_dir)
    model.phase_manifest.phases[0].files_created.append("unowned/future/file.py")
    issues = validate_cookbook(model)
    codes = [i.code for i in issues]
    assert "UNOWNED_FILE" in codes


def test_validator_catches_phase_modified_file_unauthorized():
    valid_dir = FIXTURES_ROOT / "valid_minimal"
    model = load_cookbook(valid_dir)
    # PH050 modifies app/core/dispatcher.py, remove PH050 from secondary_modifiers
    for f in model.file_owners.files:
        if f.path == "app/core/dispatcher.py":
            f.secondary_modifiers = []
    issues = validate_cookbook(model)
    codes = [i.code for i in issues]
    assert "UNAUTHORIZED_MODIFIER" in codes


def test_validator_cli_entrypoint_success(capsys):
    from tools.cookbook.validate import main as validate_main
    valid_dir = FIXTURES_ROOT / "valid_minimal"
    ret = validate_main([str(valid_dir)])
    captured = capsys.readouterr()
    assert ret == 0
    assert "MANDATORY FREEZE COUNTERS" in captured.out
    assert "CRITICAL_GAPS: 0" in captured.out


def test_validator_cli_entrypoint_failure(capsys, tmp_path):
    from tools.cookbook.validate import main as validate_main
    # Create empty directory
    ret = validate_main([str(tmp_path)])
    captured = capsys.readouterr()
    assert ret != 0


def test_fingerprint_cli_print_and_expect(capsys, tmp_path):
    from tools.cookbook.fingerprint import main as fingerprint_main
    test_file = tmp_path / "test.json"
    test_file.write_text('{"b": 2, "a": 1}', encoding="utf-8")

    # 1. Print fingerprint
    ret = fingerprint_main([str(test_file)])
    captured = capsys.readouterr()
    assert ret == 0
    calculated_hash = captured.out.strip()
    assert len(calculated_hash) == 64

    # 2. Expect match
    ret_match = fingerprint_main([str(test_file), "--expect", calculated_hash])
    assert ret_match == 0

    # 3. Expect mismatch
    ret_mismatch = fingerprint_main([str(test_file), "--expect", "0" * 64])
    assert ret_mismatch != 0


def test_validator_catches_duplicate_file_owner_path():
    valid_dir = FIXTURES_ROOT / "valid_minimal"
    model = load_cookbook(valid_dir)
    if model.file_owners.files:
        dup = model.file_owners.files[0].model_copy()
        model.file_owners.files.append(dup)
        issues = validate_cookbook(model)
        codes = [i.code for i in issues]
        assert "DUPLICATE_FILE_OWNER_PATH" in codes


def test_validator_catches_duplicate_phase_id():
    valid_dir = FIXTURES_ROOT / "valid_minimal"
    model = load_cookbook(valid_dir)
    if model.phase_manifest.phases:
        dup = model.phase_manifest.phases[0].model_copy()
        model.phase_manifest.phases.append(dup)
        issues = validate_cookbook(model)
        codes = [i.code for i in issues]
        assert "DUPLICATE_PHASE_ID" in codes


def test_validator_catches_duplicate_dependency_edge():
    valid_dir = FIXTURES_ROOT / "valid_minimal"
    model = load_cookbook(valid_dir)
    if model.dependencies.edges:
        dup = model.dependencies.edges[0].model_copy()
        model.dependencies.edges.append(dup)
        issues = validate_cookbook(model)
        codes = [i.code for i in issues]
        assert "DUPLICATE_DEPENDENCY_EDGE" in codes


def test_validator_catches_phase_self_dependency():
    valid_dir = FIXTURES_ROOT / "valid_minimal"
    model = load_cookbook(valid_dir)
    edge_cls = type(model.dependencies.edges[0])
    model.dependencies.edges.append(edge_cls(**{"from": "PH050", "to": "PH050"}))
    issues = validate_cookbook(model)
    codes = [i.code for i in issues]
    assert "PHASE_SELF_DEPENDENCY" in codes


def test_validator_catches_unknown_or_out_of_order_phase_dependency():
    valid_dir = FIXTURES_ROOT / "valid_minimal"
    model = load_cookbook(valid_dir)
    edge_cls = type(model.dependencies.edges[0])
    # Unknown dependency
    model.dependencies.edges.append(edge_cls(**{"from": "PH050", "to": "PH999"}))
    issues = validate_cookbook(model)
    codes = [i.code for i in issues]
    assert "UNKNOWN_DEPENDENCY_PHASE" in codes

    # Out of order dependency (PH050 depends on later PH070)
    model.dependencies.edges = [e for e in model.dependencies.edges if e.to != "PH999"]
    model.dependencies.edges.append(edge_cls(**{"from": "PH050", "to": "PH070"}))
    issues2 = validate_cookbook(model)
    codes2 = [i.code for i in issues2]
    assert "OUT_OF_ORDER_PHASE_DEPENDENCY" in codes2


def test_validator_catches_missing_required_read():
    valid_dir = FIXTURES_ROOT / "valid_minimal"
    model = load_cookbook(valid_dir)
    if model.phase_manifest.phases:
        model.phase_manifest.phases[0].required_reads.append("nonexistent/ghost_file.md")
        issues = validate_cookbook(model)
        codes = [i.code for i in issues]
        assert "REQUIRED_READ_MISSING" in codes


def test_validator_catches_missing_required_capsule():
    valid_dir = FIXTURES_ROOT / "valid_minimal"
    model = load_cookbook(valid_dir)
    if model.phase_manifest.phases:
        model.phase_manifest.phases[0].required_capsules.append("CAP-999")
        issues = validate_cookbook(model)
        codes = [i.code for i in issues]
        assert "REQUIRED_CAPSULE_MISSING" in codes


def test_validator_catches_duplicate_authority_coverage_heading():
    valid_dir = FIXTURES_ROOT / "valid_minimal"
    model = load_cookbook(valid_dir)
    if model.authority_coverage and model.authority_coverage.sections:
        dup = model.authority_coverage.sections[0].model_copy()
        model.authority_coverage.sections.append(dup)
        issues = validate_cookbook(model)
        codes = [i.code for i in issues]
        assert "AUTHORITY_COVERAGE_DUPLICATE" in codes


def test_packet_manifest_real_file_created_mismatch_rejected():
    phase_obj = next(p for p in load_cookbook(COOKBOOK_ROOT).phase_manifest.phases if p.phase_id == "PH050")
    dummy_contract = PacketContract(
        files_created=frozenset(["unexpected/file.py"]),
        files_modified=frozenset(phase_obj.files_modified),
        files_forbidden=frozenset(phase_obj.files_forbidden_to_modify),
        dependencies=frozenset(phase_obj.dependencies),
        output_interfaces=frozenset(phase_obj.output_interfaces),
        tests=frozenset(phase_obj.tests),
        required_capsules=frozenset(phase_obj.required_capsules),
    )
    issues = []
    compare_packet_to_manifest(phase=phase_obj, contract=dummy_contract, issues=issues)
    assert any(i.code == "PHASE_PACKET_FILES_CREATED_MISMATCH" for i in issues)


def test_packet_manifest_real_file_modified_mismatch_rejected():
    phase_obj = next(p for p in load_cookbook(COOKBOOK_ROOT).phase_manifest.phases if p.phase_id == "PH050")
    dummy_contract = PacketContract(
        files_created=frozenset(phase_obj.files_created),
        files_modified=frozenset(["unexpected/modified.py"]),
        files_forbidden=frozenset(phase_obj.files_forbidden_to_modify),
        dependencies=frozenset(phase_obj.dependencies),
        output_interfaces=frozenset(phase_obj.output_interfaces),
        tests=frozenset(phase_obj.tests),
        required_capsules=frozenset(phase_obj.required_capsules),
    )
    issues = []
    compare_packet_to_manifest(phase=phase_obj, contract=dummy_contract, issues=issues)
    assert any(i.code == "PHASE_PACKET_FILES_MODIFIED_MISMATCH" for i in issues)


def test_packet_manifest_real_forbidden_mismatch_rejected():
    phase_obj = next(p for p in load_cookbook(COOKBOOK_ROOT).phase_manifest.phases if p.phase_id == "PH050")
    dummy_contract = PacketContract(
        files_created=frozenset(phase_obj.files_created),
        files_modified=frozenset(phase_obj.files_modified),
        files_forbidden=frozenset(["unexpected/forbidden.py"]),
        dependencies=frozenset(phase_obj.dependencies),
        output_interfaces=frozenset(phase_obj.output_interfaces),
        tests=frozenset(phase_obj.tests),
        required_capsules=frozenset(phase_obj.required_capsules),
    )
    issues = []
    compare_packet_to_manifest(phase=phase_obj, contract=dummy_contract, issues=issues)
    assert any(i.code == "PHASE_PACKET_FILES_FORBIDDEN_MISMATCH" for i in issues)


def test_packet_manifest_real_dependency_mismatch_rejected():
    phase_obj = next(p for p in load_cookbook(COOKBOOK_ROOT).phase_manifest.phases if p.phase_id == "PH050")
    dummy_contract = PacketContract(
        files_created=frozenset(phase_obj.files_created),
        files_modified=frozenset(phase_obj.files_modified),
        files_forbidden=frozenset(phase_obj.files_forbidden_to_modify),
        dependencies=frozenset(["PH000"]),
        output_interfaces=frozenset(phase_obj.output_interfaces),
        tests=frozenset(phase_obj.tests),
        required_capsules=frozenset(phase_obj.required_capsules),
    )
    issues = []
    compare_packet_to_manifest(phase=phase_obj, contract=dummy_contract, issues=issues)
    assert any(i.code == "PHASE_PACKET_DEPENDENCY_MISMATCH" for i in issues)


def test_packet_manifest_real_interface_mismatch_rejected():
    phase_obj = next(p for p in load_cookbook(COOKBOOK_ROOT).phase_manifest.phases if p.phase_id == "PH050")
    dummy_contract = PacketContract(
        files_created=frozenset(phase_obj.files_created),
        files_modified=frozenset(phase_obj.files_modified),
        files_forbidden=frozenset(phase_obj.files_forbidden_to_modify),
        dependencies=frozenset(phase_obj.dependencies),
        output_interfaces=frozenset(["ghost_interface"]),
        tests=frozenset(phase_obj.tests),
        required_capsules=frozenset(phase_obj.required_capsules),
    )
    issues = []
    compare_packet_to_manifest(phase=phase_obj, contract=dummy_contract, issues=issues)
    assert any(i.code == "PHASE_PACKET_INTERFACE_MISMATCH" for i in issues)


def test_packet_manifest_real_test_mismatch_rejected():
    phase_obj = next(p for p in load_cookbook(COOKBOOK_ROOT).phase_manifest.phases if p.phase_id == "PH050")
    dummy_contract = PacketContract(
        files_created=frozenset(phase_obj.files_created),
        files_modified=frozenset(phase_obj.files_modified),
        files_forbidden=frozenset(phase_obj.files_forbidden_to_modify),
        dependencies=frozenset(phase_obj.dependencies),
        output_interfaces=frozenset(phase_obj.output_interfaces),
        tests=frozenset(["test_ghost_unplanned"]),
        required_capsules=frozenset(phase_obj.required_capsules),
    )
    issues = []
    compare_packet_to_manifest(phase=phase_obj, contract=dummy_contract, issues=issues)
    assert any(i.code == "PHASE_PACKET_TEST_MISMATCH" for i in issues)


def test_packet_manifest_real_capsule_mismatch_rejected():
    phase_obj = next(p for p in load_cookbook(COOKBOOK_ROOT).phase_manifest.phases if p.phase_id == "PH050")
    dummy_contract = PacketContract(
        files_created=frozenset(phase_obj.files_created),
        files_modified=frozenset(phase_obj.files_modified),
        files_forbidden=frozenset(phase_obj.files_forbidden_to_modify),
        dependencies=frozenset(phase_obj.dependencies),
        output_interfaces=frozenset(phase_obj.output_interfaces),
        tests=frozenset(phase_obj.tests),
        required_capsules=frozenset(["CAP-999"]),
    )
    issues = []
    compare_packet_to_manifest(phase=phase_obj, contract=dummy_contract, issues=issues)
    assert any(i.code == "PHASE_PACKET_CAPSULE_MISMATCH" for i in issues)


def test_placeholder_algorithm_section_rejected():
    sections = {13: PacketSection(13, "Exact Algorithms", "Standard exact algorithms / security invariants contract verified")}
    issues = []
    validate_section_content("PH050", sections, issues)
    assert any(i.code == "PLACEHOLDER_SECTION_CONTENT" for i in issues)


def test_placeholder_failure_section_rejected():
    sections = {23: PacketSection(23, "Failure Cases", "Standard failure cases / edge cases contract verified")}
    issues = []
    validate_section_content("PH050", sections, issues)
    assert any(i.code == "PLACEHOLDER_SECTION_CONTENT" for i in issues)


def test_placeholder_fixture_section_rejected():
    sections = {24: PacketSection(24, "Fakes / Fixtures", "Standard fakes / fixtures contract verified and enforced per phase manifest")}
    issues = []
    validate_section_content("PH050", sections, issues)
    assert any(i.code == "PLACEHOLDER_SECTION_CONTENT" for i in issues)


def test_placeholder_adversarial_section_rejected():
    sections = {26: PacketSection(26, "Adversarial Tests", "Standard adversarial / negative tests contract verified")}
    issues = []
    validate_section_content("PH050", sections, issues)
    assert any(i.code == "PLACEHOLDER_SECTION_CONTENT" for i in issues)


def test_requirement_supports_multiple_test_ids():
    model = load_cookbook(COOKBOOK_ROOT)
    prov_req = next(r for r in model.requirements.requirements if r.id == "REQ-PROV-001")
    assert len(prov_req.test_ids) >= 2
    assert "test_nvidia_client_configuration" in prov_req.test_ids
    assert "test_missing_api_key_fails_fast" in prov_req.test_ids


def test_verified_existing_nodeid_collectability():
    model = load_cookbook(COOKBOOK_ROOT)
    collect_issues = verify_existing_test_collectability(REPO_ROOT, model.tests.tests)
    assert collect_issues == []

    class DummyTest:
        status = "VERIFIED_EXISTING"
        pytest_nodeid = "tests/test_config.py::other_func"
        test_function = "test_config_loads"
        file = "tests/test_config.py"
        test_id = "test_dummy_nodeid"

    issues = verify_existing_test_collectability(REPO_ROOT, [DummyTest()])
    assert any(i.code == "VERIFIED_TEST_NODEID_MISMATCH" for i in issues)


def test_out_of_v1_requires_existing_authority_heading():
    model = load_cookbook(COOKBOOK_ROOT)
    assert model.authority_coverage is not None
    oov1 = next(s for s in model.authority_coverage.sections if s.classification == "EXPLICIT_OUT_OF_V1")
    assert oov1.exclusion_source == "Docs/DOCS.md"
    assert oov1.exclusion_heading == "## 15. V1 non-goals"

    bad_model = model.model_copy(deep=True)
    bad_sec = next(s for s in bad_model.authority_coverage.sections if s.classification == "EXPLICIT_OUT_OF_V1")
    bad_sec.exclusion_heading = "## 999. Ghost heading"
    issues = validate_cookbook(bad_model)
    assert any(i.code == "OUT_OF_V1_AUTHORITY_UNVERIFIED" for i in issues)


def test_resource_bound_requires_numeric_limit():
    valid_dir = FIXTURES_ROOT / "valid_minimal"
    model = load_cookbook(valid_dir)
    with pytest.raises(Exception):
        ResourceBoundItem(
            id="RB-TEST-NO-LIMIT",
            owner="test.owner",
            phase="PH050",
            lifetime="DAEMON",
            structure="list",
            max_count=None,
            max_bytes=None,
            timeout_seconds=None,
            overflow_policy="drop",
        )
    bad_bound = ResourceBoundItem.model_construct(
        id="RB-TEST-NO-LIMIT",
        owner="test.owner",
        phase="PH050",
        lifetime="DAEMON",
        structure="list",
        max_count=None,
        max_bytes=None,
        timeout_seconds=None,
        overflow_policy="drop",
    )
    model.resource_bounds = ResourceBoundsModel.model_construct(bounds=[bad_bound])
    issues = validate_cookbook(model)
    assert any(i.code == "RESOURCE_BOUND_MISSING_NUMERIC_LIMIT" for i in issues)


def test_interface_resource_bound_reference_exists():
    valid_dir = FIXTURES_ROOT / "valid_minimal"
    model = load_cookbook(valid_dir)
    good_bound = ResourceBoundItem(
        id="RB-VALID-1",
        owner="test.owner",
        phase="PH050",
        lifetime="DAEMON",
        structure="list",
        max_count=10,
        max_bytes=None,
        timeout_seconds=None,
        overflow_policy="drop",
    )
    model.resource_bounds = ResourceBoundsModel(bounds=[good_bound])
    model.interfaces.interfaces[0].resource_bound_ids = ["RB-NONEXISTENT"]
    issues = validate_cookbook(model)
    assert any(i.code == "UNKNOWN_RESOURCE_BOUND_REFERENCE" for i in issues)


def test_freeze_artifact_hash_change_rejected():
    model = load_cookbook(COOKBOOK_ROOT)
    frozen_model = model.model_copy(deep=True)
    frozen_model.authority.status = "FROZEN"
    if frozen_model.authority.artifact_hashes:
        key = next(iter(frozen_model.authority.artifact_hashes.keys()))
        frozen_model.authority.artifact_hashes[key] = "0" * 64
        issues = validate_cookbook(frozen_model)
        assert any(i.code == "FREEZE_ARTIFACT_HASH_MISMATCH" for i in issues)


def test_freeze_artifact_missing_rejected():
    model = load_cookbook(COOKBOOK_ROOT)
    frozen_model = model.model_copy(deep=True)
    frozen_model.authority.status = "FROZEN"
    frozen_model.authority.artifact_hashes["Docs/NonExistent.md"] = "a" * 64
    issues = validate_cookbook(frozen_model)
    assert any(i.code == "FREEZE_ARTIFACT_MISSING" for i in issues)


def test_future_phase_repair_sha_rejected():
    assert BASE_SHA_PIN_RE.search("Base SHA pinned at 057463e24734ca89553b0b6b60792a4fcbf3cfcc")
    for phase_file in (COOKBOOK_ROOT / "phases").glob("PH*.md"):
        assert not BASE_SHA_PIN_RE.search(phase_file.read_text(encoding="utf-8"))


def test_cap001_uses_action_request_canonical_bytes():
    text = extract_capsule_python("CAP-001")
    assert "to_canonical_bytes()" in text
    assert "model_dump_json()" not in text


def test_cap001_does_not_swallow_cancelled_error():
    text = extract_capsule_python("CAP-001")
    assert "asyncio.CancelledError" in text
    assert "raise" in text


def test_ph060_owns_ai_schema():
    model = load_cookbook(COOKBOOK_ROOT)
    schema_file = next((f for f in model.file_owners.files if f.path == "app/ai/schema.py"), None)
    assert schema_file is not None
    assert schema_file.owner_phase == "PH060"
    ph060_manifest = next(p for p in model.phase_manifest.phases if p.phase_id == "PH060")
    assert "app/ai/schema.py" in ph060_manifest.files_created
    packet = parse_packet("PH060")
    assert "app/ai/schema.py" in packet[5].body


def test_ph070_owns_agent_verifier():
    model = load_cookbook(COOKBOOK_ROOT)
    verifier_file = next((f for f in model.file_owners.files if f.path == "app/agents/verifier.py"), None)
    assert verifier_file is not None
    assert verifier_file.owner_phase == "PH070"
    ph070_manifest = next(p for p in model.phase_manifest.phases if p.phase_id == "PH070")
    assert "app/agents/verifier.py" in ph070_manifest.files_created
    packet = parse_packet("PH070")
    assert "app/agents/verifier.py" in packet[5].body


def test_wake_frame_math_exact():
    text = positive_phase_text(parse_packet("PH080"))
    assert "1280 samples" in text
    assert "2560 bytes" in text
    assert "1280 bytes = 80ms" not in text


def test_stt_audio_bound_exact():
    text80 = positive_phase_text(parse_packet("PH080"))
    text90 = positive_phase_text(parse_packet("PH090"))
    assert "960000" in text80 or "960,000" in text80
    assert "960000" in text90 or "960,000" in text90
    assert "320000 bytes = 30s" not in text80
    assert "320000 bytes = 30s" not in text90


def test_systemstate_ghost_rejected():
    for pid in [f"PH{i:03d}" for i in range(50, 190, 10)]:
        packet = parse_packet(pid)
        text = positive_phase_text(packet)
        assert "SystemState" not in text, f"SystemState ghost found in positive text of {pid}"


def test_riva_local_grpc_port_50051():
    text = positive_phase_text(parse_packet("PH090"), include={1, 12, 13, 14, 15, 16, 17, 28})
    assert "localhost:9000" not in text
    assert "50051" in text


def test_dashboard_port_matches_config():
    text = positive_phase_text(parse_packet("PH130"), include={1, 12, 13, 17, 20, 27, 28})
    assert ":8443" not in text
    assert "8765" in text


def test_reasoning_trace_ui_forbidden():
    text = positive_phase_text(parse_packet("PH140"), include={1, 12, 13, 20, 22, 28})
    assert "thought disclosure" not in text.lower()
    assert "raw model reasoning" not in text.lower()


def test_sqlite_connection_pooling_stale_claim_rejected():
    text = positive_phase_text(parse_packet("PH130"))
    assert "connection pooling" not in text.lower()
    assert "serialized" in text.lower() or "worker queue" in text.lower()


def test_audit_fallback_full_fail_closed_contract_present():
    text = positive_phase_text(parse_packet("PH130"))
    assert "fail-closed" in text.lower() or "fail closed" in text.lower()


def test_memoryhardening_has_no_emergency_gc_enforcement():
    text = positive_phase_text(parse_packet("PH160"))
    assert "emergency gc" not in text.lower()


def test_memoryhardening_uses_project_hd_service_name():
    text = positive_phase_text(parse_packet("PH160"))
    assert "project-hd.service" in text
    assert "maya.service" not in text


def test_packaging_uses_dedicated_venv():
    text = positive_phase_text(parse_packet("PH170"))
    assert "~/.local/share/project-h/venv" in text
    assert "pip install --user ." not in text


def test_packaging_has_no_home_user_placeholder():
    text = positive_phase_text(parse_packet("PH170"))
    assert "/home/USER/" not in text


def test_packaging_native_host_console_script_defined():
    text = positive_phase_text(parse_packet("PH170"))
    assert "project-h-browser-host" in text or "native_host" in text


def test_ph180_manifest_includes_final_acceptance_file():
    model = load_cookbook(COOKBOOK_ROOT)
    ph180_manifest = next(p for p in model.phase_manifest.phases if p.phase_id == "PH180")
    assert "tests/test_final_acceptance.py" in ph180_manifest.files_created
    packet = parse_packet("PH180")
    assert "tests/test_final_acceptance.py" in packet[5].body


def test_ph180_no_hardcoded_requirement_count():
    text = positive_phase_text(parse_packet("PH180"))
    assert "assert len(reqs) ==" not in text
    assert "assert len(requirements) ==" not in text


def test_actual_cookbook_is_freeze_clean():
    model = load_cookbook(COOKBOOK_ROOT)
    issues = validate_cookbook(model)
    blockers = [i for i in issues if i.severity in {"critical", "important"}]
    assert blockers == []
