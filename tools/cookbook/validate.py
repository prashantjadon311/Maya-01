from collections import defaultdict
from pathlib import Path
from tools.cookbook.model import CookbookModel, ValidationIssue


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

    # Check that requirement tests exist in test_map
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

    # 6. Freeze gate check
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
