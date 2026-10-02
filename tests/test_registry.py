"""Deterministic registry behavior and trust boundary tests."""

import json
import socket
import subprocess
import urllib.request

import pytest

from app.actions.schema import ActionRequest


def definition(action_id="app.open", **overrides):
    return dict(id=action_id, phrases=["open vscode", "vs code kholo"],
                executor="process", arguments={"argv": ["code"]},
                approval="preapproved", risk="low") | overrides


def write_pack(directory, name="core", actions=None, **overrides):
    path = directory / f"{name}.json"
    data = dict(pack_id=name, label=name, schema_version=1,
                actions=[definition()] if actions is None else actions) | overrides
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def registry(directory):
    from app.actions.registry import ActionRegistry
    result = ActionRegistry(directory)
    assert result.reload()
    return result


def test_valid_multiple_packs_and_definition_isolation(tmp_path):
    write_pack(tmp_path)
    write_pack(tmp_path, "other", [definition("app.other", phrases=["other"])])
    reg = registry(tmp_path)
    assert reg.resolve("other").action_id == "app.other"
    trusted = reg.get_definition("app.open")
    trusted.arguments["argv"].append("--changed")
    trusted.enabled = False
    assert reg.get_definition("app.open").arguments == {"argv": ["code"]}
    assert reg.resolve("open vscode").action_id == "app.open"
    assert reg.get_definition("missing") is None


@pytest.mark.parametrize("text", ["open vscode", "vs code kholo", "Open VSCode", "OPEN VSCODE", "  open \t vscode \n", "ＯＰＥＮ　ＶＳＣＯＤＥ"])
def test_normalized_exact_phrases(tmp_path, text):
    write_pack(tmp_path)
    match = registry(tmp_path).resolve(text)
    assert match.action_id == "app.open" and dict(match.captured_slots) == {}


def test_disabled_and_no_match(tmp_path):
    write_pack(tmp_path, actions=[definition(enabled=False)])
    reg = registry(tmp_path)
    assert reg.get_definition("app.open").enabled is False
    assert reg.resolve("open vscode") is None
    assert reg.resolve("unrelated") is None


@pytest.mark.parametrize("phrase,text", [("google search {query}", "Google search Python Docs"), ("google par {query} search karo", "google par Python Docs search karo")])
def test_slots_and_safe_substitution(tmp_path, phrase, text):
    from app.actions.matcher import substitute_arguments
    write_pack(tmp_path, actions=[definition(phrases=[phrase], arguments={"query": "{query}", "nested": ["prefix:{query}", 1, True]})])
    reg = registry(tmp_path)
    match = reg.resolve(text)
    assert dict(match.captured_slots) == {"query": "Python Docs"}
    assert substitute_arguments(reg.get_definition(match.action_id).arguments, match.captured_slots) == {"query": "Python Docs", "nested": ["prefix:Python Docs", 1, True]}
    assert reg.resolve(text.replace("Python Docs", "")) is None


def test_regex_characters_literal_and_matching_anchored(tmp_path):
    write_pack(tmp_path, actions=[definition(phrases=["open (a+b).*?"])])
    reg = registry(tmp_path)
    assert reg.resolve("open (a+b).*?").action_id == "app.open"
    assert reg.resolve("open abxyz") is None
    assert reg.resolve("prefix open (a+b).*?") is None


@pytest.mark.parametrize("phrase", ["open {bad-name}", "open {obj.__class__}", "open {", "open }", "open {}", "open {x!r}", "open {x}{y}", "open {x} {x}", "  "])
def test_invalid_templates_rejected(tmp_path, phrase):
    from app.actions.registry import ActionRegistry
    write_pack(tmp_path, actions=[definition(phrases=[phrase])])
    reg = ActionRegistry(tmp_path)
    assert not reg.reload()
    assert reg.get_definition("app.open") is None
    assert reg.diagnostics


def test_undeclared_argument_slot_rejects_candidate(tmp_path):
    from app.actions.registry import ActionRegistry
    write_pack(tmp_path, actions=[definition(arguments={"argv": ["code", "{missing}"]})])
    reg = ActionRegistry(tmp_path)
    assert not reg.reload()
    assert reg.diagnostics


