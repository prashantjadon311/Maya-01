from pathlib import Path
import json
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
COOKBOOK_ROOT = REPO_ROOT / "Docs" / "ImplementationCookbook"
AUTHORITY_JSON = COOKBOOK_ROOT / "machine" / "authority.json"
FREEZE_MANIFEST = COOKBOOK_ROOT / "00_FREEZE_MANIFEST.md"
AUTHORITY_MAP = COOKBOOK_ROOT / "01_AUTHORITY_MAP.md"


def test_cookbook_skeleton_and_authority_metadata_exists():
    assert AUTHORITY_JSON.exists(), f"Missing {AUTHORITY_JSON}"
    assert FREEZE_MANIFEST.exists(), f"Missing {FREEZE_MANIFEST}"
    assert AUTHORITY_MAP.exists(), f"Missing {AUTHORITY_MAP}"

    with open(AUTHORITY_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["cookbook_work_base_sha"] == "d603173624ddc9285b32ee00f33c10be2ecc9b58"
    assert data["product_code_base_sha"] == "ef00714c86d3d7b5684d693da35aa82595a088d4"
    assert data["base_sha"] == "ef00714c86d3d7b5684d693da35aa82595a088d4"
    assert data["status"] in ("DRAFT", "FROZEN")
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

    expected_blobs = {
        "Docs/DOCS.md": "f0661e12eb37d7cb35468fb998d24e3be9ca61a0",
        "Docs/SECURITY.md": "018eddf2c193818f2e54f38dfe24639aac8af395",
        "Docs/ARCHITECTURE.md": "60c03ec8ef6122409da8c56020896dfe9f26bbd6",
        "Docs/CONFIG.md": "0df558337f3fe51a90f7eef6369b22218309879f",
        "Docs/UI.md": "33599d1fe7c09f3cd558824bcd13826dd958b302",
        "Docs/PLAN.md": "317d8e583903d901310755ca96db5eab8f090399",
        "Docs/TASKS.md": "f2b8f60c28f023946a3e3c4376c0bba14f585902",
        "Docs/EXECUTION.md": "4a41e269f1a46146e87b83829560294b85890563",
    }
    for doc, sha in expected_blobs.items():
        assert data["blob_shas"].get(doc) == sha, f"Blob SHA mismatch for {doc}"
