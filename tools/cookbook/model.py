from pathlib import Path
from typing import Literal, Any
import json
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ValidationIssue(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    code: str
    path: str
    message: str
    severity: Literal["critical", "important", "warning"]


class InterfaceParam(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    name: str
    type: str


class RequirementItem(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: str
    source: str
    category: str
    description: str

    phase: str | None = None
    component: str | None = None
    file: str | None = None
    symbol: str | None = None

    # FINAL: one requirement may require multiple evidence records.
    test_ids: list[str] = Field(default_factory=list)

    acceptance_evidence: str | None = None
    out_of_v1_rationale: str | None = None

    @model_validator(mode="before")
    @classmethod
    def migrate_test_id(cls, data: Any) -> Any:
        if isinstance(data, dict) and "test_id" in data:
            val = data.pop("test_id")
            if "test_ids" not in data:
                data["test_ids"] = [val] if val else []
        return data

    @property
    def test_id(self) -> str | None:
        return self.test_ids[0] if self.test_ids else None


class RequirementsModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    requirements: list[RequirementItem]


class SymbolItem(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    symbol: str
    file: str
    type: str
    status: Literal["KEEP", "EXTEND", "REFACTOR_IN_PLACE", "REPLACE_LATER", "DEPRECATED", "DO_NOT_TOUCH"]
    callers: list[str] = Field(default_factory=list)
    callees: list[str] = Field(default_factory=list)
    state_owned: list[str] = Field(default_factory=list)
    side_effects: list[str] = Field(default_factory=list)
    security_role: str = ""
    resource_ownership: str = ""
    test_coverage: list[str] = Field(default_factory=list)


class SymbolsModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    symbols: list[SymbolItem]


class InterfaceItem(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    name: str
    owning_phase: str
    file: str
    signature: str

    inputs: list[InterfaceParam] = Field(default_factory=list)
    output: str

    preconditions: list[str] = Field(default_factory=list)
    postconditions: list[str] = Field(default_factory=list)

    is_security_boundary: bool = False
    security_test_id: str | None = None

    # Human-readable summary.
    bounds: str | None = None

    # Machine-verifiable bounds.
    resource_bound_ids: list[str] = Field(default_factory=list)

    timeout_seconds: float | None = None
    cancellation: str | None = None
    idempotent: bool = False
    audit_code: str | None = None
    errors: list[str] = Field(default_factory=list)


class InterfacesModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    interfaces: list[InterfaceItem]


class FileOwnerItem(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    path: str
    owner_phase: str
    secondary_modifiers: list[str] = Field(default_factory=list)
    purpose: str
    allowed_contents: list[str] = Field(default_factory=list)
    forbidden_contents: list[str] = Field(default_factory=list)


class FileOwnersModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    files: list[FileOwnerItem]


class PhaseManifestItem(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    phase_id: str
    title: str
    status: Literal["PLANNED", "IN_PROGRESS", "COMPLETED", "FROZEN", "BLOCKED_OPEN_DESIGN_DECISION"]
    required_reads: list[str] = Field(default_factory=list)
    files_created: list[str] = Field(default_factory=list)
    files_modified: list[str] = Field(default_factory=list)
    files_forbidden_to_modify: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    required_capsules: list[str] = Field(default_factory=list)
    tests: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    output_interfaces: list[str] = Field(default_factory=list)
    stop_conditions: list[str] = Field(default_factory=list)


class PhaseManifestModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    phases: list[PhaseManifestItem]


class TestRecipeItem(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    test_id: str
    phase: str
    requirement_id: str
    file: str

    test_type: Literal[
        "unit",
        "integration",
        "security",
        "adversarial",
        "resource",
        "manual",
    ]

    status: Literal[
        "VERIFIED_EXISTING",
        "PLANNED_FUTURE_TEST",
        "MANUAL_ACCEPTANCE",
    ] = "PLANNED_FUTURE_TEST"

    fixture: str
    attack_setup: str | None = None
    fault_injection: str | None = None
    act: str
    assert_positive: str
    assert_not: str | None = None
    verification_command: str

    test_function: str | None = None
    pytest_nodeid: str | None = None
    source_sha256: str | None = None

    component: str | None = None
    evidence_kind: str | None = None


class TestsModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    tests: list[TestRecipeItem]


class AuthorityCoverageItem(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    source: str
    heading: str

    classification: Literal[
        "NORMATIVE",
        "INFORMATIVE",
        "EXPLICIT_OUT_OF_V1",
    ]

    requirement_ids: list[str] = Field(default_factory=list)

    reason: str | None = None
    notes: str | None = None

    # Required only for EXPLICIT_OUT_OF_V1.
    exclusion_source: str | None = None
    exclusion_heading: str | None = None


class AuthorityCoverageModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    sections: list[AuthorityCoverageItem]


class DependencyEdge(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    from_: str = Field(alias="from")
    to: str


class DependenciesModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    components: list[str]
    edges: list[DependencyEdge]
    forbidden_edges: list[DependencyEdge] = Field(default_factory=list)


class ResourceBoundItem(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: str
    owner: str
    phase: str

    lifetime: Literal[
        "DAEMON",
        "TASK",
        "COMMAND",
        "REQUEST",
        "TAB",
        "PROCESS",
        "SESSION",
    ]

    structure: str

    max_count: int | None = Field(default=None, gt=0)
    max_bytes: int | None = Field(default=None, gt=0)
    timeout_seconds: float | None = Field(default=None, gt=0)

    overflow_policy: str

    @model_validator(mode="after")
    def validate_bound(self) -> "ResourceBoundItem":
        if (
            self.max_count is None
            and self.max_bytes is None
            and self.timeout_seconds is None
        ):
            raise ValueError(
                f"Resource bound {self.id!r} has no numeric bound"
            )
        if not self.overflow_policy.strip():
            raise ValueError(
                f"Resource bound {self.id!r} has empty overflow_policy"
            )
        return self


class ResourceBoundsModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    bounds: list[ResourceBoundItem]


class AuthorityModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    cookbook_version: str
    status: Literal["DRAFT", "FROZEN", "BLOCKED"]

    cookbook_work_base_sha: str
    product_code_base_sha: str
    base_sha: str

    ci_baseline_run: str
    python_floor: str
    target_os: str

    authority_order: list[str]
    blob_shas: dict[str, str]

    # Legacy hashes preserved for backward validation
    interface_hash: str | None = None
    requirement_map_hash: str | None = None
    phase_manifest_hash: str | None = None

    # FINAL complete freeze map.
    artifact_hashes: dict[str, str] = Field(default_factory=dict)
    artifact_bundle_hash: str | None = None


class CookbookModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    root_path: Path
    authority: AuthorityModel
    requirements: RequirementsModel
    symbols: SymbolsModel
    interfaces: InterfacesModel
    file_owners: FileOwnersModel
    phase_manifest: PhaseManifestModel
    tests: TestsModel
    dependencies: DependenciesModel
    authority_coverage: AuthorityCoverageModel | None = None
    resource_bounds: ResourceBoundsModel | None = None


def load_cookbook(root: Path) -> CookbookModel:
    """Load machine manifest models from cookbook directory."""
    machine_dir = root / "machine" if (root / "machine").is_dir() else root

    with open(machine_dir / "authority.json", "r", encoding="utf-8") as f:
        auth_data = json.load(f)
    authority = AuthorityModel.model_validate(auth_data)

    with open(machine_dir / "requirements.json", "r", encoding="utf-8") as f:
        req_data = json.load(f)
    requirements = RequirementsModel.model_validate(req_data)

    with open(machine_dir / "symbols.json", "r", encoding="utf-8") as f:
        sym_data = json.load(f)
    symbols = SymbolsModel.model_validate(sym_data)

    with open(machine_dir / "interfaces.json", "r", encoding="utf-8") as f:
        iface_data = json.load(f)
    interfaces = InterfacesModel.model_validate(iface_data)

    with open(machine_dir / "file_owners.json", "r", encoding="utf-8") as f:
        files_data = json.load(f)
    file_owners = FileOwnersModel.model_validate(files_data)

    with open(machine_dir / "phase_manifest.json", "r", encoding="utf-8") as f:
        phase_data = json.load(f)
    phase_manifest = PhaseManifestModel.model_validate(phase_data)

    with open(machine_dir / "tests.json", "r", encoding="utf-8") as f:
        test_data = json.load(f)
    tests = TestsModel.model_validate(test_data)

    with open(machine_dir / "dependencies.json", "r", encoding="utf-8") as f:
        dep_data = json.load(f)
    dependencies = DependenciesModel.model_validate(dep_data)

    authority_coverage = None
    cov_path = machine_dir / "authority_coverage.json"
    if cov_path.exists():
        with open(cov_path, "r", encoding="utf-8") as f:
            cov_data = json.load(f)
        authority_coverage = AuthorityCoverageModel.model_validate(cov_data)

    resource_bounds = None
    bounds_path = machine_dir / "resource_bounds.json"
    if bounds_path.exists():
        with open(bounds_path, "r", encoding="utf-8") as f:
            bounds_data = json.load(f)
        resource_bounds = ResourceBoundsModel.model_validate(bounds_data)

    return CookbookModel(
        root_path=root,
        authority=authority,
        requirements=requirements,
        symbols=symbols,
        interfaces=interfaces,
        file_owners=file_owners,
        phase_manifest=phase_manifest,
        tests=tests,
        dependencies=dependencies,
        authority_coverage=authority_coverage,
        resource_bounds=resource_bounds,
    )