def test_every_phrase_declares_required_argument_slots(tmp_path):
    from app.actions.registry import ActionRegistry
    write_pack(tmp_path, actions=[definition(phrases=["open {path}", "open"], arguments={"path": "{path}"})])
    assert not ActionRegistry(tmp_path).reload()


def test_runtime_ambiguity_never_picks_an_action(tmp_path):
    from app.actions.registry import RegistryAmbiguity
    write_pack(tmp_path, actions=[definition("app.one", phrases=["search {query}"]), definition("app.two", phrases=["{verb} python"])])
    result = registry(tmp_path).resolve("search python")
    assert isinstance(result, RegistryAmbiguity)
    assert set(result.action_ids) == {"app.one", "app.two"}


def test_duplicate_normalized_phrases_reported_and_ambiguous(tmp_path):
    from app.actions.registry import RegistryAmbiguity
    write_pack(tmp_path, actions=[definition("app.one", phrases=["Open  Code"]), definition("app.two", phrases=["open code"])])
    reg = registry(tmp_path)
    assert reg.diagnostics
    assert isinstance(reg.resolve("open code"), RegistryAmbiguity)


def test_duplicate_ids_across_files_preserve_snapshot(tmp_path):
    write_pack(tmp_path)
    reg = registry(tmp_path)
    before = reg.snapshot_version
    write_pack(tmp_path, "duplicate")
    assert not reg.reload()
    assert reg.snapshot_version == before
    assert reg.resolve("open vscode").action_id == "app.open"


@pytest.mark.parametrize("damage", ["json", "unknown", "duplicate", "oversized"])
def test_invalid_file_retains_last_good_pack(tmp_path, damage):
    from app.actions.registry import MAX_PACK_BYTES
    path = write_pack(tmp_path)
    reg = registry(tmp_path)
    if damage == "json":
        path.write_text("{", encoding="utf-8")
    elif damage == "unknown":
        write_pack(tmp_path, unexpected=True)
    elif damage == "duplicate":
        write_pack(tmp_path, actions=[definition(), definition()])
    else:
        path.write_bytes(b" " * (MAX_PACK_BYTES + 1))
    reg.reload()
    assert reg.diagnostics
    assert reg.resolve("open vscode").action_id == "app.open"


def test_initial_bad_file_skipped_other_valid_pack_activated(tmp_path):
    (tmp_path / "bad.json").write_text("{", encoding="utf-8")
    write_pack(tmp_path)
    reg = registry(tmp_path)
    assert reg.diagnostics
    assert reg.resolve("open vscode").action_id == "app.open"


def test_reload_validates_all_relationships_before_publish(tmp_path):
    path = write_pack(tmp_path)
    reg = registry(tmp_path)
    version = reg.snapshot_version
    write_pack(tmp_path, actions=[definition(phrases=["changed"])])
    write_pack(tmp_path, "bad", [definition("app.bad", executor="composite", arguments={"steps": ["app.missing"]})])
    assert not reg.reload()
    assert reg.snapshot_version == version
    assert reg.resolve("open vscode").action_id == "app.open"
    assert reg.resolve("changed") is None


@pytest.mark.parametrize("steps", [[], ["app.missing"], [123], [{"executor": "process"}], "app.open"])
def test_invalid_composite_steps(tmp_path, steps):
    from app.actions.registry import ActionRegistry
    write_pack(tmp_path, actions=[definition("app.group", executor="composite", arguments={"steps": steps})])
    assert not ActionRegistry(tmp_path).reload()


@pytest.mark.parametrize("indirect", [False, True])
def test_composite_cycles_rejected(tmp_path, indirect):
    from app.actions.registry import ActionRegistry
    actions = [definition("app.one", executor="composite", arguments={"steps": ["app.two" if indirect else "app.one"]})]
    if indirect:
        actions.append(definition("app.two", executor="composite", arguments={"steps": ["app.one"]}))
    write_pack(tmp_path, actions=actions)
    assert not ActionRegistry(tmp_path).reload()


