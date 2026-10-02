# PH-030 Deterministic Action Registry Result

## 1. Interfaces
- **`ActionDefinition` (`app.actions.schema`)**:
  - `approval` and `risk` fields are REQUIRED; no defaults (fail-closed contract).
  - Model validator rejects actions with `risk in {"high", "critical"}` and `approval == "preapproved"`.
- **`ActionRegistry` (`app.actions.registry`)**:
  - `__init__(actions_dir: str | Path)`
  - `reload() -> bool`: Transactional candidate validation and atomic snapshot publish.
  - `resolve(command: str) -> RegistryMatch | RegistryAmbiguity | None`: Case-insensitive resolution.
  - `get_definition(action_id: str) -> ActionDefinition | None`: Defensive `copy.deepcopy`.
  - Properties: `snapshot_version: int`, `diagnostics: list[str]`.
- **`RegistryMatch` (`app.actions.registry`)**:
  - Frozen dataclass `(action_id: str, captured_slots: dict[str, str])`.
  - Dedicated trust boundary result; NOT an `ActionRequest` and NOT an approval token.
- **`RegistryAmbiguity` (`app.actions.registry`)**:
  - Frozen dataclass `(action_ids: list[str])`.
- **`app.actions.matcher`**:
  - `parse_phrase_template(phrase: str) -> tuple[re.Pattern, list[str]]`
  - `normalize_text(text: str) -> str`: NFKC normalization, whitespace collapsing, case-preserving.
  - `extract_argument_slots(arguments: Any) -> set[str]`
  - `substitute_arguments(arguments: Any, captured_slots: dict[str, str]) -> Any`

## 2. Semantics
- **Bounded Resource Limits:**
  - `MAX_PACK_BYTES = 1_048_576` (1 MiB)
  - `MAX_PACK_FILES = 64`
  - `MAX_TOTAL_ACTIONS = 2048`
  - `MAX_PHRASES_PER_ACTION = 32`
  - `MAX_PHRASE_CHARS = 512`
  - `MAX_COMMAND_CHARS = 4096`
- **Safe File Loading:** Strict UTF-8 decoding, `O_NOFOLLOW` file descriptor open, symlink rejection, path traversal containment checks, size check prior to parsing.
- **Transactional Reload & Snapshots:**
  - Candidate snapshot created separately from active snapshot; published atomically only upon complete validation.
  - Corrupted existing files retain their previous last-known-good (LKG) pack.
  - Brand-new malformed files are skipped with recorded diagnostics.
  - Intentionally deleted pack files are dropped; deleted packs are never resurrected from LKG.
  - Empty actions directory publishes a valid empty registry.
- **Global Invariants:**
  - Rejection of duplicate action IDs across pack files (no last-file-wins).
  - Validation of argument `{slot}` placeholders: every phrase in the action must declare all slots required by its arguments.
  - Composite action validation: `steps` must be a non-empty list of strings referencing existing actions.
  - Composite cycle detection: direct (A -> A) and indirect (A -> B -> A) cycles rejected.
  - Ambiguity: If multiple enabled actions match, returns `RegistryAmbiguity` without arbitrary ordering.
- **Trust Boundary:**
  - Registry definitions isolated from caller mutation via `copy.deepcopy`.
  - Model cannot forge preapproval by crafting an `ActionRequest` with a registered ID.

## 3. Tests & Totals
- **Targeted tests (`tests/test_registry.py`):** 57 passed (41 original RED tests made GREEN + 16 new security/boundary tests).
- **Schema tests (`tests/test_schemas.py`):** 39 passed.
- **Full suite:** 327 passed (baseline 270 + 57 registry tests).
- **Installed package import:** Verified via isolated `python -I` without repository working directory.
- **Git diff hygiene:** `git diff --check` clean.

## 4. Remote CI Run
- **GitHub Actions Run ID:** `37066139719`
- **Status:** GREEN (Success)
- **Environments:** Python 3.11 and Python 3.14 both passed full test suite and isolated import verification.

## 5. RSS Delta
- Baseline empty daemon: initial = 13.742 MiB, active = 16.457 MiB.
- Daemon with registry and matcher loaded: 28.227 MiB.
- Resident memory remains well below the 300 MiB cgroup budget ceiling.

## 6. Deferred PH-040 Security Requirements
- **Action Dispatcher:** PH-040 must consume `RegistryMatch` exclusively through trusted deterministic execution pathways. `ActionRequest.id` matching a registered action ID must never bypass policy engine evaluation.
- **Composite Execution:** PH-040 executor must policy-check EACH child action in `steps` separately; parent composite approval must never downgrade child security permissions.
- **Executor Controls:** Process and file executors must enforce timeouts, environment allowlists, network restrictions, and verify real current working directories immediately before execution.
