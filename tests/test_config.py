from pathlib import Path
import pytest
from pydantic import ValidationError

from app.core.config import Config, load_config, parse_config_toml


def test_load_valid_fixture():
    fixture_path = Path(__file__).parent / "fixtures" / "config.example.toml"
    cfg = load_config(fixture_path)
    assert isinstance(cfg, Config)
    assert cfg.assistant.display_name == "Maya"
    assert cfg.assistant.wake_phrase == "Maya"
    assert cfg.voice.enabled is True
    assert cfg.voice.wake_engine == "openwakeword"
    assert cfg.stt.provider == "nvidia"
    assert cfg.stt.api_key_env == "NVIDIA_API_KEY"
    assert cfg.ai.provider == "nvidia"
    assert cfg.ai.model == "nvidia/nemotron-3-ultra-550b-a55b"
    assert cfg.resources.memory_high_mb == 240
    assert cfg.resources.memory_max_mb == 300
    assert len(cfg.browser.domains) == 2
    assert len(cfg.files.roots) == 1


def test_config_unknown_field_fails():
    toml_str = """
    unknown_top_level = "unexpected"

    [assistant]
    display_name = "Maya"
    wake_phrase = "Maya"
    """
    with pytest.raises(ValidationError):
        parse_config_toml(toml_str)


def test_config_nested_unknown_field_fails():
    toml_str = """
    [assistant]
    display_name = "Maya"
    wake_phrase = "Maya"
    unexpected_option = 123
    """
    with pytest.raises(ValidationError):
        parse_config_toml(toml_str)


def test_invalid_memory_limits_order():
    toml_str = """
    [resources]
    memory_high_mb = 280
    memory_max_mb = 240
    """
    with pytest.raises(ValidationError) as exc_info:
        parse_config_toml(toml_str)
    assert "memory_high_mb must not exceed memory_max_mb" in str(exc_info.value)


def test_invalid_memory_limits_exceed_300():
    toml_str = """
    [resources]
    memory_high_mb = 240
    memory_max_mb = 400
    """
    with pytest.raises(ValidationError) as exc_info:
        parse_config_toml(toml_str)
    assert "memory_max_mb must not exceed 300" in str(exc_info.value)


def test_invalid_memory_limits_non_positive():
    toml_str = """
    [resources]
    memory_high_mb = -10
    memory_max_mb = 300
    """
    with pytest.raises(ValidationError):
        parse_config_toml(toml_str)


def test_missing_required_section_or_field():
    toml_str = """
    [assistant]
    # missing display_name and wake_phrase
    language = "auto"
    """
    with pytest.raises(ValidationError):
        parse_config_toml(toml_str)


def test_env_key_reference_only_no_real_key_required(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    fixture_path = Path(__file__).parent / "fixtures" / "config.example.toml"
    cfg = load_config(fixture_path)
    assert cfg.ai.api_key_env == "NVIDIA_API_KEY"
    assert cfg.stt.api_key_env == "NVIDIA_API_KEY"