def test_valid_composite(tmp_path):
    write_pack(tmp_path, actions=[definition(), definition("app.group", phrases=["group"], executor="composite", arguments={"steps": ["app.open"]})])
    assert registry(tmp_path).resolve("group").action_id == "app.group"


def test_registry_has_no_side_effects_or_policy_calls(tmp_path, monkeypatch):
    from app.policy.engine import PolicyEngine
    def forbidden(*args, **kwargs):
        pytest.fail("registry crossed execution/network/policy boundary")
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(PolicyEngine, "evaluate", forbidden)
    write_pack(tmp_path)
    result = registry(tmp_path).resolve("open vscode")
    assert result.action_id == "app.open"
    assert not isinstance(result, ActionRequest)
    forged = ActionRequest(id=result.action_id, tool="process.run", arguments={"argv": ["rm", "-rf", "/"]})
    assert not hasattr(forged, "captured_slots")


def test_model_id_does_not_grant_preapproval(tmp_path):
    from app.policy.engine import PolicyEngine, PolicyDecision
    write_pack(tmp_path)
    match = registry(tmp_path).resolve("open vscode")
    proposed = ActionRequest(id=match.action_id, tool="process.run", arguments={"argv": ["code"]})
    assert PolicyEngine().evaluate(proposed) == PolicyDecision.ASK_USER


def test_action_definition_missing_approval_rejected():
    from pydantic import ValidationError
    from app.actions.schema import ActionDefinition
    with pytest.raises(ValidationError):
        ActionDefinition(id="app.test", executor="process", risk="low")


def test_action_definition_missing_risk_rejected():
    from pydantic import ValidationError
    from app.actions.schema import ActionDefinition
    with pytest.raises(ValidationError):
        ActionDefinition(id="app.test", executor="process", approval="preapproved")


def test_action_definition_high_preapproved_rejected():
    from pydantic import ValidationError
    from app.actions.schema import ActionDefinition
    with pytest.raises(ValidationError):
        ActionDefinition(id="app.test", executor="process", approval="preapproved", risk="high")


def test_action_definition_critical_preapproved_rejected():
    from pydantic import ValidationError
    from app.actions.schema import ActionDefinition
    with pytest.raises(ValidationError):
        ActionDefinition(id="app.test", executor="process", approval="preapproved", risk="critical")


def test_captured_slot_preserves_original_case(tmp_path):
    write_pack(tmp_path, actions=[definition("file.open", phrases=["open file {filename}"], arguments={"path": "/data/{filename}"})])
    reg = registry(tmp_path)
    match = reg.resolve("open file MyDocument_V2.PDF")
    assert match.action_id == "file.open"
    assert match.captured_slots["filename"] == "MyDocument_V2.PDF"


def test_symlinked_pack_rejected(tmp_path):
    real_file = tmp_path / "target.json"
    real_file.write_text(json.dumps(dict(pack_id="core", label="Core", schema_version=1, actions=[definition()])), encoding="utf-8")
    link_file = tmp_path / "symlinked.json"
    link_file.symlink_to(real_file)
    reg = registry(tmp_path)
    assert any("Symlink rejected" in d for d in reg.diagnostics)


def test_non_utf8_pack_rejected(tmp_path):
    write_pack(tmp_path)
    bad_path = tmp_path / "non_utf8.json"
    bad_path.write_bytes(b"\xff\xfe\x00\x00")
    reg = registry(tmp_path)
    assert any("Non-UTF-8" in d for d in reg.diagnostics)
    assert reg.resolve("open vscode").action_id == "app.open"


def test_max_pack_files_enforced(tmp_path):
    from app.actions.registry import MAX_PACK_FILES, ActionRegistry
    for i in range(MAX_PACK_FILES + 1):
        write_pack(tmp_path, name=f"pack_{i:03d}", actions=[definition(f"app.act_{i:03d}", phrases=[f"act {i}"])])
    reg = ActionRegistry(tmp_path)
    assert not reg.reload()
    assert any("MAX_PACK_FILES" in d for d in reg.diagnostics)


