"""Project H Base Executor Protocol and Strict Argument Models."""

from typing import Any, Literal, Protocol, runtime_checkable
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.actions.schema import ActionRequest, ActionResult

MAX_ARGV_COUNT = 256
MAX_ARG_CHARS = 4096
MAX_ENV_COUNT = 64
MAX_ENV_KEY_CHARS = 256
MAX_ENV_VAL_CHARS = 4096
MAX_FILE_BYTES = 10_485_760      # 10 MiB
MAX_DIR_LIST_ENTRIES = 1024


class ProcessArgs(BaseModel):
    """Strict typed arguments for process execution."""

    model_config = ConfigDict(extra="forbid", strict=True)

    argv: list[str] = Field(min_length=1, max_length=MAX_ARGV_COUNT)
    cwd: str = Field(min_length=1)
    env: dict[str, str] = Field(default_factory=dict)

    @field_validator("argv")
    @classmethod
    def validate_argv(cls, v: list[str]) -> list[str]:
        for idx, arg in enumerate(v):
            if not isinstance(arg, str):
                raise ValueError(f"argv[{idx}] must be a string")
            if not arg.strip():
                raise ValueError(f"argv[{idx}] must not be empty or whitespace only")
            if "\x00" in arg:
                raise ValueError(f"argv[{idx}] contains forbidden NUL character")
            if len(arg) > MAX_ARG_CHARS:
                raise ValueError(f"argv[{idx}] exceeds maximum length of {MAX_ARG_CHARS} characters")
        return v

    @field_validator("cwd")
    @classmethod
    def validate_cwd(cls, v: str) -> str:
        if not v.strip() or "\x00" in v:
            raise ValueError("cwd must be a non-empty string without NUL")
        return v

    @field_validator("env")
    @classmethod
    def validate_env(cls, v: dict[str, str]) -> dict[str, str]:
        if len(v) > MAX_ENV_COUNT:
            raise ValueError(f"env exceeds maximum of {MAX_ENV_COUNT} variables")
        for k, val in v.items():
            if not isinstance(k, str) or not k.strip() or "\x00" in k or len(k) > MAX_ENV_KEY_CHARS:
                raise ValueError(f"env key '{k}' must be non-empty string <= {MAX_ENV_KEY_CHARS} chars without NUL")
            if not isinstance(val, str) or "\x00" in val or len(val) > MAX_ENV_VAL_CHARS:
                raise ValueError(f"env value for key '{k}' must be string <= {MAX_ENV_VAL_CHARS} chars without NUL")
        return v


class FileReadArgs(BaseModel):
    """Strict typed arguments for file reading."""

    model_config = ConfigDict(extra="forbid", strict=True)

    path: str = Field(min_length=1)
    max_bytes: int = Field(default=MAX_FILE_BYTES, gt=0, le=MAX_FILE_BYTES)

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        if not v.strip() or "\x00" in v:
            raise ValueError("path must be a non-empty string without NUL")
        return v


class FileListArgs(BaseModel):
    """Strict typed arguments for directory listing."""

    model_config = ConfigDict(extra="forbid", strict=True)

    path: str = Field(min_length=1)
    max_entries: int = Field(default=MAX_DIR_LIST_ENTRIES, gt=0, le=MAX_DIR_LIST_ENTRIES)

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        if not v.strip() or "\x00" in v:
            raise ValueError("path must be a non-empty string without NUL")
        return v


class FileWriteArgs(BaseModel):
    """Strict typed arguments for atomic file writing."""

    model_config = ConfigDict(extra="forbid", strict=True)

    path: str = Field(min_length=1)
    content: str | bytes
    encoding: Literal["utf-8", "binary"] = "utf-8"

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        if not v.strip() or "\x00" in v:
            raise ValueError("path must be a non-empty string without NUL")
        return v

    @model_validator(mode="after")
    def validate_content_size(self) -> "FileWriteArgs":
        size = len(self.content.encode("utf-8")) if isinstance(self.content, str) else len(self.content)
        if size > MAX_FILE_BYTES:
            raise ValueError(f"content size ({size} bytes) exceeds maximum limit ({MAX_FILE_BYTES} bytes)")
        return self


class FileDeleteArgs(BaseModel):
    """Strict typed arguments for file deletion."""

    model_config = ConfigDict(extra="forbid", strict=True)

    path: str = Field(min_length=1)

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        if not v.strip() or "\x00" in v:
            raise ValueError("path must be a non-empty string without NUL")
        return v


class XdgOpenArgs(BaseModel):
    """Strict typed arguments for app opening via xdg-open."""

    model_config = ConfigDict(extra="forbid", strict=True)

    target: str = Field(min_length=1)

    @field_validator("target")
    @classmethod
    def validate_target(cls, v: str) -> str:
        if not v.strip() or "\x00" in v:
            raise ValueError("target must be a non-empty string without NUL")
        lowered = v.lower()
        if lowered.startswith("http://") or lowered.startswith("https://"):
            raise ValueError("xdg-open cannot open HTTP/HTTPS URLs; browser URLs must pass browser policy via BrowserBridge")
        return v


@runtime_checkable
class BaseExecutor(Protocol):
    """Base protocol implemented by all Project H executors."""

    async def execute(self, action: ActionRequest, context: Any = None) -> ActionResult:
        """Execute validated action request within security constraints."""
        ...
