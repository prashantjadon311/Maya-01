"""Deterministic registry behavior and trust boundary tests."""

import json
import socket
import subprocess
import urllib.request

import pytest

from app.actions.schema import ActionRequest


def definition(action_id="app.open", **overrides):
    return dict(id=action_id, phrases=["open vscode", "vs code kholo"],
                executor="process", arguments={"argv": ["code"]}) | overrides


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
    assert dict(match.captured_slots) == {"query": "python docs"}
    assert substitute_arguments(reg.get_definition(match.action_id).arguments, match.captured_slots) == {"query": "python docs", "nested": ["prefix:python docs", 1, True]}
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
