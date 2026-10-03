from collections import defaultdict
from pathlib import Path
from tools.cookbook.model import CookbookModel, ValidationIssue
from tools.cookbook.fingerprint import fingerprint_json


def detect_cycles(components: list[str], edges: list[dict[str, str]]) -> list[list[str]]:
    """Detect cycles in dependency graph using DFS."""
    adj = defaultdict(list)
    for edge in edges:
        u = edge["from"] if "from" in edge else edge.get("from_")
        v = edge["to"]
        if u and v:
            adj[u].append(v)

    visited = {}  # None = unvisited, 1 = visiting, 2 = visited
    cycles = []

    def dfs(node: str, path: list[str]):
        visited[node] = 1
        path.append(node)
        for neighbor in adj.get(node, []):
            if visited.get(neighbor) == 1:
                # cycle found
                cycle_start_idx = path.index(neighbor)
                cycles.append(path[cycle_start_idx:] + [neighbor])
            elif neighbor not in visited:
                dfs(neighbor, path)
        path.pop()
        visited[node] = 2

    all_nodes = set(components)
    for edge in edges:
        u = edge["from"] if "from" in edge else edge.get("from_")
        v = edge["to"]
        if u:
            all_nodes.add(u)
        if v:
            all_nodes.add(v)

    for node in sorted(all_nodes):
        if node not in visited:
            dfs(node, [])

    return cycles


