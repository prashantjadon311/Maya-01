import ast
from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
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

SECTION_HEADING_RE = re.compile(
    r"^##\s+(\d+)\.\s+(.*)$",
    re.MULTILINE,
)

BASE_SHA_PIN_RE = re.compile(
    r"Base SHA pinned at [` ]?[0-9a-f]{40}",
    re.IGNORECASE,
)

GENERIC_PLACEHOLDER_PATTERNS = [
    re.compile(
        r"Standard exact algorithms / security invariants contract",
        re.IGNORECASE,
    ),
    re.compile(
        r"Standard failure cases / edge cases contract",
        re.IGNORECASE,
    ),
    re.compile(
        r"Standard fakes / fixtures contract",
        re.IGNORECASE,
    ),
    re.compile(
        r"Standard adversarial / negative tests contract",
        re.IGNORECASE,
    ),
    re.compile(
        r"verified and enforced per phase manifest",
        re.IGNORECASE,
    ),
]

TEST_ID_RE = re.compile(r"\btest_[A-Za-z0-9_]+\b")
CAPSULE_RE = re.compile(r"\bCAP-[0-9]+[A-Z]?\b")


@dataclass(frozen=True)
class PacketSection:
    number: int
    title: str
    body: str


@dataclass(frozen=True)
class PacketContract:
    files_created: frozenset[str]
    files_modified: frozenset[str]
    files_forbidden: frozenset[str]
    dependencies: frozenset[str]
    output_interfaces: frozenset[str]
    tests: frozenset[str]
    required_capsules: frozenset[str]


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


