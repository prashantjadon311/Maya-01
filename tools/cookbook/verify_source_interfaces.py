"""Project H Source Interface Verifier.

AST-based verification of actual PH000-PH040 Python source interfaces against
Docs/ImplementationCookbook/machine/source_interfaces.json.

Ensures that documentation and delta-checks are grounded in AST reality of the
current codebase, catching source interface drift before cookbook freeze.
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import sys
from typing import Any

CANONICAL_SOURCE_FILES = [
    "app/main.py",
    "app/core/state.py",
    "app/core/config.py",
    "app/core/dispatcher.py",
    "app/actions/schema.py",
    "app/actions/registry.py",
    "app/actions/matcher.py",
    "app/policy/engine.py",
    "app/policy/risk.py",
    "app/policy/paths.py",
    "app/executors/base.py",
    "app/executors/process.py",
    "app/executors/files.py",
    "app/executors/xdg.py",
    "app/browser/protocol.py",
]


def extract_file_interfaces(filepath: Path) -> dict[str, Any]:
    """Extract AST-based public interfaces from a Python source file."""
    content = filepath.read_text(encoding="utf-8")
    tree = ast.parse(content, filename=str(filepath))

    classes: dict[str, Any] = {}
    functions: list[str] = []
    constants: list[str] = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)
        elif isinstance(node, ast.ClassDef):
            methods: list[str] = []
            fields: list[str] = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append(item.name)
                elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    fields.append(item.target.id)
                elif isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            fields.append(target.id)
            classes[node.name] = {
                "methods": sorted(set(methods)),
                "fields": sorted(set(fields)),
            }
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    constants.append(target.id)

    return {
        "classes": dict(sorted(classes.items())),
        "functions": sorted(set(functions)),
        "constants": sorted(set(constants)),
    }


def generate_source_interfaces(repo_root: Path) -> dict[str, Any]:
    """Generate canonical interface snapshot across all PH000-PH040 source files."""
    interfaces: dict[str, Any] = {}
    for rel_path in sorted(CANONICAL_SOURCE_FILES):
        p = repo_root / rel_path
        if not p.exists():
            raise FileNotFoundError(f"Canonical source file missing: {rel_path}")
        interfaces[rel_path] = extract_file_interfaces(p)
    return interfaces


def verify_source_interfaces(
    repo_root: Path,
    expected_path: Path,
) -> tuple[int, list[str]]:
    """Compare live AST interfaces against expected source_interfaces.json."""
    if not expected_path.exists():
        return 1, [f"Expected source interfaces file missing: {expected_path}"]

    with open(expected_path, "r", encoding="utf-8") as f:
        expected = json.load(f)

    actual = generate_source_interfaces(repo_root)

    mismatches: list[str] = []

    for file_key, exp_info in expected.items():
        if file_key not in actual:
            mismatches.append(f"{file_key}: File present in expected but missing from actual source")
            continue
        act_info = actual[file_key]

        # Check classes
        exp_classes = exp_info.get("classes", {})
        act_classes = act_info.get("classes", {})
        for cls_name, exp_cls in exp_classes.items():
            if cls_name not in act_classes:
                mismatches.append(f"{file_key}: Expected class '{cls_name}' missing from source")
                continue
            act_cls = act_classes[cls_name]
            for m in exp_cls.get("methods", []):
                if m not in act_cls.get("methods", []):
                    mismatches.append(f"{file_key}: Class '{cls_name}' missing expected method '{m}'")
            for fld in exp_cls.get("fields", []):
                if fld not in act_cls.get("fields", []):
                    mismatches.append(f"{file_key}: Class '{cls_name}' missing expected field '{fld}'")

        # Check functions
        for fn in exp_info.get("functions", []):
            if fn not in act_info.get("functions", []):
                mismatches.append(f"{file_key}: Expected top-level function '{fn}' missing from source")

        # Check constants
        for c in exp_info.get("constants", []):
            if c not in act_info.get("constants", []):
                mismatches.append(f"{file_key}: Expected constant '{c}' missing from source")

    return len(mismatches), mismatches


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify actual PH000-PH040 source interfaces against canonical snapshot."
    )
    parser.add_argument(
        "interfaces_file",
        nargs="?",
        default="Docs/ImplementationCookbook/machine/source_interfaces.json",
        help="Path to source_interfaces.json",
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate or update the source_interfaces.json snapshot from current AST",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root directory (default: current directory)",
    )

    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    target_path = Path(args.interfaces_file)
    if not target_path.is_absolute():
        target_path = repo_root / target_path

    if args.generate:
        interfaces = generate_source_interfaces(repo_root)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(interfaces, f, indent=2, sort_keys=True)
            f.write("\n")
        print(f"Generated source interfaces snapshot at {target_path}")
        return 0

    count, mismatches = verify_source_interfaces(repo_root, target_path)
    if count == 0:
        print("SOURCE INTERFACES VERIFIED: 0 mismatches found.")
        return 0
    else:
        print(f"SOURCE INTERFACE MISMATCHES ({count} issues found):", file=sys.stderr)
        for m in mismatches:
            print(f"  - {m}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
