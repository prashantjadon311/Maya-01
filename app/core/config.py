"""Project H Configuration Loader and Validation Models."""

from pathlib import Path
import tomllib
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AssistantConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str
    wake_phrase: str
    language: str = "auto"
    start_on_login: bool = True

    @field_validator("display_name", "wake_phrase")
    @classmethod
    def validate_identity(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Assistant identity must not be empty")
        return value


class VoiceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    always_listen: bool = False
    push_to_talk_hotkey: str = "Ctrl+Space"
    wake_engine: str = "openwakeword"
    wake_model: str = "~/.config/project-h/wake/assistant_name.tflite"
    wake_threshold: float = Field(default=0.55, ge=0.0, le=1.0)
    vad_enabled: bool = True
    max_command_seconds: int = Field(default=30, gt=0)
    retain_command_audio: bool = False


class STTConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = "nvidia"
    model: str = "nvidia/parakeet-1_1b-rnnt-multilingual-asr"
    api_key_env: str = "NVIDIA_API_KEY"
    default_language: str = "hi-IN"


class AIConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = "nvidia"
    base_url: str = "https://integrate.api.nvidia.com/v1"
    model: str = "nvidia/nemotron-3-ultra-550b-a55b"
    api_key_env: str = "NVIDIA_API_KEY"
    timeout_seconds: int = 120
    reasoning_effort: str = "medium"
    reasoning_budget: int = 4096
    max_output_tokens: int = 8192


class DashboardConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host: Literal["127.0.0.1"] = "127.0.0.1"
    port: int = Field(default=8765, ge=1, le=65535)
    open_browser: bool = True


class AgentsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_active: int = Field(default=1, gt=0)
    max_steps: int = Field(default=30, gt=0)
    max_api_calls_per_task: int = Field(default=20, gt=0)
    default_timeout_minutes: int = Field(default=30, gt=0)


class ResourcesConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory_high_mb: int = Field(default=240, gt=0)
    memory_max_mb: int = Field(default=300, gt=0)
    max_event_queue: int = Field(default=256, ge=1)
    max_audio_command_seconds: int = Field(default=30, gt=0)

    @model_validator(mode="after")
    def validate_memory_limits(self) -> "ResourcesConfig":
        if self.memory_max_mb > 300:
            raise ValueError("memory_max_mb must not exceed 300")
        if self.memory_high_mb > self.memory_max_mb:
            raise ValueError("memory_high_mb must not exceed memory_max_mb")
        return self


class PrivacyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    store_chat_history: bool = True
    store_action_audit: bool = True
    log_prompt_content: bool = False
    log_response_content: bool = False
    retain_audio: bool = False


class BrowserDomainConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pattern: str = Field(min_length=1)
    enabled: bool = True
    capabilities: list[Literal["open", "read", "click", "type", "submit", "download", "upload", "clipboard"]] = Field(default_factory=list)
    adapter: str | None = None


class BrowserConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domains: list[BrowserDomainConfig] = Field(default_factory=list)


class FileRootConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    read: bool = False
    write: bool = False
    delete: bool = False


class FilesConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    roots: list[FileRootConfig] = Field(default_factory=list)


class Config(BaseModel):
    """Canonical Project H Configuration Root."""

    model_config = ConfigDict(extra="forbid")

    assistant: AssistantConfig
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    stt: STTConfig = Field(default_factory=STTConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    dashboard: DashboardConfig = Field(default_factory=DashboardConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    resources: ResourcesConfig = Field(default_factory=ResourcesConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    files: FilesConfig = Field(default_factory=FilesConfig)


def parse_config_toml(toml_str: str) -> Config:
    """Parse and validate configuration from TOML string."""
    data = tomllib.loads(toml_str)
    return Config.model_validate(data)


def load_config(path: str | Path) -> Config:
    """Load and validate configuration from TOML file path."""
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return Config.model_validate(data)
