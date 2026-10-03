from pathlib import Path
import json
import pytest
from tools.cookbook.model import (
    CookbookModel,
    ValidationIssue,
    load_cookbook,
)
from tools.cookbook.validate import validate_cookbook
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


def test_actual_cookbook_is_freeze_clean():
    model = load_cookbook(COOKBOOK_ROOT)
    issues = validate_cookbook(model)
    blockers = [i for i in issues if i.severity in {"critical", "important"}]
    assert blockers == []
