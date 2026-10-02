import pytest
from pydantic import ValidationError

def test_chat_message_valid():
    from app.schemas import ChatMessage
    msg = ChatMessage(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"

def test_chat_message_empty_content_rejected():
    from app.schemas import ChatMessage
    with pytest.raises(ValidationError):
        ChatMessage(role="user", content="")

def test_chat_message_invalid_role_rejected():
    from app.schemas import ChatMessage
    with pytest.raises(ValidationError):
        ChatMessage(role="system", content="System prompt")

def test_selection_auto_shape():
    from app.schemas import AutoSelection, Selection
    sel = AutoSelection(profile="balanced")
    assert sel.mode == "auto"
    assert sel.profile == "balanced"

def test_selection_manual_shape():
    from app.schemas import ManualSelection
    sel = ManualSelection(model="nvidia:nemotron-ultra")
    assert sel.mode == "manual"
    assert sel.model == "nvidia:nemotron-ultra"

def test_chat_request_forbidden_unknown_fields():
    from app.schemas import ChatRequest, ChatMessage, AutoSelection
    data = {
        "messages": [{"role": "user", "content": "Hi"}],
        "selection": {"mode": "auto", "profile": "balanced"},
        "unknown_extra": "foo"
    }
    with pytest.raises(ValidationError):
        ChatRequest.model_validate(data)

def test_chat_request_empty_messages_rejected():
    from app.schemas import ChatRequest
    data = {
        "messages": [],
        "selection": {"mode": "auto", "profile": "balanced"}
    }
    with pytest.raises(ValidationError):
        ChatRequest.model_validate(data)

def test_error_codes():
    from app.schemas import ErrorCode
    assert ErrorCode.VALIDATION_ERROR == "VALIDATION_ERROR"
    assert ErrorCode.RATE_LIMIT == "RATE_LIMIT"
    assert ErrorCode.AUTH == "AUTH"

def test_stream_event_models():
    from app.schemas import StartEvent, DeltaEvent, FallbackEvent, UsageEvent, DoneEvent, ErrorEvent
    
    start = StartEvent(
        request_id="req-123",
        seq=0,
        selection_mode="auto",
        routing_profile="balanced",
        provider="nvidia",
        model="nvidia:nemotron-ultra",
        attempt=1
    )
    assert start.type == "start"
    assert start.seq == 0

    delta = DeltaEvent(request_id="req-123", seq=1, text="Hello world")
    assert delta.type == "delta"

    with pytest.raises(ValidationError):
        DeltaEvent(request_id="req-123", seq=1, text="")

    done = DoneEvent(
        request_id="req-123",
        seq=2,
        provider="nvidia",
        model="nvidia:nemotron-ultra",
        finish_reason="stop",
        first_token_latency_ms=120.5,
        total_latency_ms=500.0
    )
    assert done.type == "done"
