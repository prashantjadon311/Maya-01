from pathlib import Path
import pytest
from pydantic import ValidationError

from app.core.config import Config, load_config, parse_config_toml


@pytest.mark.parametrize("host", ["0.0.0.0", "localhost", "::1"])
def test_dashboard_is_ipv4_loopback_only(host):
    from app.core.config import DashboardConfig
    assert DashboardConfig(host="127.0.0.1").host == "127.0.0.1"
    with pytest.raises(ValidationError):
        DashboardConfig(host=host)


@pytest.mark.parametrize("capability", ["download", "upload", "clipboard"])
def test_canonical_browser_capabilities_accepted(capability):
    from app.core.config import BrowserDomainConfig
    assert BrowserDomainConfig(pattern="https://example.com/*", capabilities=[capability]).capabilities == [capability]


@pytest.mark.parametrize("capability", ["evaluate", "javascript", "cookies", "local_storage", "downloads", "camera", "microphone"])
def test_noncanonical_browser_capabilities_rejected(capability):
    from app.core.config import BrowserDomainConfig
    with pytest.raises(ValidationError):
        BrowserDomainConfig(pattern="https://example.com/*", capabilities=[capability])


@pytest.mark.parametrize("field", ["display_name", "wake_phrase"])
def test_assistant_identity_is_nonempty_and_trimmed(field):
    from app.core.config import AssistantConfig
    data = {"display_name": "Maya", "wake_phrase": "Maya"}
    with pytest.raises(ValidationError):
        AssistantConfig(**(data | {field: " \t "}))
    assert getattr(AssistantConfig(**(data | {field: " Maya "})), field) == "Maya"


@pytest.mark.parametrize("field,value", [("wake_threshold", -0.1), ("wake_threshold", 1.1), ("wake_threshold", float("nan")), ("max_command_seconds", 0), ("max_command_seconds", -1)])
def test_voice_bounds(field, value):
    from app.core.config import VoiceConfig
    with pytest.raises(ValidationError):
        VoiceConfig(**{field: value})


@pytest.mark.parametrize("field", ["max_active", "max_steps", "max_api_calls_per_task", "default_timeout_minutes"])
@pytest.mark.parametrize("value", [0, -1])
def test_positive_agent_budgets(field, value):
    from app.core.config import AgentsConfig
    with pytest.raises(ValidationError):
        AgentsConfig(**{field: value})


def test_resource_bounds_follow_product_contract():
    from app.core.config import ResourcesConfig
    cfg = ResourcesConfig(memory_high_mb=1, memory_max_mb=2, max_audio_command_seconds=301)
    assert cfg.memory_high_mb == 1
    for field in ["memory_high_mb", "memory_max_mb", "max_event_queue", "max_audio_command_seconds"]:
        with pytest.raises(ValidationError):
            ResourcesConfig(**{field: 0})


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
def test_ISSUE_K_config_model_constraints():
    from app.core.config import DashboardConfig, ResourcesConfig, BrowserDomainConfig
    from pydantic import ValidationError
    import pytest

    # Dashboard port bounds
    with pytest.raises(ValidationError):
        DashboardConfig(port=-1)
    with pytest.raises(ValidationError):
        DashboardConfig(port=99999)

    # Resources bounds
    with pytest.raises(ValidationError):
        ResourcesConfig(memory_high_mb=0, memory_max_mb=20)
    with pytest.raises(ValidationError):
        ResourcesConfig(max_event_queue=-5)
    with pytest.raises(ValidationError):
        ResourcesConfig(max_audio_command_seconds=0)

    # Browser capabilities
    with pytest.raises(ValidationError):
        BrowserDomainConfig(pattern="*", capabilities=["HACK_SYS"])
