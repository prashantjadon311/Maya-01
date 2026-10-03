# Maya Test Fixture & Fake Subsystem Architecture

To guarantee deterministic, fast test execution without burning paid cloud API quotas or requiring desktop GUI servers in CI, all tests rely on structured test doubles and fakes.

---

## 1. Reusable Test Fakes

### 1.1 `FakeAIProvider` (`tests/fakes/fake_nvidia.py`)
Mocks the `NvidiaProvider` interface.
- Stores pre-configured responses or tool calls.
- Simulates streaming SSE chunks with configurable delays.
- Tracks `call_count` and received `messages` for inspection.
- Can simulate `ProviderTimeoutError` or `ProviderAPIError`.

```python
class FakeAIProvider:
    def __init__(self, response_text: str = "Mock response", tool_calls = None):
        self.response_text = response_text
        self.tool_calls = tool_calls or []
        self.calls: list[list[ChatMessage]] = []

    async def complete(self, messages: list[ChatMessage], tools = None) -> ChatResponse:
        self.calls.append(messages)
        return ChatResponse(content=self.response_text, tool_calls=self.tool_calls, finish_reason="stop")

    async def stream_chat(self, messages: list[ChatMessage], tools = None):
        self.calls.append(messages)
        yield ChatChunk(delta_content=self.response_text)
```

### 1.2 `FakePopupBackend` (`tests/fakes/fake_popup.py`)
Mocks the desktop approval dialog.
- Captures `ActionRequest`, `reason`, and `risk` sent to the popup.
- Configurable auto-decision: `"ALLOW_ONCE"`, `"DENY"`, or `"TIMEOUT"`.
- Never attempts to spawn GTK/Zenity windows in automated test runs.

### 1.3 `FakeAudioSource` & `FakeWakeDetector` (`tests/fakes/fake_voice.py`)
- `FakeAudioSource`: Feeds pre-recorded 16kHz mono PCM frames from memory.
- `FakeWakeDetector`: Returns `0.95` confidence when target sample is processed; `0.05` otherwise.

### 1.4 `FakeBrowserBridge` (`tests/fakes/fake_browser.py`)
- Emulates the Firefox Native Messaging host pipe without launching Firefox.
- Responds with synthetic DOM extraction payloads or simulated tab errors.

### 1.5 `FakeAuditSink` (`tests/fakes/fake_audit.py`)
- In-memory list collecting audit dictionaries.
- Exposes `assert_event_logged(code: str, target: str)` and `assert_secret_not_logged(secret: str)`.
