"""Project H Deterministic Action Registry and Snapshot Management."""

import copy
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import stat
from typing import Any

from app.actions.matcher import (
    extract_argument_slots,
    normalize_text,
    parse_phrase_template,
)
from app.actions.schema import ActionDefinition, ActionPack

# Bounded security limits to guarantee <= 300 MiB resident ceiling
MAX_PACK_BYTES = 1_048_576      # 1 MiB per pack file
MAX_PACK_FILES = 64             # Maximum number of pack files in actions.d
MAX_TOTAL_ACTIONS = 2048        # Maximum total actions across all packs
MAX_PHRASES_PER_ACTION = 32     # Maximum phrases per action definition
MAX_PHRASE_CHARS = 512          # Maximum characters per phrase template
MAX_COMMAND_CHARS = 4096        # Maximum characters in a command string


@dataclass(frozen=True)
class RegistryMatch:
    """Dedicated result of a deterministic action match.

    TRUST BOUNDARY:
    This is NOT an ActionRequest and NOT an approval token.
    ActionRequest.id == registered action id DOES NOT establish trusted registry provenance.
    An external caller or AI model can forge an ID.
    Deterministic execution consumes RegistryMatch through trusted internal dispatch (PH-040).
    """

    action_id: str
    captured_slots: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RegistryAmbiguity:
    """Returned when a command matches multiple enabled registered actions.

    Deterministic command resolution never guesses or picks by arbitrary ordering.
    """

    action_ids: list[str] = field(default_factory=list)


@dataclass
class _RegistrySnapshot:
    """Immutable snapshot of the active registry state."""

    packs: dict[str, ActionPack]
    actions: dict[str, ActionDefinition]
    matchers: list[tuple[re.Pattern[str], str, list[str]]]


def _check_composite_cycles(actions: dict[str, ActionDefinition]) -> None:
    """
    Check composite action dependencies for cycles (A -> A, A -> B -> A, etc.).

    DEFERRED INVARIANT FOR PH-040:
    Composite actions reference child registered action IDs in sequence.
    PH-040 executor/dispatcher must policy-check EACH child action separately.
    Composite parent permissions must never downgrade or bypass child security.
    """
    visited: dict[str, int] = {}  # 0: unvisited, 1: visiting (in stack), 2: finished

    def dfs(node: str, path: list[str]) -> None:
        visited[node] = 1
        action = actions.get(node)
        if action and action.executor == "composite":
            steps = action.arguments.get("steps", [])
            for step in steps:
                if step not in actions:
                    raise ValueError(f"Composite action '{node}' references nonexistent action '{step}'")
                state = visited.get(step, 0)
                if state == 1:
                    cycle_str = " -> ".join(path + [step])
                    raise ValueError(f"Composite cycle detected: {cycle_str}")
                if state == 0:
                    dfs(step, path + [step])
        visited[node] = 2

    for action_id, action in actions.items():
        if action.executor == "composite" and action_id not in visited:
            dfs(action_id, [action_id])