def sha256_file(path: Path) -> str:
    """Compute sha256 hex digest of file bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze_artifact_paths(cookbook_root: Path) -> list[Path]:
    """Return all deterministic paths included in the freeze artifact bundle."""
    paths: list[Path] = []

    # Machine contracts except authority.json, which contains the hashes.
    machine = cookbook_root / "machine"
    if machine.is_dir():
        for p in sorted(machine.glob("*.json")):
            if p.name != "authority.json":
                paths.append(p)
    else:
        for p in sorted(cookbook_root.glob("*.json")):
            if p.name != "authority.json":
                paths.append(p)

    # Phase packets.
    phases_dir = cookbook_root / "phases"
    if phases_dir.is_dir():
        paths.extend(sorted(phases_dir.glob("PH*.md")))

    # Critical human-readable contracts.
    for name in [
        "01_AUTHORITY_MAP.md",
        "02_REQUIREMENTS.md",
        "03_CURRENT_CODE_MODEL.md",
        "04_FINAL_SYSTEM_ARCHITECTURE.md",
        "05_TRUST_BOUNDARIES.md",
        "06_STATE_OWNERSHIP.md",
        "07_OBJECT_LIFETIMES.md",
        "08_COMPOSITION_ROOT.md",
        "09_PUBLIC_INTERFACES.md",
        "10_DATA_SCHEMAS.md",
        "11_STATE_MACHINES.md",
        "12_CONCURRENCY.md",
        "13_ERRORS_RETRIES_CANCELLATION.md",
        "14_RESOURCE_BUDGET.md",
        "15_SECURITY_MODEL.md",
        "16_FILE_OWNERSHIP.md",
        "17_REFERENCE_CODE_CAPSULES.md",
        "18_TEST_FIXTURES.md",
        "19_TEST_MATRIX.md",
        "20_FAILURE_MATRIX.md",
        "21_END_TO_END_JOURNEYS.md",
    ]:
        p = cookbook_root / name
        if p.exists():
            paths.append(p)

    execution = cookbook_root / "execution"
    if execution.is_dir():
        paths.extend(sorted(execution.glob("*.md")))
        paths.extend(sorted(execution.glob("*.json")))

    return paths


def compute_artifact_hashes(
    repo_root: Path,
    cookbook_root: Path,
) -> dict[str, str]:
    """Compute relative-path to sha256 map for all freeze bundle artifacts."""
    result: dict[str, str] = {}

    resolved_repo = repo_root.resolve()
    for path in freeze_artifact_paths(cookbook_root):
        rel = path.resolve().relative_to(resolved_repo).as_posix()
        result[rel] = sha256_file(path)

    return dict(sorted(result.items()))


def compute_artifact_bundle_hash(
    artifact_hashes: dict[str, str],
) -> str:
    """Compute composite sha256 of all artifact hashes in canonical JSON format."""
    payload = json.dumps(
        artifact_hashes,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    return hashlib.sha256(payload).hexdigest()


def parse_numbered_sections(text: str) -> dict[int, PacketSection]:
    """Parse 36 numbered sections from phase packet markdown."""
    matches = list(SECTION_HEADING_RE.finditer(text))
    sections: dict[int, PacketSection] = {}

    for idx, match in enumerate(matches):
        number = int(match.group(1))
        title = match.group(2).strip()

        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)

        body = text[start:end].strip()

        if number in sections:
            raise ValueError(f"duplicate section {number}")

        sections[number] = PacketSection(
            number=number,
            title=title,
            body=body,
        )

    return sections


def _normalize_bullet_value(raw: str) -> str:
    value = raw.strip()
    if value.startswith("`") and value.endswith("`"):
        value = value[1:-1]
    return value.strip()


def parse_bullet_values(section_body: str) -> frozenset[str]:
    """Extract bullet items as a set of normalized strings."""
    if re.search(r"^\s*None(?:\.|\s|\(|$)", section_body, re.IGNORECASE):
        return frozenset()

    values: set[str] = set()

    for line in section_body.splitlines():
        match = re.match(r"^\s*-\s+(.+?)\s*$", line)
        if not match:
            continue

        raw_item = match.group(1).strip()
        code_match = re.match(r"^`([^`]+)`", raw_item)
        if code_match:
            value = code_match.group(1).strip()
        else:
            value = _normalize_bullet_value(raw_item)
            if ":" in value:
                value = value.split(":", 1)[0].strip()

        values.add(value)

    return frozenset(values)


def parse_packet_contract(
    packet_text: str,
) -> tuple[dict[int, PacketSection], PacketContract]:
    """Parse section map and structured contract from phase packet text."""
    sections = parse_numbered_sections(packet_text)

    tests = set(TEST_ID_RE.findall(sections.get(25, PacketSection(25, "", "")).body))
    tests.update(TEST_ID_RE.findall(sections.get(26, PacketSection(26, "", "")).body))

    capsules = set(CAPSULE_RE.findall(sections.get(14, PacketSection(14, "", "")).body))

    return sections, PacketContract(
        files_created=parse_bullet_values(sections.get(5, PacketSection(5, "", "")).body),
        files_modified=parse_bullet_values(sections.get(6, PacketSection(6, "", "")).body),
        files_forbidden=parse_bullet_values(sections.get(7, PacketSection(7, "", "")).body),
        dependencies=parse_bullet_values(sections.get(8, PacketSection(8, "", "")).body),
        output_interfaces=parse_bullet_values(sections.get(11, PacketSection(11, "", "")).body),
        tests=frozenset(tests),
        required_capsules=frozenset(capsules),
    )


def compare_packet_to_manifest(
    *,
    phase: Any,
    contract: PacketContract,
    issues: list[ValidationIssue],
) -> None:
    """Compare parsed packet contract with phase manifest item."""
    checks = [
        (
            "PHASE_PACKET_FILES_CREATED_MISMATCH",
            contract.files_created,
            frozenset(phase.files_created),
        ),
        (
            "PHASE_PACKET_FILES_MODIFIED_MISMATCH",
            contract.files_modified,
            frozenset(phase.files_modified),
        ),
        (
            "PHASE_PACKET_FILES_FORBIDDEN_MISMATCH",
            contract.files_forbidden,
            frozenset(phase.files_forbidden_to_modify),
        ),
        (
            "PHASE_PACKET_DEPENDENCY_MISMATCH",
            contract.dependencies,
            frozenset(phase.dependencies),
        ),
        (
            "PHASE_PACKET_INTERFACE_MISMATCH",
            contract.output_interfaces,
            frozenset(phase.output_interfaces),
        ),
        (
            "PHASE_PACKET_TEST_MISMATCH",
            contract.tests,
            frozenset(phase.tests),
        ),
        (
            "PHASE_PACKET_CAPSULE_MISMATCH",
            contract.required_capsules,
            frozenset(phase.required_capsules),
        ),
    ]

    for code, packet_value, manifest_value in checks:
        if packet_value != manifest_value:
            issues.append(
                ValidationIssue(
                    code=code,
                    path=f"phases/{phase.phase_id}.md",
                    message=(
                        f"packet={sorted(packet_value)} "
                        f"manifest={sorted(manifest_value)}"
                    ),
                    severity="critical",
                )
            )


def validate_section_content(
    phase_id: str,
    sections: dict[int, PacketSection],
    issues: list[ValidationIssue],
) -> None:
    """Ensure packet sections contain phase-specific implementation rather than generic placeholders."""
    for number, section in sections.items():
        for pattern in GENERIC_PLACEHOLDER_PATTERNS:
            if pattern.search(section.body):
                issues.append(
                    ValidationIssue(
                        code="PLACEHOLDER_SECTION_CONTENT",
                        path=f"phases/{phase_id}.md#section-{number}",
                        message=(
                            f"Section {number} contains generic placeholder "
                            "instead of phase-specific implementation contract"
                        ),
                        severity="critical",
                    )
                )


def positive_phase_text(
    sections: dict[int, PacketSection],
    *,
    include: set[int] | None = None,
) -> str:
    """Concatenate positive implementation sections (excluding negative/adversarial sections by default)."""
    if include is None:
        include = set(range(1, 35)) - {26}

    return "\n".join(
        sections[n].body
        for n in sorted(include)
        if n in sections
    )


def parse_packet(
    phase_ref: str | Path,
    cookbook_root: Path | None = None,
) -> dict[int, PacketSection]:
    """Parse a phase packet by ID or path and return its section map."""
    if isinstance(phase_ref, Path):
        path = phase_ref
    elif str(phase_ref).endswith(".md"):
        path = Path(phase_ref)
    else:
        root = cookbook_root or (Path(__file__).resolve().parent.parent.parent / "Docs" / "ImplementationCookbook")
        path = root / "phases" / f"{phase_ref}.md"

    text = path.read_text(encoding="utf-8")
    return parse_numbered_sections(text)


def extract_capsule_python(capsule_id: str, cookbook_root: Path | None = None) -> str:
    """Extract python source code blocks for a capsule from 17_REFERENCE_CODE_CAPSULES.md."""
    root = cookbook_root or (Path(__file__).resolve().parent.parent.parent / "Docs" / "ImplementationCookbook")
    path = root / "17_REFERENCE_CODE_CAPSULES.md"
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    pattern = rf"##+.*?\b{re.escape(capsule_id)}\b(.*?)(?=\n##+|\Z)"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return ""
    block = match.group(1)
    py_blocks = re.findall(r"```python\s*(.*?)\s*```", block, re.DOTALL)
    return "\n".join(py_blocks)


def verify_existing_test_collectability(
    repo_root: Path,
    tests: Any,
) -> list[ValidationIssue]:
    """Collect VERIFIED_EXISTING pytest node IDs to ensure they are valid and collectable."""
    issues: list[ValidationIssue] = []
    by_file: dict[str, list[str]] = defaultdict(list)

    for test in tests:
        if getattr(test, "status", None) != "VERIFIED_EXISTING":
            continue

        if not getattr(test, "pytest_nodeid", None) or not getattr(test, "test_function", None):
            issues.append(
                ValidationIssue(
                    code="VERIFIED_TEST_NODEID_MISSING",
                    path=f"tests/{getattr(test, 'test_id', 'unknown')}",
                    message="VERIFIED_EXISTING test has no pytest_nodeid/function",
                    severity="critical",
                )
            )
            continue

        expected_prefix = f"{test.file}::{test.test_function}"

        # Parametrized node IDs may append [case].
        if not test.pytest_nodeid.startswith(expected_prefix):
            issues.append(
                ValidationIssue(
                    code="VERIFIED_TEST_NODEID_MISMATCH",
                    path=f"tests/{test.test_id}",
                    message=(
                        f"nodeid={test.pytest_nodeid!r}, "
                        f"expected prefix={expected_prefix!r}"
                    ),
                    severity="critical",
                )
            )
            continue

        if (repo_root / test.file).exists():
            by_file[test.file].append(test.pytest_nodeid)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)

    for file_name, nodeids in sorted(by_file.items()):
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "--collect-only",
                    "-q",
                    *nodeids,
                ],
                cwd=repo_root,
                env=env,
                text=True,
                capture_output=True,
            )

            if result.returncode != 0:
                issues.append(
                    ValidationIssue(
                        code="VERIFIED_TEST_NOT_COLLECTABLE",
                        path=file_name,
                        message=result.stdout[-2000:] + result.stderr[-2000:],
                        severity="critical",
                    )
                )
        except Exception as exc:
            issues.append(
                ValidationIssue(
                    code="VERIFIED_TEST_NOT_COLLECTABLE",
                    path=file_name,
                    message=f"Collection execution error: {exc}",
                    severity="critical",
                )
            )

    return issues


def validate_cookbook(model: CookbookModel) -> list[ValidationIssue]:
    """Deterministically validate all cookbook models and manifest constraints."""
    issues: list[ValidationIssue] = []
    repo_root = find_repo_root(model.root_path)

    # 1. Tests indexing and verification
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

    # 1b. Batch test collectability check
    issues.extend(verify_existing_test_collectability(repo_root, model.tests.tests))

    # 2. Requirement validation & multi-test evidence mapping
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
            if not req.test_ids:
                issues.append(
                    ValidationIssue(
                        code="UNTESTED_ACCEPTANCE",
                        path=f"requirements/{req.id}",
                        message=f"Requirement {req.id} in phase {req.phase} has no test_ids",
                        severity="critical",
                    )
                )
            else:
                for test_id in req.test_ids:
                    if test_id not in test_ids:
                        issues.append(
                            ValidationIssue(
                                code="UNTESTED_ACCEPTANCE",
                                path=f"requirements/{req.id}",
                                message=f"Test {test_id} for requirement {req.id} not found in tests.json",
                                severity="critical",
                            )
                        )
                    else:
                        test_rec = test_map[test_id]
                        if test_rec.requirement_id != req.id:
                            issues.append(
                                ValidationIssue(
                                    code="REQUIREMENT_TEST_MISMATCH",
                                    path=f"requirements/{req.id}",
                                    message=f"Test {test_id} requirement_id '{test_rec.requirement_id}' != '{req.id}'",
                                    severity="critical",
                                )
                            )
                        if test_rec.phase != req.phase:
                            issues.append(
                                ValidationIssue(
                                    code="REQUIREMENT_PHASE_MISMATCH",
                                    path=f"requirements/{req.id}",
                                    message=f"Test {test_id} phase '{test_rec.phase}' != requirement phase '{req.phase}'",
                                    severity="critical",
                                )
                            )

    # 3. Authority coverage check
    if model.authority_coverage is not None:
        real_heading_counts: dict[tuple[str, str], int] = defaultdict(int)
        headings_by_source: dict[str, list[str]] = defaultdict(list)
        for doc_rel in model.authority.authority_order:
            doc_path = repo_root / doc_rel
            if doc_path.exists():
                headings = extract_markdown_headings(doc_path)
                headings_by_source[doc_rel] = headings
                for h in headings:
                    real_heading_counts[(doc_rel, h)] += 1

        authority_rank = {doc: i for i, doc in enumerate(model.authority.authority_order)}

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

            classification = getattr(sec, "classification", "NORMATIVE")
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

                if not sec.exclusion_source or not sec.exclusion_heading:
                    issues.append(
                        ValidationIssue(
                            code="OUT_OF_V1_AUTHORITY_UNVERIFIED",
                            path=f"authority_coverage/{sec.source}#{sec.heading}",
                            message=f"Explicit out-of-V1 section '{sec.heading}' missing exclusion_source or exclusion_heading",
                            severity="critical",
                        )
                    )
                else:
                    source_headings = set(headings_by_source.get(sec.exclusion_source, []))
                    if sec.exclusion_heading not in source_headings:
                        issues.append(
                            ValidationIssue(
                                code="OUT_OF_V1_AUTHORITY_UNVERIFIED",
                                path=f"authority_coverage/{sec.source}#{sec.heading}",
                                message=f"Exclusion heading '{sec.exclusion_heading}' not found in exclusion source '{sec.exclusion_source}'",
                                severity="critical",
                            )
                        )
                    source_rank = authority_rank.get(sec.source, 10_000)
                    exclusion_rank = authority_rank.get(sec.exclusion_source, 10_000)
                    if exclusion_rank > source_rank:
                        issues.append(
                            ValidationIssue(
                                code="OUT_OF_V1_AUTHORITY_UNVERIFIED",
                                path=f"authority_coverage/{sec.source}#{sec.heading}",
                                message=f"Exclusion source '{sec.exclusion_source}' (rank {exclusion_rank}) has lower authority than source '{sec.source}' (rank {source_rank})",
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

    # 4. Interfaces validation & duplicates
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

    # 5. Resource bounds validation
    bound_ids = set()
    if model.resource_bounds is not None:
        for bound in model.resource_bounds.bounds:
            if bound.id in bound_ids:
                issues.append(
                    ValidationIssue(
                        code="DUPLICATE_RESOURCE_BOUND_ID",
                        path=f"resource_bounds/{bound.id}",
                        message=f"Duplicate resource bound ID: {bound.id}",
                        severity="critical",
                    )
                )
            bound_ids.add(bound.id)

            if not bound.owner or not bound.owner.strip():
                issues.append(
                    ValidationIssue(
                        code="RESOURCE_BOUND_MISSING_OWNER",
                        path=f"resource_bounds/{bound.id}",
                        message=f"Resource bound {bound.id} has empty owner",
                        severity="critical",
                    )
                )

            if bound.phase not in CANONICAL_PHASES:
                issues.append(
                    ValidationIssue(
                        code="UNKNOWN_RESOURCE_BOUND_PHASE",
                        path=f"resource_bounds/{bound.id}",
                        message=f"Resource bound {bound.id} has unknown phase: {bound.phase}",
                        severity="critical",
                    )
                )

            if bound.max_count is None and bound.max_bytes is None and bound.timeout_seconds is None:
                issues.append(
                    ValidationIssue(
                        code="RESOURCE_BOUND_MISSING_NUMERIC_LIMIT",
                        path=f"resource_bounds/{bound.id}",
                        message=f"Resource bound {bound.id} must declare at least one numeric limit (max_count, max_bytes, timeout_seconds)",
                        severity="critical",
                    )
                )

            if not bound.overflow_policy or not bound.overflow_policy.strip():
                issues.append(
                    ValidationIssue(
                        code="RESOURCE_BOUND_MISSING_OVERFLOW_POLICY",
                        path=f"resource_bounds/{bound.id}",
                        message=f"Resource bound {bound.id} has empty overflow policy",
                        severity="critical",
                    )
                )

        # Check that interface resource bounds exist
        for iface in model.interfaces.interfaces:
            for bound_id in iface.resource_bound_ids:
                if bound_id not in bound_ids:
                    issues.append(
                        ValidationIssue(
                            code="UNKNOWN_RESOURCE_BOUND_REFERENCE",
                            path=f"interfaces/{iface.name}/{bound_id}",
                            message=f"Interface {iface.name} references unknown resource bound ID: {bound_id}",
                            severity="critical",
                        )
                    )

    # 6. File ownership
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

    # 7. Phase manifest validation
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

    # 8. Dependencies and cycle detection
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

    # 9. AST Capsule verification (if capsule file exists)
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

    # 10. Phase packet verification (if phases/ directory exists)
    phases_dir = None
    if (model.root_path / "phases").is_dir():
        phases_dir = model.root_path / "phases"
    elif (model.root_path.parent / "phases").is_dir():
        phases_dir = model.root_path.parent / "phases"

    if phases_dir and phases_dir.is_dir():
        manifest_phase_ids = {p.phase_id for p in model.phase_manifest.phases if p.phase_id.startswith("PH") and int(p.phase_id[2:]) >= 50}
        phase_obj_map = {p.phase_id: p for p in model.phase_manifest.phases}
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

            # Check for stale phase base SHA pin
            if BASE_SHA_PIN_RE.search(packet_content):
                issues.append(
                    ValidationIssue(
                        code="STALE_PHASE_BASE_SHA",
                        path=f"phases/{pid}.md",
                        message=f"Phase packet {pid}.md contains hardcoded pre-merge base SHA pin",
                        severity="critical",
                    )
                )

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

            # Parse packet contract and compare to manifest
            try:
                sections, contract = parse_packet_contract(packet_content)
                validate_section_content(pid, sections, issues)
                phase_obj = phase_obj_map.get(pid)
                if phase_obj:
                    compare_packet_to_manifest(phase=phase_obj, contract=contract, issues=issues)
            except Exception as exc:
                issues.append(
                    ValidationIssue(
                        code="PHASE_PACKET_PARSE_ERROR",
                        path=f"phases/{pid}.md",
                        message=f"Failed to parse packet contract for {pid}.md: {exc}",
                        severity="critical",
                    )
                )

    # 11. Freeze gate check & fingerprint verification
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

        # Check artifact hashes
        if model.authority.artifact_hashes:
            actual_hashes = compute_artifact_hashes(repo_root, model.root_path)
            for exp_rel, exp_hash in model.authority.artifact_hashes.items():
                if exp_rel not in actual_hashes:
                    issues.append(
                        ValidationIssue(
                            code="FREEZE_ARTIFACT_MISSING",
                            path=f"authority/artifact_hashes/{exp_rel}",
                            message=f"Freeze artifact missing from disk: {exp_rel}",
                            severity="critical",
                        )
                    )
                elif actual_hashes[exp_rel] != exp_hash:
                    issues.append(
                        ValidationIssue(
                            code="FREEZE_ARTIFACT_HASH_MISMATCH",
                            path=f"authority/artifact_hashes/{exp_rel}",
                            message=f"Artifact hash mismatch for {exp_rel}: expected {exp_hash}, got {actual_hashes[exp_rel]}",
                            severity="critical",
                        )
                    )

            for act_rel in actual_hashes:
                if act_rel not in model.authority.artifact_hashes:
                    issues.append(
                        ValidationIssue(
                            code="FREEZE_ARTIFACT_UNEXPECTED",
                            path=f"authority/artifact_hashes/{act_rel}",
                            message=f"Unexpected artifact present in cookbook but missing from freeze hashes: {act_rel}",
                            severity="critical",
                        )
                    )

        # Check artifact bundle hash
        if model.authority.artifact_bundle_hash:
            actual_hashes = compute_artifact_hashes(repo_root, model.root_path)
            actual_bundle_hash = compute_artifact_bundle_hash(actual_hashes)
            if actual_bundle_hash != model.authority.artifact_bundle_hash:
                issues.append(
                    ValidationIssue(
                        code="FREEZE_BUNDLE_HASH_MISMATCH",
                        path="authority/artifact_bundle_hash",
                        message=f"Artifact bundle hash mismatch: expected {model.authority.artifact_bundle_hash}, got {actual_bundle_hash}",
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
        if r.phase and (not r.test_ids or not all(tid in test_ids for tid in r.test_ids))
    )

    # 3. UNRESOLVED_PUBLIC_INTERFACES
    unresolved_ifaces = sum(
        1 for i in issues
        if i.code in (
            "DUPLICATE_INTERFACE",
            "UNKNOWN_OUTPUT_INTERFACE",
            "INTERFACE_OWNER_MISMATCH",
            "PHASE_PACKET_INTERFACE_MISMATCH",
            "UNKNOWN_RESOURCE_BOUND_REFERENCE",
        )
    )

    # 4. UNRESOLVED_SECURITY_INTERFACES
    unresolved_sec = sum(
        1 for i in issues
        if i.code in ("SECURITY_TEST_MISSING", "FALSE_SECURITY_TEST", "MISSING_ASSERT_NOT")
    )

    # 5. UNOWNED_FUTURE_FILES
    unowned_files = sum(
        1 for i in issues
        if i.code in (
            "UNOWNED_FILE",
            "FILE_OWNER_MISMATCH",
            "UNAUTHORIZED_MODIFIER",
            "DUPLICATE_FILE_OWNER_PATH",
            "PHASE_PACKET_MANIFEST_FILE_MISMATCH",
            "PHASE_PACKET_FILES_CREATED_MISMATCH",
            "PHASE_PACKET_FILES_MODIFIED_MISMATCH",
            "PHASE_PACKET_FILES_FORBIDDEN_MISMATCH",
        )
    )

    # 6. CIRCULAR_DEPENDENCIES
    circular_deps = sum(
        1 for i in issues
        if i.code in (
            "CIRCULAR_DEPENDENCY",
            "ILLEGAL_DEPENDENCY",
            "PHASE_SELF_DEPENDENCY",
            "UNKNOWN_DEPENDENCY_PHASE",
            "OUT_OF_ORDER_PHASE_DEPENDENCY",
            "DUPLICATE_DEPENDENCY_EDGE",
            "PHASE_PACKET_DEPENDENCY_MISMATCH",
        )
    )

    # 7. UNBOUNDED_RESIDENT_STRUCTURES
    unbounded = sum(
        1 for i in issues
        if i.code in (
            "UNBOUNDED_RESOURCE",
            "RESOURCE_BOUND_MISSING_NUMERIC_LIMIT",
            "RESOURCE_BOUND_MISSING_OWNER",
            "RESOURCE_BOUND_MISSING_OVERFLOW_POLICY",
            "DUPLICATE_RESOURCE_BOUND_ID",
            "UNKNOWN_RESOURCE_BOUND_PHASE",
        )
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
        if i.code in (
            "GUESS_REQUIRED",
            "VAGUE_SPECIFICATION",
            "PLACEHOLDER_FOUND",
            "PLACEHOLDER_SECTION_CONTENT",
            "STALE_PHASE_BASE_SHA",
        )
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