def validate_cookbook(model: CookbookModel) -> list[ValidationIssue]:
    """Deterministically validate all cookbook models and manifest constraints."""
    issues: list[ValidationIssue] = []

    # 1. Requirement validation & duplicate check
    req_ids = set()
    req_map = {}
    for req in model.requirements.requirements:
        if req.id in req_ids:
            issues.append(
                ValidationIssue(
                    code="DUPLICATE_REQUIREMENT_ID",
                    path=f"requirements/{req.id}",
                    message=f"Duplicate requirement ID: {req.id}",
                    severity="critical",
                )
            )
        req_ids.add(req.id)
        req_map[req.id] = req

        if not req.phase and not req.out_of_v1_rationale:
            issues.append(
                ValidationIssue(
                    code="UNMAPPED_REQUIREMENT",
                    path=f"requirements/{req.id}",
                    message=f"Requirement {req.id} is unmapped and has no out_of_v1_rationale",
                    severity="critical",
                )
            )
        elif req.phase:
            if not req.test_id:
                issues.append(
                    ValidationIssue(
                        code="MISSING_TEST",
                        path=f"requirements/{req.id}",
                        message=f"Requirement {req.id} in phase {req.phase} has no test_id",
                        severity="important",
                    )
                )

    # 1b. Authority coverage check
    if model.authority_coverage is not None:
        for sec in model.authority_coverage.sections:
            if sec.normative:
                has_reqs = bool(sec.requirement_ids)
                has_out_of_v1 = bool(sec.notes and "OUT_OF_V1" in sec.notes)
                if not has_reqs and not has_out_of_v1:
                    issues.append(
                        ValidationIssue(
                            code="UNMAPPED_AUTHORITY_SECTION",
                            path=f"authority_coverage/{sec.source}#{sec.heading}",
                            message=f"Normative section '{sec.heading}' in {sec.source} has no mapped requirements or OUT_OF_V1 rationale",
                            severity="critical",
                        )
                    )
            for rid in sec.requirement_ids:
                if rid not in req_ids:
                    issues.append(
                        ValidationIssue(
                            code="UNKNOWN_REQUIREMENT_IN_AUTHORITY",
                            path=f"authority_coverage/{sec.source}#{sec.heading}/{rid}",
                            message=f"Authority coverage references unknown requirement ID: {rid}",
                            severity="critical",
                        )
                    )

    # 2. Test validation & duplicate check
    test_ids = set()
    test_map = {}
    for t in model.tests.tests:
        if t.test_id in test_ids:
            issues.append(
                ValidationIssue(
                    code="DUPLICATE_TEST_ID",
                    path=f"tests/{t.test_id}",
                    message=f"Duplicate test ID: {t.test_id}",
                    severity="critical",
                )
            )
        test_ids.add(t.test_id)
        test_map[t.test_id] = t

        if t.test_type in ("security", "adversarial"):
            if not t.attack_setup and not t.fault_injection:
                issues.append(
                    ValidationIssue(
                        code="FALSE_SECURITY_TEST",
                        path=f"tests/{t.test_id}",
                        message=f"Security test {t.test_id} has neither attack_setup nor fault_injection",
                        severity="critical",
                    )
                )
            if not t.assert_not:
                issues.append(
                    ValidationIssue(
                        code="MISSING_ASSERT_NOT",
                        path=f"tests/{t.test_id}",
                        message=f"Security test {t.test_id} is missing negative assertion assert_not",
                        severity="important",
                    )
                )

    # Check that requirement tests exist in test_map and match requirement
    for req in model.requirements.requirements:
        if req.phase and req.test_id:
            if req.test_id not in test_ids:
                issues.append(
                    ValidationIssue(
                        code="UNTESTED_ACCEPTANCE",
                        path=f"requirements/{req.id}",
                        message=f"Test {req.test_id} for requirement {req.id} not found in tests.json",
                        severity="critical",
                    )
                )
            else:
                test_rec = test_map[req.test_id]
                if test_rec.requirement_id != req.id:
                    issues.append(
                        ValidationIssue(
                            code="REQUIREMENT_TEST_MISMATCH",
                            path=f"requirements/{req.id}",
                            message=f"Test {req.test_id} requirement_id '{test_rec.requirement_id}' != '{req.id}'",
                            severity="critical",
                        )
                    )
                if test_rec.phase != req.phase:
                    issues.append(
                        ValidationIssue(
                            code="REQUIREMENT_PHASE_MISMATCH",
                            path=f"requirements/{req.id}",
                            message=f"Test {req.test_id} phase '{test_rec.phase}' != requirement phase '{req.phase}'",
                            severity="critical",
                        )
                    )


    # 3. Interfaces validation & duplicates
    iface_names = set()
    for iface in model.interfaces.interfaces:
        key = (iface.name, iface.owning_phase)
        if iface.name in iface_names:
            issues.append(
                ValidationIssue(
                    code="DUPLICATE_INTERFACE",
                    path=f"interfaces/{iface.name}",
                    message=f"Duplicate public interface name: {iface.name}",
                    severity="critical",
                )
            )
        iface_names.add(iface.name)

        if not iface.bounds:
            issues.append(
                ValidationIssue(
                    code="UNBOUNDED_RESOURCE",
                    path=f"interfaces/{iface.name}",
                    message=f"Interface {iface.name} has no bounded resource declaration",
                    severity="important",
                )
            )

        if iface.is_security_boundary:
            if not iface.security_test_id or iface.security_test_id not in test_ids:
                issues.append(
                    ValidationIssue(
                        code="SECURITY_TEST_MISSING",
                        path=f"interfaces/{iface.name}",
                        message=f"Security boundary interface {iface.name} has missing/invalid security test",
                        severity="critical",
                    )
                )

    # 4. File ownership
    for f in model.file_owners.files:
        if not f.owner_phase:
            issues.append(
                ValidationIssue(
                    code="UNOWNED_FILE",
                    path=f"file_owners/{f.path}",
                    message=f"File {f.path} has no owner_phase",
                    severity="critical",
                )
            )

    # 5. Phase manifest validation
    file_owner_map = {f.path: f for f in model.file_owners.files}
    iface_owner_map = {i.name: i.owning_phase for i in model.interfaces.interfaces}

    for phase in model.phase_manifest.phases:
        pid = phase.phase_id
        # Check files_created
        for fc in phase.files_created:
            if fc not in file_owner_map:
                issues.append(
                    ValidationIssue(
                        code="UNOWNED_FILE",
                        path=f"phases/{pid}/files_created/{fc}",
                        message=f"File {fc} created by {pid} is not registered in file_owners.json",
                        severity="critical",
                    )
                )
            elif file_owner_map[fc].owner_phase != pid:
                issues.append(
                    ValidationIssue(
                        code="FILE_OWNER_MISMATCH",
                        path=f"phases/{pid}/files_created/{fc}",
                        message=f"File {fc} created by {pid} is owned by {file_owner_map[fc].owner_phase}",
                        severity="critical",
                    )
                )
        # Check files_modified
        for fm in phase.files_modified:
            if fm not in file_owner_map:
                issues.append(
                    ValidationIssue(
                        code="UNOWNED_FILE",
                        path=f"phases/{pid}/files_modified/{fm}",
                        message=f"File {fm} modified by {pid} is not registered in file_owners.json",
                        severity="critical",
                    )
                )
            elif pid not in file_owner_map[fm].secondary_modifiers:
                issues.append(
                    ValidationIssue(
                        code="UNAUTHORIZED_MODIFIER",
                        path=f"phases/{pid}/files_modified/{fm}",
                        message=f"Phase {pid} modifies {fm} without being declared in secondary_modifiers",
                        severity="critical",
                    )
                )
        # Check tests
        for t in phase.tests:
            if t not in test_ids:
                issues.append(
                    ValidationIssue(
                        code="UNKNOWN_PHASE_TEST",
                        path=f"phases/{pid}/tests/{t}",
                        message=f"Test {t} in phase {pid} not found in tests.json",
                        severity="critical",
                    )
                )
        # Check output interfaces
        for out_iface in phase.output_interfaces:
            if out_iface not in iface_owner_map:
                issues.append(
                    ValidationIssue(
                        code="UNKNOWN_OUTPUT_INTERFACE",
                        path=f"phases/{pid}/output_interfaces/{out_iface}",
                        message=f"Output interface {out_iface} in phase {pid} not found in interfaces.json",
                        severity="critical",
                    )
                )
            elif iface_owner_map[out_iface] != pid:
                issues.append(
                    ValidationIssue(
                        code="INTERFACE_OWNER_MISMATCH",
                        path=f"phases/{pid}/output_interfaces/{out_iface}",
                        message=f"Output interface {out_iface} in phase {pid} owned by {iface_owner_map[out_iface]}",
                        severity="critical",
                    )
                )

    # 6. Dependencies and cycle detection
    edge_dicts = []
    for edge in model.dependencies.edges:
        u = edge.from_ if hasattr(edge, "from_") else (edge.get("from") or edge.get("from_"))
        v = edge.to if hasattr(edge, "to") else edge.get("to")
        if u and v:
            edge_dicts.append({"from": u, "to": v})

    cycles = detect_cycles(model.dependencies.components, edge_dicts)
    for c in cycles:
        issues.append(
            ValidationIssue(
                code="CIRCULAR_DEPENDENCY",
                path="dependencies",
                message=f"Circular dependency detected: {' -> '.join(c)}",
                severity="critical",
            )
        )

    # Check forbidden edges
    for f_edge in model.dependencies.forbidden_edges:
        f_from = f_edge.from_ if hasattr(f_edge, "from_") else (f_edge.get("from") or f_edge.get("from_"))
        f_to = f_edge.to if hasattr(f_edge, "to") else f_edge.get("to")
        for a_edge in model.dependencies.edges:
            a_from = a_edge.from_ if hasattr(a_edge, "from_") else (a_edge.get("from") or a_edge.get("from_"))
            a_to = a_edge.to if hasattr(a_edge, "to") else a_edge.get("to")
            if f_from == a_from and f_to == a_to:
                issues.append(
                    ValidationIssue(
                        code="ILLEGAL_DEPENDENCY",
                        path=f"dependencies/{a_from}->{a_to}",
                        message=f"Forbidden dependency edge present: {a_from} -> {a_to}",
                        severity="critical",
                    )
                )

    # 7. Freeze gate check
    if model.authority.status == "FROZEN":
        unresolved = [i for i in issues if i.severity in ("critical", "important")]
        if unresolved:
            issues.append(
                ValidationIssue(
                    code="FROZEN_WITH_OPEN_ISSUES",
                    path="authority/status",
                    message=f"Cookbook marked FROZEN but has {len(unresolved)} open critical/important issues",
                    severity="critical",
                )
            )

    return issues


