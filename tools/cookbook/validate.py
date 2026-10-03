import ast
from collections import defaultdict
import hashlib
from pathlib import Path
import re
from typing import Any

from tools.cookbook.fingerprint import fingerprint_json
from tools.cookbook.model import CookbookModel, ValidationIssue

CANONICAL_PHASES = [
    "PH000", "PH010", "PH020", "PH030", "PH040", "PH050", "PH060",
    "PH070", "PH080", "PH090", "PH100", "PH110", "PH120", "PH130",
    "PH140", "PH150", "PH160", "PH170", "PH180",
]
PHASE_ORDER = {pid: i for i, pid in enumerate(CANONICAL_PHASES)}

VAGUE_PATTERNS = [
    (re.compile(r"\bTBD\b"), "TBD"),
    (re.compile(r"\bTODO\b"), "TODO"),
    (re.compile(r"\bFIXME\b"), "FIXME"),
    (re.compile(r"\bas needed\b", re.IGNORECASE), "as needed"),
    (re.compile(r"\bif required\b", re.IGNORECASE), "if required"),
    (re.compile(r"\bif necessary\b", re.IGNORECASE), "if necessary"),
    (re.compile(r"\bor equivalent\b", re.IGNORECASE), "or equivalent"),
    (re.compile(r"\bchoose a library\b", re.IGNORECASE), "choose a library"),
    (re.compile(r"\bchoose between\b", re.IGNORECASE), "choose between"),
    (re.compile(r"\bhttpx or nvidia-riva-client\b", re.IGNORECASE), "httpx or nvidia-riva-client"),
]


def find_repo_root(start_path: Path) -> Path:
    """Find repository root containing Docs/ and app/ directories."""
    curr = start_path.resolve()
    for _ in range(5):
        if (curr / "Docs").is_dir() and (curr / "app").is_dir():
            return curr
        if curr.parent == curr:
            break
        curr = curr.parent
    return start_path.resolve()


def extract_markdown_headings(file_path: Path) -> list[str]:
    """Parse markdown headings outside fenced code blocks."""
    if not file_path.exists():
        return []
    headings = []
    in_code_block = False
    for line in file_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        m = re.match(r"^(#{1,6})\s+(.+)$", line)
        if m:
            headings.append(line.strip())
    return headings


def get_git_blob_sha(file_path: Path) -> str | None:
    """Compute git object blob sha1 (sha1('blob <size>\\0<content>'))."""
    if not file_path.exists():
        return None
    content = file_path.read_bytes()
    header = f"blob {len(content)}\0".encode("utf-8")
    return hashlib.sha1(header + content).hexdigest()


def get_function_source_sha256(file_path: Path, func_name: str) -> str | None:
    """Extract AST node for func_name and return its sha256."""
    if not file_path.exists():
        return None
    source = file_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(file_path))
    except Exception:
        return None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            segment = ast.get_source_segment(source, node)
            if segment:
                return hashlib.sha256(segment.encode("utf-8")).hexdigest()
    return None


def detect_cycles(components: list[str], edges: list[dict[str, str]]) -> list[list[str]]:
    """Detect cycles in dependency graph using DFS."""
    adj = defaultdict(list)
    for edge in edges:
        u = edge["from"] if "from" in edge else edge.get("from_")
        v = edge["to"]
        if u and v:
            adj[u].append(v)

    visited: dict[str, int] = {}  # 1 = visiting, 2 = visited
    cycles: list[list[str]] = []

    def dfs(node: str, path: list[str]):
        visited[node] = 1
        path.append(node)
        for neighbor in adj.get(node, []):
            if visited.get(neighbor) == 1:
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


