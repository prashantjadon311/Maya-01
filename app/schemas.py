from enum import Enum
from typing import Annotated, Literal, Union
from pydantic import BaseModel, ConfigDict, Field


class ErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    PROVIDER_NOT_CONFIGURED = "PROVIDER_NOT_CONFIGURED"
    AUTH = "AUTH"
    RATE_LIMIT = "RATE_LIMIT"
    TIMEOUT = "TIMEOUT"
    UNAVAILABLE = "UNAVAILABLE"
    NETWORK = "NETWORK"
    CONTEXT_LIMIT = "CONTEXT_LIMIT"
    INVALID_REQUEST = "INVALID_REQUEST"
    CANCELLED = "CANCELLED"
    INTERNAL = "INTERNAL"


class FinishReason(str, Enum):
    STOP = "stop"
    LENGTH = "length"
    CONTENT_FILTER = "content_filter"
    ERROR = "error"
    CANCELLED = "cancelled"


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class AutoSelection(BaseModel):
    mode: Literal["auto"] = "auto"
    profile: str = "balanced"


class ManualSelection(BaseModel):
    mode: Literal["manual"] = "manual"
    model: str = Field(min_length=1)


Selection = Annotated[
    Union[AutoSelection, ManualSelection],
    Field(discriminator="mode")
]


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: str | None = None
    messages: list[ChatMessage] = Field(min_length=1)
    selection: Selection


class AppInfo(BaseModel):
    name: str = "Project H"
    version: str = "0.1.0"


class BootstrapDefaults(BaseModel):
    routing_profile: str = "balanced"


class RoutingProfileInfo(BaseModel):
    id: str
    label: str


class ProviderInfo(BaseModel):
    id: str
    label: str
    configured: bool
    health: str
    adapter: str


class ModelInfo(BaseModel):
    id: str
    label: str
    provider_id: str
    enabled: bool
    capabilities: list[str]
    routing_profiles: list[str]
    health: str


class BootstrapResponse(BaseModel):
    api_version: str = "v1"
    app: AppInfo = Field(default_factory=AppInfo)
    defaults: BootstrapDefaults = Field(default_factory=BootstrapDefaults)
    routing_profiles: list[RoutingProfileInfo] = Field(default_factory=list)
    providers: list[ProviderInfo] = Field(default_factory=list)
    models: list[ModelInfo] = Field(default_factory=list)


class StreamEvent(BaseModel):
    type: str
    request_id: str
    seq: int = Field(ge=0)


class StartEvent(StreamEvent):
    type: Literal["start"] = "start"
    selection_mode: Literal["auto", "manual"]
    routing_profile: str | None = None
    provider: str
    model: str
    attempt: int = Field(ge=1)


class DeltaEvent(StreamEvent):
    type: Literal["delta"] = "delta"
    text: str = Field(min_length=1)


class FallbackEvent(StreamEvent):
    type: Literal["fallback"] = "fallback"
    from_provider: str
    from_model: str
    to_provider: str
    to_model: str
    reason: str
    attempt: int = Field(ge=1)


class UsageEvent(StreamEvent):
    type: Literal["usage"] = "usage"
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class DoneEvent(StreamEvent):
    type: Literal["done"] = "done"
    provider: str
    model: str
    finish_reason: str
    first_token_latency_ms: float | None = None
    total_latency_ms: float | None = None


class ErrorEvent(StreamEvent):
    type: Literal["error"] = "error"
    code: ErrorCode
    message: str
    retryable: bool
    provider: str | None = None
    model: str | None = None
    partial_output: bool = False