def compute_freeze_counters(model: CookbookModel, issues: list[ValidationIssue]) -> dict[str, int]:
    """Compute the 10 mandatory freeze counters from model and validation issues."""
    test_ids = {t.test_id for t in model.tests.tests}

    # 1. UNMAPPED_REQUIREMENTS
    unmapped_reqs = sum(
        1 for r in model.requirements.requirements
        if not r.phase and not r.out_of_v1_rationale
    )

    # 2. UNTESTED_ACCEPTANCE_CRITERIA
    untested_crit = sum(
        1 for r in model.requirements.requirements
        if r.phase and (not r.test_id or r.test_id not in test_ids)
    )

    # 3. UNRESOLVED_PUBLIC_INTERFACES
    unresolved_ifaces = sum(
        1 for i in issues
        if i.code in ("DUPLICATE_INTERFACE", "UNKNOWN_OUTPUT_INTERFACE", "INTERFACE_OWNER_MISMATCH")
    )

    # 4. UNRESOLVED_SECURITY_INTERFACES
    unresolved_sec = sum(
        1 for i in issues
        if i.code in ("SECURITY_TEST_MISSING", "FALSE_SECURITY_TEST", "MISSING_ASSERT_NOT")
    )

    # 5. UNOWNED_FUTURE_FILES
    unowned_files = sum(
        1 for i in issues
        if i.code in ("UNOWNED_FILE", "FILE_OWNER_MISMATCH", "UNAUTHORIZED_MODIFIER")
    )

    # 6. CIRCULAR_DEPENDENCIES
    circular_deps = sum(
        1 for i in issues
        if i.code in ("CIRCULAR_DEPENDENCY", "ILLEGAL_DEPENDENCY")
    )

    # 7. UNBOUNDED_RESIDENT_STRUCTURES
    unbounded = sum(
        1 for i in issues
        if i.code == "UNBOUNDED_RESOURCE"
    )

    # 8. CRITICAL_GAPS
    critical_gaps = sum(
        1 for i in issues
        if i.severity == "critical" and i.code != "FROZEN_WITH_OPEN_ISSUES"
    )

    # 9. IMPORTANT_GAPS
    important_gaps = sum(
        1 for i in issues
        if i.severity == "important"
    )

    # 10. GUESS_REQUIRED_IMPLEMENTATION_ITEMS
    guess_required = sum(
        1 for i in issues
        if i.code in ("GUESS_REQUIRED", "VAGUE_SPECIFICATION", "PLACEHOLDER_FOUND")
    )

    return {
        "UNMAPPED_REQUIREMENTS": unmapped_reqs,
        "UNTESTED_ACCEPTANCE_CRITERIA": untested_crit,
        "UNRESOLVED_PUBLIC_INTERFACES": unresolved_ifaces,
        "UNRESOLVED_SECURITY_INTERFACES": unresolved_sec,
        "UNOWNED_FUTURE_FILES": unowned_files,
        "CIRCULAR_DEPENDENCIES": circular_deps,
        "UNBOUNDED_RESIDENT_STRUCTURES": unbounded,
        "CRITICAL_GAPS": critical_gaps,
        "IMPORTANT_GAPS": important_gaps,
        "GUESS_REQUIRED_IMPLEMENTATION_ITEMS": guess_required,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for cookbook validation."""
    import argparse
    import sys
    from tools.cookbook.model import load_cookbook

    parser = argparse.ArgumentParser(description="Deterministic Maya Implementation Cookbook Validator")
    parser.add_argument("path", nargs="?", default="Docs/ImplementationCookbook", help="Path to cookbook root directory")
    args = parser.parse_args(argv)

    root = Path(args.path)
    if not root.exists():
        print(f"Error: Directory not found: {root}")
        return 1

    try:
        model = load_cookbook(root)
    except Exception as exc:
        print(f"Error loading cookbook manifests: {exc}")
        return 1

    issues = validate_cookbook(model)
    counters = compute_freeze_counters(model, issues)

    # Print issues deterministically sorted by severity, code, path
    severity_order = {"critical": 0, "important": 1, "warning": 2}
    sorted_issues = sorted(issues, key=lambda i: (severity_order.get(i.severity, 99), i.code, i.path))

    if sorted_issues:
        print(f"VALIDATION ISSUES ({len(sorted_issues)}):")
        for issue in sorted_issues:
            print(f"  [{issue.severity.upper()}] {issue.code} at {issue.path}: {issue.message}")
    else:
        print("VALIDATION ISSUES: 0 issues found.")

    # Print freeze counters deterministically
    print("\nMANDATORY FREEZE COUNTERS:")
    for name, val in counters.items():
        print(f"  {name}: {val}")

    blockers = [i for i in issues if i.severity in ("critical", "important")]
    non_zero_counters = [k for k, v in counters.items() if v != 0]

    if blockers or non_zero_counters:
        return 1
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv[1:]))