class ActionRegistry:
    """
    Deterministic Action Registry managing action packs loaded from an actions directory.

    Guarantees:
    - Transactional reload: Builds a candidate snapshot and publishes only after complete validation.
    - Last-known-good: If an existing valid pack file becomes malformed, its previous valid pack is retained.
    - Deleted packs: If a pack file is removed from disk, its actions are removed upon reload.
    - Ambiguity: If two actions match, returns RegistryAmbiguity without guessing.
    - Safe loading: Strict UTF-8, no symlinks, bounded sizes, no eval/exec/network.
    """

    def __init__(self, actions_dir: str | Path) -> None:
        self.actions_dir = Path(actions_dir)
        self.diagnostics: list[str] = []
        self._snapshot_version: int = 0
        self._active_snapshot: _RegistrySnapshot | None = None
        self._last_known_good: dict[str, ActionPack] = {}

    @property
    def snapshot_version(self) -> int:
        return self._snapshot_version

    def get_definition(self, action_id: str) -> ActionDefinition | None:
        """Return a defensive deep copy of the trusted ActionDefinition for action_id."""
        if self._active_snapshot is None:
            return None
        action = self._active_snapshot.actions.get(action_id)
        if action is None:
            return None
        return copy.deepcopy(action)

    def resolve(self, command: str) -> RegistryMatch | RegistryAmbiguity | None:
        """
        Resolve a user command string to a registered action match or ambiguity.
        Ignores disabled actions. Case-insensitive matching, case-preserving slot extraction.
        """
        if self._active_snapshot is None:
            return None

        if not isinstance(command, str) or len(command) > MAX_COMMAND_CHARS:
            return None

        normalized = normalize_text(command)
        if not normalized:
            return None

        matching_actions: dict[str, dict[str, str]] = {}
        for pattern, action_id, declared_slots in self._active_snapshot.matchers:
            m = pattern.match(normalized)
            if m is not None:
                slot_vals: dict[str, str] = {}
                valid_match = True
                for s in declared_slots:
                    val = m.group(s)
                    if not val or not val.strip():
                        valid_match = False
                        break
                    slot_vals[s] = val.strip()
                if valid_match:
                    matching_actions[action_id] = slot_vals

        if not matching_actions:
            return None

        if len(matching_actions) > 1:
            return RegistryAmbiguity(action_ids=sorted(matching_actions.keys()))

        action_id, captured_slots = next(iter(matching_actions.items()))
        return RegistryMatch(action_id=action_id, captured_slots=captured_slots)

    def reload(self) -> bool:
        """
        Scan actions_dir and build a candidate snapshot.
        If validation succeeds, publish candidate snapshot and return True.
        If validation fails, retain active snapshot, record diagnostics, and return False.
        """
        diagnostics: list[str] = []

        if not self.actions_dir.exists() or not self.actions_dir.is_dir():
            # If actions directory does not exist or is not a dir, publish empty registry
            self._active_snapshot = _RegistrySnapshot(packs={}, actions={}, matchers=[])
            self._last_known_good.clear()
            self._snapshot_version += 1
            self.diagnostics = diagnostics
            return True

        real_dir = self.actions_dir.resolve()

        # Only load *.json files inside configured actions directory
        try:
            entries = sorted(
                [p for p in self.actions_dir.iterdir() if p.name.endswith(".json") and not p.name.startswith(".")],
                key=lambda x: x.name,
            )
        except OSError as exc:
            diagnostics.append(f"Failed to read actions directory: {exc}")
            self.diagnostics = diagnostics
            return False

        if len(entries) > MAX_PACK_FILES:
            diagnostics.append(f"Pack file count ({len(entries)}) exceeds MAX_PACK_FILES ({MAX_PACK_FILES})")
            self.diagnostics = diagnostics
            return False

        # Drop last-known-good entries for pack files that were intentionally deleted from disk
        existing_names = {p.name for p in entries}
        for filename in list(self._last_known_good.keys()):
            if filename not in existing_names:
                del self._last_known_good[filename]

        if not entries:
            # Actions directory is empty: publish valid empty registry
            self._active_snapshot = _RegistrySnapshot(packs={}, actions={}, matchers=[])
            self._last_known_good.clear()
            self._snapshot_version += 1
            self.diagnostics = diagnostics
            return True

        candidate_packs: dict[str, ActionPack] = {}
        had_file_loading_errors = False

        for file_path in entries:
            filename = file_path.name
            pack, error_msg = self._load_pack_file(file_path, real_dir)
            if error_msg:
                had_file_loading_errors = True
                diagnostics.append(error_msg)
                # Check for existing last-known-good pack
                if filename in self._last_known_good:
                    candidate_packs[filename] = self._last_known_good[filename]
                    diagnostics.append(f"Retained last-known-good pack for '{filename}'")
                else:
                    diagnostics.append(f"Skipped brand-new malformed pack '{filename}'")
            elif pack is not None:
                candidate_packs[filename] = pack

        # If files were present on disk, but none could be loaded and none had LKG:
        if not candidate_packs and entries:
            diagnostics.append("No valid action packs available to publish")
            self.diagnostics = diagnostics
            return False

        # -------------------------------------------------------------
        # Candidate Validation: Limits, Relationships, Composites, Slots
        # -------------------------------------------------------------
        total_actions = sum(len(p.actions) for p in candidate_packs.values())
        if total_actions > MAX_TOTAL_ACTIONS:
            diagnostics.append(
                f"Total actions ({total_actions}) exceeds MAX_TOTAL_ACTIONS ({MAX_TOTAL_ACTIONS})"
            )
            self.diagnostics = diagnostics
            return False

        all_actions: dict[str, ActionDefinition] = {}
        action_source_file: dict[str, str] = {}

        for filename, pack in candidate_packs.items():
            for action in pack.actions:
                if action.id in all_actions:
                    diagnostics.append(
                        f"Duplicate action ID '{action.id}' across packs '{action_source_file[action.id]}' and '{filename}'"
                    )
                    self.diagnostics = diagnostics
                    return False
                all_actions[action.id] = action
                action_source_file[action.id] = filename

        # Validate per-action limits, phrases, and argument slots
        seen_normalized_phrases: dict[str, str] = {}  # normalized_phrase -> action_id

        for action_id, action in all_actions.items():
            if len(action.phrases) > MAX_PHRASES_PER_ACTION:
                diagnostics.append(
                    f"Action '{action_id}' has {len(action.phrases)} phrases, exceeding MAX_PHRASES_PER_ACTION ({MAX_PHRASES_PER_ACTION})"
                )
                self.diagnostics = diagnostics
                return False

            arg_slots = extract_argument_slots(action.arguments)
            if arg_slots and not action.phrases:
                diagnostics.append(
                    f"Action '{action_id}' references argument slots {arg_slots} but declares no phrases"
                )
                self.diagnostics = diagnostics
                return False

            for phrase in action.phrases:
                try:
                    _pattern, declared_slots = parse_phrase_template(phrase)
                except ValueError as exc:
                    diagnostics.append(f"Action '{action_id}' invalid phrase template '{phrase}': {exc}")
                    self.diagnostics = diagnostics
                    return False

                declared_set = set(declared_slots)
                if not arg_slots.issubset(declared_set):
                    missing = arg_slots - declared_set
                    diagnostics.append(
                        f"Action '{action_id}' phrase '{phrase}' missing required argument slots {missing}"
                    )
                    self.diagnostics = diagnostics
                    return False

                norm_p = normalize_text(phrase).lower()
                if norm_p in seen_normalized_phrases:
                    other_id = seen_normalized_phrases[norm_p]
                    if other_id != action_id:
                        diagnostics.append(
                            f"Duplicate normalized phrase '{norm_p}' in actions '{other_id}' and '{action_id}'"
                        )
                else:
                    seen_normalized_phrases[norm_p] = action_id

            # Composite validation
            if action.executor == "composite":
                if "steps" not in action.arguments:
                    diagnostics.append(f"Composite action '{action_id}' missing 'steps' in arguments")
                    self.diagnostics = diagnostics
                    return False
                steps = action.arguments.get("steps")
                if not isinstance(steps, list) or len(steps) == 0:
                    diagnostics.append(f"Composite action '{action_id}' 'steps' must be a non-empty list")
                    self.diagnostics = diagnostics
                    return False
                for step in steps:
                    if not isinstance(step, str) or not step:
                        diagnostics.append(f"Composite action '{action_id}' step {step!r} must be a non-empty string")
                        self.diagnostics = diagnostics
                        return False
                    if step not in all_actions:
                        diagnostics.append(
                            f"Composite action '{action_id}' references nonexistent action '{step}'"
                        )
                        self.diagnostics = diagnostics
                        return False

        # Validate composite cycle freedom
        try:
            _check_composite_cycles(all_actions)
        except ValueError as exc:
            diagnostics.append(str(exc))
            self.diagnostics = diagnostics
            return False

        # Build compiled matchers for enabled actions
        matchers: list[tuple[re.Pattern[str], str, list[str]]] = []
        for action_id, action in all_actions.items():
            if not action.enabled:
                continue
            for phrase in action.phrases:
                pattern, declared_slots = parse_phrase_template(phrase)
                matchers.append((pattern, action_id, declared_slots))

        # Successfully validate and publish candidate snapshot
        self._active_snapshot = _RegistrySnapshot(
            packs=candidate_packs,
            actions=all_actions,
            matchers=matchers,
        )
        self._last_known_good = dict(candidate_packs)
        self._snapshot_version += 1
        self.diagnostics = diagnostics
        return True

    def _load_pack_file(self, file_path: Path, real_dir: Path) -> tuple[ActionPack | None, str | None]:
        """Safely load and validate an action pack JSON file without following symlinks."""
        if file_path.is_symlink() or os.path.islink(file_path):
            return None, f"Symlink rejected: '{file_path.name}'"

        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
        fd = -1
        try:
            fd = os.open(str(file_path), flags)
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode):
                return None, f"Not a regular file: '{file_path.name}'"
            if st.st_size > MAX_PACK_BYTES:
                return None, f"File '{file_path.name}' size ({st.st_size} bytes) exceeds MAX_PACK_BYTES ({MAX_PACK_BYTES})"

            content_bytes = os.read(fd, st.st_size + 1)
            if len(content_bytes) > MAX_PACK_BYTES:
                return None, f"File '{file_path.name}' content exceeds MAX_PACK_BYTES ({MAX_PACK_BYTES})"

            try:
                content_str = content_bytes.decode("utf-8")
            except UnicodeDecodeError as exc:
                return None, f"Non-UTF-8 encoding in '{file_path.name}': {exc}"

            resolved = file_path.resolve()
            if not resolved.is_relative_to(real_dir):
                return None, f"File '{file_path.name}' resolves outside actions directory"

            try:
                data = json.loads(content_str)
            except Exception as exc:
                return None, f"JSON parse error in '{file_path.name}': {exc}"

            try:
                pack = ActionPack.model_validate(data)
            except Exception as exc:
                return None, f"ActionPack validation failed for '{file_path.name}': {exc}"

            return pack, None

        except OSError as exc:
            return None, f"Failed to open '{file_path.name}': {exc}"
        finally:
            if fd >= 0:
                os.close(fd)