def check_capsule_import(mod_name: str, repo_root: Path, registered_files: set[str], issues: list[ValidationIssue]):
    """Verify that an app import in a reference capsule points to real or planned code."""
    if mod_name.startswith("app.") or mod_name == "app":
        parts = mod_name.split(".")
        cand_file = "/".join(parts) + ".py"
        cand_pkg = "/".join(parts) + "/__init__.py"
        cand_dir = "/".join(parts)
        if (
            not (repo_root / cand_file).exists()
            and not (repo_root / cand_pkg).exists()
            and cand_file not in registered_files
            and cand_pkg not in registered_files
            and not any(rf.startswith(cand_dir + "/") for rf in registered_files)
        ):
            issues.append(
                ValidationIssue(
                    code="CAPSULE_GHOST_IMPORT",
                    path=f"17_REFERENCE_CODE_CAPSULES.md#{mod_name}",
                    message=f"Capsule imports unknown or ghost module: {mod_name}",
                    severity="critical",
                )
            )


def validate_cookbook(model: CookbookModel) -> list[ValidationIssue]:
    """Deterministically validate all cookbook models and manifest constraints."""
    issues: list[ValidationIssue] = []
    repo_root = find_repo_root(model.root_path)

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
        real_heading_counts: dict[tuple[str, str], int] = defaultdict(int)
        for doc_rel in model.authority.authority_order:
            doc_path = repo_root / doc_rel
            if doc_path.exists():
                for h in extract_markdown_headings(doc_path):
                    real_heading_counts[(doc_rel, h)] += 1

        seen_cov_counts: dict[tuple[str, str], int] = defaultdict(int)
        for sec in model.authority_coverage.sections:
            cov_key = (sec.source, sec.heading)
            seen_cov_counts[cov_key] += 1
            max_allowed = real_heading_counts.get(cov_key, 1)
            if seen_cov_counts[cov_key] > max_allowed:
                issues.append(
                    ValidationIssue(
                        code="AUTHORITY_COVERAGE_DUPLICATE",
                        path=f"authority_coverage/{sec.source}#{sec.heading}",
                        message=f"Duplicate authority coverage heading: {sec.source}#{sec.heading}",
                        severity="critical",
                    )
                )

            classification = sec.classification if hasattr(sec, "classification") and sec.classification else ("NORMATIVE" if getattr(sec, "normative", True) else "INFORMATIVE")
            if classification == "NORMATIVE":
                if not sec.requirement_ids:
                    issues.append(
                        ValidationIssue(
                            code="UNMAPPED_AUTHORITY_SECTION",
                            path=f"authority_coverage/{sec.source}#{sec.heading}",
                            message=f"Normative section '{sec.heading}' in {sec.source} has no mapped requirements",
                            severity="critical",
                        )
                    )
            elif classification == "INFORMATIVE":
                reason = sec.reason or sec.notes
                if not reason or not reason.strip():
                    issues.append(
                        ValidationIssue(
                            code="INFORMATIVE_SECTION_MISSING_REASON",
                            path=f"authority_coverage/{sec.source}#{sec.heading}",
                            message=f"Informative section '{sec.heading}' in {sec.source} has no non-empty reason",
                            severity="critical",
                        )
                    )
            elif classification == "EXPLICIT_OUT_OF_V1":
                reason = sec.reason or sec.notes
                if not reason or not reason.strip():
                    issues.append(
                        ValidationIssue(
                            code="OUT_OF_V1_MISSING_REASON",
                            path=f"authority_coverage/{sec.source}#{sec.heading}",
                            message=f"Explicit out-of-V1 section '{sec.heading}' in {sec.source} has no governing authority reason",
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

        # Dynamic authority heading extraction (run when status is not DRAFT)
        if model.authority.status != "DRAFT":
            for doc_rel in model.authority.authority_order:
                doc_path = repo_root / doc_rel
                if doc_path.exists():
                    real_headings = extract_markdown_headings(doc_path)
                    real_set = set(real_headings)
                    cov_headings_for_doc = {s.heading for s in model.authority_coverage.sections if s.source == doc_rel}

                    for rh in real_headings:
                        if rh not in cov_headings_for_doc:
                            issues.append(
                                ValidationIssue(
                                    code="AUTHORITY_HEADING_UNTRACKED",
                                    path=f"authority_coverage/{doc_rel}#{rh}",
                                    message=f"Heading '{rh}' in {doc_rel} has no entry in authority_coverage.json",
                                    severity="critical",
                                )
                            )

                    for ch in cov_headings_for_doc:
                        if ch not in real_set:
                            issues.append(
                                ValidationIssue(
                                    code="AUTHORITY_COVERAGE_STALE",
                                    path=f"authority_coverage/{doc_rel}#{ch}",
                                    message=f"Authority coverage references nonexistent heading '{ch}' in {doc_rel}",
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

        # Real test verification for VERIFIED_EXISTING
        if t.status == "VERIFIED_EXISTING":
            test_file = repo_root / t.file
            if not test_file.exists():
                issues.append(
                    ValidationIssue(
                        code="EXISTING_TEST_NOT_FOUND",
                        path=f"tests/{t.test_id}",
                        message=f"Verified test file {t.file} does not exist on disk",
                        severity="critical",
                    )
                )
            elif not t.test_function:
                issues.append(
                    ValidationIssue(
                        code="EXISTING_TEST_MISSING_FUNCTION",
                        path=f"tests/{t.test_id}",
                        message=f"Verified test {t.test_id} missing test_function",
                        severity="critical",
                    )
                )
            else:
                calc_sha = get_function_source_sha256(test_file, t.test_function)
                if calc_sha is None:
                    issues.append(
                        ValidationIssue(
                            code="EXISTING_TEST_FUNCTION_NOT_FOUND",
                            path=f"tests/{t.test_id}",
                            message=f"Test function {t.test_function} not found in {t.file}",
                            severity="critical",
                        )
                    )
                elif t.source_sha256 and calc_sha != t.source_sha256:
                    issues.append(
                        ValidationIssue(
                            code="EXISTING_TEST_HASH_MISMATCH",
                            path=f"tests/{t.test_id}",
                            message=f"Test function {t.test_function} SHA mismatch: expected {t.source_sha256}, got {calc_sha}",
                            severity="critical",
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
    seen_file_paths = set()
    for f in model.file_owners.files:
        if f.path in seen_file_paths:
            issues.append(
                ValidationIssue(
                    code="DUPLICATE_FILE_OWNER_PATH",
                    path=f"file_owners/{f.path}",
                    message=f"Duplicate file owner path: {f.path}",
                    severity="critical",
                )
            )
        seen_file_paths.add(f.path)

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

    # Precompute created files by earlier phases for required_reads verification
    sorted_phases = sorted(model.phase_manifest.phases, key=lambda p: PHASE_ORDER.get(p.phase_id, 999))
    accumulated_files: set[str] = set()
    files_created_by_earlier: dict[str, set[str]] = {}
    for sp in sorted_phases:
        files_created_by_earlier[sp.phase_id] = set(accumulated_files)
        accumulated_files.update(sp.files_created)

    # Locate reference code capsules
    capsule_file = None
    for cand in [
        model.root_path / "17_REFERENCE_CODE_CAPSULES.md",
        model.root_path.parent / "17_REFERENCE_CODE_CAPSULES.md",
    ]:
        if cand.is_file():
            capsule_file = cand
            break

    defined_capsules: set[str] = set()
    if capsule_file and capsule_file.is_file():
        cap_text = capsule_file.read_text(encoding="utf-8")
        defined_capsules = set(re.findall(r"\bCAP-[0-9A-Za-z_-]+\b", cap_text))
    else:
        # Fallback for minimal fixture to read defined capsule IDs
        repo_capsule = repo_root / "Docs" / "ImplementationCookbook" / "17_REFERENCE_CODE_CAPSULES.md"
        if repo_capsule.is_file():
            cap_text = repo_capsule.read_text(encoding="utf-8")
            defined_capsules = set(re.findall(r"\bCAP-[0-9A-Za-z_-]+\b", cap_text))

    seen_phase_ids = set()
    for phase in model.phase_manifest.phases:
        pid = phase.phase_id
        if pid in seen_phase_ids:
            issues.append(
                ValidationIssue(
                    code="DUPLICATE_PHASE_ID",
                    path=f"phase_manifest/{pid}",
                    message=f"Duplicate phase ID: {pid}",
                    severity="critical",
                )
            )
        seen_phase_ids.add(pid)

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

        # Check phase dependencies
        for dep in phase.dependencies:
            if dep == pid:
                issues.append(
                    ValidationIssue(
                        code="PHASE_SELF_DEPENDENCY",
                        path=f"phases/{pid}/dependencies/{dep}",
                        message=f"Phase {pid} cannot depend on itself",
                        severity="critical",
                    )
                )
            elif dep not in PHASE_ORDER:
                issues.append(
                    ValidationIssue(
                        code="UNKNOWN_DEPENDENCY_PHASE",
                        path=f"phases/{pid}/dependencies/{dep}",
                        message=f"Phase {pid} depends on unknown phase {dep}",
                        severity="critical",
                    )
                )
            elif PHASE_ORDER[dep] >= PHASE_ORDER.get(pid, -1):
                issues.append(
                    ValidationIssue(
                        code="OUT_OF_ORDER_PHASE_DEPENDENCY",
                        path=f"phases/{pid}/dependencies/{dep}",
                        message=f"Phase {pid} depends on later or equal phase {dep}",
                        severity="critical",
                    )
                )

        # Check required reads
        earlier_files = files_created_by_earlier.get(pid, set())
        for r_path in phase.required_reads:
            exists_on_disk = (repo_root / r_path).exists()
            created_earlier = r_path in earlier_files
            if not exists_on_disk and not created_earlier:
                issues.append(
                    ValidationIssue(
                        code="REQUIRED_READ_MISSING",
                        path=f"phases/{pid}/required_reads/{r_path}",
                        message=f"Required read '{r_path}' not found on disk or created by earlier phase",
                        severity="critical",
                    )
                )

        # Check required capsules
        for req_cap in phase.required_capsules:
            if req_cap not in defined_capsules:
                issues.append(
                    ValidationIssue(
                        code="REQUIRED_CAPSULE_MISSING",
                        path=f"phases/{pid}/required_capsules/{req_cap}",
                        message=f"Required capsule '{req_cap}' not found in 17_REFERENCE_CODE_CAPSULES.md",
                        severity="critical",
                    )
                )

    # 6. Dependencies and cycle detection
    edge_dicts = []
    seen_edges = set()
    for edge in model.dependencies.edges:
        u = edge.from_ if hasattr(edge, "from_") else (edge.get("from") or edge.get("from_"))
        v = edge.to if hasattr(edge, "to") else edge.get("to")
        if u and v:
            if (u, v) in seen_edges:
                issues.append(
                    ValidationIssue(
                        code="DUPLICATE_DEPENDENCY_EDGE",
                        path=f"dependencies/{u}->{v}",
                        message=f"Duplicate dependency edge: {u} -> {v}",
                        severity="critical",
                    )
                )
            seen_edges.add((u, v))

            if u == v:
                issues.append(
                    ValidationIssue(
                        code="PHASE_SELF_DEPENDENCY",
                        path=f"dependencies/{u}->{v}",
                        message=f"Self dependency detected: {u} -> {v}",
                        severity="critical",
                    )
                )

            if u.startswith("PH"):
                if v.startswith("PH"):
                    if v not in PHASE_ORDER:
                        issues.append(
                            ValidationIssue(
                                code="UNKNOWN_DEPENDENCY_PHASE",
                                path=f"dependencies/{u}->{v}",
                                message=f"Unknown dependency phase: {v}",
                                severity="critical",
                            )
                        )
                    elif PHASE_ORDER[v] >= PHASE_ORDER.get(u, -1) and u != v:
                        issues.append(
                            ValidationIssue(
                                code="OUT_OF_ORDER_PHASE_DEPENDENCY",
                                path=f"dependencies/{u}->{v}",
                                message=f"Phase {u} depends on later or equal phase {v}",
                                severity="critical",
                            )
                        )

            edge_dicts.append({"from": u, "to": v})

    # Run cycle detection only on non-self edges to avoid duplicate issue reporting
    non_self_edges = [e for e in edge_dicts if e["from"] != e["to"]]
    cycles = detect_cycles(model.dependencies.components, non_self_edges)
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

    # 7. AST Capsule verification (if capsule file exists)
    if capsule_file and capsule_file.is_file():
        registered_file_set = {f.path for f in model.file_owners.files}
        py_blocks = re.findall(r"```python\s*(.*?)\s*```", cap_text, re.DOTALL)
        for block in py_blocks:
            try:
                tree = ast.parse(block)
            except Exception as exc:
                issues.append(
                    ValidationIssue(
                        code="CAPSULE_SYNTAX_ERROR",
                        path="17_REFERENCE_CODE_CAPSULES.md",
                        message=f"Capsule syntax error: {exc}",
                        severity="critical",
                    )
                )
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        check_capsule_import(alias.name, repo_root, registered_file_set, issues)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        check_capsule_import(node.module, repo_root, registered_file_set, issues)

    # 8. Phase packet verification (if phases/ directory exists)
    phases_dir = None
    if (model.root_path / "phases").is_dir():
        phases_dir = model.root_path / "phases"
    elif (model.root_path.parent / "phases").is_dir():
        phases_dir = model.root_path.parent / "phases"

    if phases_dir and phases_dir.is_dir():
        manifest_phase_ids = {p.phase_id for p in model.phase_manifest.phases if p.phase_id.startswith("PH") and int(p.phase_id[2:]) >= 50}
        for pid in sorted(manifest_phase_ids):
            packet_path = phases_dir / f"{pid}.md"
            if not packet_path.exists():
                issues.append(
                    ValidationIssue(
                        code="PHASE_PACKET_MISSING",
                        path=f"phases/{pid}.md",
                        message=f"Phase packet {pid}.md missing in {phases_dir}",
                        severity="critical",
                    )
                )
                continue
            packet_content = packet_path.read_text(encoding="utf-8")

            # Check vague phrases
            for pat, phrase_name in VAGUE_PATTERNS:
                if pat.search(packet_content):
                    issues.append(
                        ValidationIssue(
                            code="VAGUE_SPECIFICATION",
                            path=f"phases/{pid}.md",
                            message=f"Phase packet {pid}.md contains forbidden vague phrase: '{phrase_name}'",
                            severity="critical",
                        )
                    )

            # Check 36 numbered sections
            sec_matches = list(re.finditer(r"^##\s+(\d+)[\.\s]+(.*)$", packet_content, re.MULTILINE))
            found_nums = [int(m.group(1)) for m in sec_matches]

            missing = [i for i in range(1, 37) if i not in found_nums]
            for m_num in missing:
                issues.append(
                    ValidationIssue(
                        code="PHASE_SECTION_MISSING",
                        path=f"phases/{pid}.md#Section-{m_num}",
                        message=f"Phase packet {pid}.md missing numbered section {m_num}",
                        severity="critical",
                    )
                )

            seen_sec_nums = set()
            for s_num in found_nums:
                if s_num in seen_sec_nums:
                    issues.append(
                        ValidationIssue(
                            code="PHASE_SECTION_DUPLICATE",
                            path=f"phases/{pid}.md#Section-{s_num}",
                            message=f"Phase packet {pid}.md has duplicate numbered section {s_num}",
                            severity="critical",
                        )
                    )
                seen_sec_nums.add(s_num)

            if found_nums and found_nums != sorted(found_nums):
                issues.append(
                    ValidationIssue(
                        code="PHASE_SECTION_ORDER_INVALID",
                        path=f"phases/{pid}.md",
                        message=f"Phase packet {pid}.md numbered sections are out of order: {found_nums}",
                        severity="critical",
                    )
                )

    # 9. Freeze gate check & fingerprint verification
    if model.authority.status == "FROZEN":
        machine_dir = model.root_path / "machine" if (model.root_path / "machine").is_dir() else model.root_path

        # Check interface hash
        if model.authority.interface_hash:
            iface_path = machine_dir / "interfaces.json"
            if iface_path.exists():
                actual_iface_fp = fingerprint_json(iface_path)
                if actual_iface_fp != model.authority.interface_hash:
                    issues.append(
                        ValidationIssue(
                            code="INTERFACE_HASH_MISMATCH",
                            path="authority/interface_hash",
                            message=f"interfaces.json hash mismatch: expected {model.authority.interface_hash}, got {actual_iface_fp}",
                            severity="critical",
                        )
                    )

        # Check requirement map hash
        if model.authority.requirement_map_hash:
            req_path = machine_dir / "requirements.json"
            if req_path.exists():
                actual_req_fp = fingerprint_json(req_path)
                if actual_req_fp != model.authority.requirement_map_hash:
                    issues.append(
                        ValidationIssue(
                            code="REQUIREMENT_MAP_HASH_MISMATCH",
                            path="authority/requirement_map_hash",
                            message=f"requirements.json hash mismatch: expected {model.authority.requirement_map_hash}, got {actual_req_fp}",
                            severity="critical",
                        )
                    )

        # Check phase manifest hash
        if model.authority.phase_manifest_hash:
            pm_path = machine_dir / "phase_manifest.json"
            if pm_path.exists():
                actual_pm_fp = fingerprint_json(pm_path)
                if actual_pm_fp != model.authority.phase_manifest_hash:
                    issues.append(
                        ValidationIssue(
                            code="PHASE_MANIFEST_HASH_MISMATCH",
                            path="authority/phase_manifest_hash",
                            message=f"phase_manifest.json hash mismatch: expected {model.authority.phase_manifest_hash}, got {actual_pm_fp}",
                            severity="critical",
                        )
                    )

        # Check authority doc blob SHAs
        for doc_rel, expected_sha in model.authority.blob_shas.items():
            doc_path = repo_root / doc_rel
            actual_sha = get_git_blob_sha(doc_path)
            if actual_sha is not None and actual_sha != expected_sha:
                issues.append(
                    ValidationIssue(
                        code="AUTHORITY_BLOB_HASH_MISMATCH",
                        path=f"authority/blob_shas/{doc_rel}",
                        message=f"Blob SHA mismatch for {doc_rel}: expected {expected_sha}, got {actual_sha}",
                        severity="critical",
                    )
                )

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
        if i.code in ("DUPLICATE_INTERFACE", "UNKNOWN_OUTPUT_INTERFACE", "INTERFACE_OWNER_MISMATCH", "PHASE_PACKET_INTERFACE_MISMATCH")
    )

    # 4. UNRESOLVED_SECURITY_INTERFACES
    unresolved_sec = sum(
        1 for i in issues
        if i.code in ("SECURITY_TEST_MISSING", "FALSE_SECURITY_TEST", "MISSING_ASSERT_NOT")
    )

    # 5. UNOWNED_FUTURE_FILES
    unowned_files = sum(
        1 for i in issues
        if i.code in ("UNOWNED_FILE", "FILE_OWNER_MISMATCH", "UNAUTHORIZED_MODIFIER", "DUPLICATE_FILE_OWNER_PATH", "PHASE_PACKET_MANIFEST_FILE_MISMATCH")
    )

    # 6. CIRCULAR_DEPENDENCIES
    circular_deps = sum(
        1 for i in issues
        if i.code in ("CIRCULAR_DEPENDENCY", "ILLEGAL_DEPENDENCY", "PHASE_SELF_DEPENDENCY", "UNKNOWN_DEPENDENCY_PHASE", "OUT_OF_ORDER_PHASE_DEPENDENCY", "DUPLICATE_DEPENDENCY_EDGE")
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