def test_max_total_actions_enforced(tmp_path):
    from app.actions.registry import MAX_TOTAL_ACTIONS, ActionRegistry
    actions = [definition(f"app.a_{i:04d}", phrases=[f"phrase {i}"]) for i in range(MAX_TOTAL_ACTIONS + 1)]
    write_pack(tmp_path, actions=actions)
    reg = ActionRegistry(tmp_path)
    assert not reg.reload()
    assert any("MAX_TOTAL_ACTIONS" in d for d in reg.diagnostics)


def test_phrase_count_limit_enforced(tmp_path):
    from app.actions.registry import MAX_PHRASES_PER_ACTION, ActionRegistry
    phrases = [f"phrase {i}" for i in range(MAX_PHRASES_PER_ACTION + 1)]
    write_pack(tmp_path, actions=[definition("app.heavy", phrases=phrases)])
    reg = ActionRegistry(tmp_path)
    assert not reg.reload()
    assert any("MAX_PHRASES_PER_ACTION" in d for d in reg.diagnostics)


def test_phrase_length_limit_enforced(tmp_path):
    from app.actions.registry import MAX_PHRASE_CHARS, ActionRegistry
    long_phrase = "x" * (MAX_PHRASE_CHARS + 1)
    write_pack(tmp_path, actions=[definition("app.long", phrases=[long_phrase])])
    reg = ActionRegistry(tmp_path)
    assert not reg.reload()
    assert any("512" in d or "exceed" in d for d in reg.diagnostics)


def test_command_length_limit_enforced(tmp_path):
    from app.actions.registry import MAX_COMMAND_CHARS
    write_pack(tmp_path)
    reg = registry(tmp_path)
    oversized_command = "open vscode " + ("x" * MAX_COMMAND_CHARS)
    assert reg.resolve(oversized_command) is None


def test_deleting_valid_pack_removes_actions(tmp_path):
    write_pack(tmp_path, "core", [definition("app.core", phrases=["open core"])])
    extra_path = write_pack(tmp_path, "extra", [definition("app.extra", phrases=["open extra"])])
    reg = registry(tmp_path)
    assert reg.resolve("open core").action_id == "app.core"
    assert reg.resolve("open extra").action_id == "app.extra"

    extra_path.unlink()
    assert reg.reload()
    assert reg.resolve("open core").action_id == "app.core"
    assert reg.resolve("open extra") is None
    assert reg.get_definition("app.extra") is None


def test_empty_directory_publishes_empty_registry(tmp_path):
    pack_path = write_pack(tmp_path, "core", [definition("app.core", phrases=["open core"])])
    reg = registry(tmp_path)
    assert reg.resolve("open core").action_id == "app.core"

    pack_path.unlink()
    assert reg.reload()
    assert reg.resolve("open core") is None
    assert reg.get_definition("app.core") is None
    assert reg.snapshot_version == 2


def test_get_definition_deep_copy_cannot_mutate_active_nested_arguments(tmp_path):
    write_pack(tmp_path, actions=[definition("app.open", arguments={"argv": ["code"], "options": {"env": {"DEBUG": "1"}, "flags": ["-v"]}})])
    reg = registry(tmp_path)
    defn1 = reg.get_definition("app.open")
    defn1.arguments["argv"].append("--hacked")
    defn1.arguments["options"]["env"]["DEBUG"] = "0"
    defn1.arguments["options"]["flags"].append("--mutated")

    defn2 = reg.get_definition("app.open")
    assert defn2.arguments == {"argv": ["code"], "options": {"env": {"DEBUG": "1"}, "flags": ["-v"]}}


def test_model_forged_action_request_gives_no_registry_trust(tmp_path):
    from app.policy.engine import PolicyEngine, PolicyDecision
    write_pack(tmp_path, actions=[definition("app.open", phrases=["open vscode"], executor="process", arguments={"argv": ["code"]}, approval="preapproved", risk="low")])
    reg = registry(tmp_path)
    match = reg.resolve("open vscode")
    assert match.action_id == "app.open"

    forged = ActionRequest(id=match.action_id, tool="process.run", arguments={"argv": ["rm", "-rf", "/"]})
    decision = PolicyEngine().evaluate(forged)
    assert decision != PolicyDecision.ALLOW_PREAPPROVED
