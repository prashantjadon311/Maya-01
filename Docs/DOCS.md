# Project H — Product, API and Dashboard Specification

**Version:** 1.0  
**Status:** implementation authority  
**Primary implementation agent:** Gemini / Antigravity  
**First runtime provider:** NVIDIA Nemotron 3 Ultra

## 1. Product Vision

Project H is a **very small local AI console** that lets a user chat with one or more hosted LLM providers through one consistent interface.

MVP mental model:

```text
Prompt
→ choose model or Auto
→ Project H backend
→ provider adapter
→ hosted LLM API
→ normalized streamed answer
```

The product is intentionally not an agent platform yet. Its job is to establish a clean, reliable provider/routing/streaming foundation that future RETHINK capabilities can build on without rewriting the core.

## 2. MVP Success Criteria

Project H succeeds when a user can:

- start it locally with one Python command;
- open one lightweight browser dashboard;
- send a prompt;
- select Nemotron manually or use Auto;
- see the answer stream incrementally;
- stop generation;
- retry/regenerate;
- see provider/model/latency/token metadata when available;
- see clear provider/error/fallback state;
- keep basic browser-local conversation history;
- configure providers via server-side environment variables without exposing keys to the browser.

## 3. MVP Technology

```text
Backend        Python + FastAPI + Uvicorn
Validation     Pydantic v2
Provider SDK   OpenAI Python async client against compatible endpoints
Config         config.toml + environment variables
Frontend       plain HTML + CSS + vanilla JavaScript
Streaming      POST + NDJSON over fetch() ReadableStream
Cancel         AbortController
History        localStorage
Server DB      none
Processes      one
```

## 4. First Live Provider — NVIDIA Nemotron 3 Ultra

Current official NVIDIA hosted configuration:

```text
Provider ID:       nvidia
Base URL:          https://integrate.api.nvidia.com/v1
Model:             nvidia/nemotron-3-ultra-550b-a55b
API style:         OpenAI-compatible Chat Completions
Secret env var:    NVIDIA_API_KEY
Streaming:         supported
Model context:     up to 1M tokens on the published model/hosted offering
```

NVIDIA documents Nemotron 3 Ultra as a 550B-total / roughly 55B-active hybrid Mamba/MoE reasoning model with configurable reasoning behavior.

### MVP NVIDIA behavior

Project H uses Nemotron as **one provider behind the generic adapter boundary**. Do not make the rest of the application NVIDIA-specific.

Recommended client behavior:

```text
Async client
custom base_url
max_retries = 0
Project H-owned timeout/retry policy
stream = true
```

Provider-only options should be adapter/config-owned. Current NVIDIA documentation includes reasoning controls and a coding-agent compatibility recommendation around `force_nonempty_content`.

Nemotron streams reasoning separately in some configurations. The MVP must ignore reasoning trace for user-visible output.

Do not:

- send `reasoning_content` to browser;
- store it in `localStorage`;
- log it by default;
- append it to later conversation turns.

Visible TTFT starts at the first non-empty assistant content delta.

## 5. Public HTTP API

MVP public endpoints:

```text
GET  /healthz
GET  /api/v1/bootstrap
POST /api/v1/chat/stream
```

There is no WebSocket API, server-side conversation CRUD, separate cancel endpoint, or non-streaming chat endpoint in MVP.

### `GET /healthz`

Must not contact external providers.

```json
{"status":"ok"}
```

### `GET /api/v1/bootstrap`

Returns everything the browser needs to initialize:

```json
{
  "api_version": "v1",
  "app": {"name":"Project H","version":"0.1.0"},
  "defaults": {"routing_profile":"balanced"},
  "routing_profiles": [{"id":"balanced","label":"Balanced"}],
  "providers": [],
  "models": []
}
```

The initial live setup may contain only NVIDIA. Future providers are config additions or adapter additions, not frontend rewrites.

### Public provider health

Allowed values:

```text
unknown
healthy
degraded
cooldown
unavailable
```

`configured=true` means required server-side secret/config exists. It does not guarantee the credential has already been validated live.

### Public model shape

```json
{
  "id":"nvidia:nemotron-ultra",
  "label":"Nemotron 3 Ultra",
  "provider_id":"nvidia",
  "enabled":true,
  "capabilities":["text","streaming"],
  "routing_profiles":["balanced"],
  "health":"unknown"
}
```

The browser uses the stable Project H model ID. Upstream provider model IDs remain backend configuration details.

## 6. Chat Request Contract

Endpoint:

```text
POST /api/v1/chat/stream
Content-Type: application/json
```

Auto example:

```json
{
  "conversation_id":"browser-generated-id",
  "messages":[
    {"role":"user","content":"Explain async generators."}
  ],
  "selection":{
    "mode":"auto",
    "profile":"balanced"
  }
}
```

Manual example:

```json
{
  "messages":[{"role":"user","content":"Hello"}],
  "selection":{
    "mode":"manual",
    "model":"nvidia:nemotron-ultra"
  }
}
```

MVP browser transcript roles:

```text
user
assistant
```

Application/system instructions remain backend-owned.

## 7. NDJSON Streaming Contract

Response content type:

```text
application/x-ndjson
```

MVP event types:

```text
start
delta
fallback
usage
done
error
```

Every event contains:

```json
{
  "type":"...",
  "request_id":"uuid",
  "seq":0
}
```

Sequence numbers start at 0 and increase monotonically.

### Start

```json
{
  "type":"start",
  "request_id":"...",
  "seq":0,
  "selection_mode":"auto",
  "routing_profile":"balanced",
  "provider":"nvidia",
  "model":"nvidia:nemotron-ultra",
  "attempt":1
}
```

### Delta

```json
{
  "type":"delta",
  "request_id":"...",
  "seq":1,
  "text":"Visible output fragment"
}
```

`text` is never empty.

### Fallback

Fallback event is legal only before the first visible `delta`.

```json
{
  "type":"fallback",
  "request_id":"...",
  "seq":1,
  "from_provider":"nvidia",
  "from_model":"nvidia:nemotron-ultra",
  "to_provider":"future-provider",
  "to_model":"future:model",
  "reason":"UNAVAILABLE",
  "attempt":2
}
```

For the first MVP with only NVIDIA live, this behavior is proven using fake providers even when no real second provider is configured.

### Usage

At most one event:

```json
{
  "type":"usage",
  "request_id":"...",
  "seq":42,
  "input_tokens":1024,
  "output_tokens":382,
  "total_tokens":1406
}
```

Unavailable values are `null`, never guessed and presented as provider fact.

### Done

```json
{
  "type":"done",
  "request_id":"...",
  "seq":43,
  "provider":"nvidia",
  "model":"nvidia:nemotron-ultra",
  "finish_reason":"stop",
  "first_token_latency_ms":812,
  "total_latency_ms":3218
}
```

### Error

```json
{
  "type":"error",
  "request_id":"...",
  "seq":3,
  "code":"RATE_LIMIT",
  "message":"The selected AI service is temporarily rate limited.",
  "retryable":true,
  "provider":"nvidia",
  "model":"nvidia:nemotron-ultra",
  "partial_output":false
}
```

Terminal invariant:

```text
A stream ends in exactly one of: done | error.
No event follows either terminal event.
```

A client disconnect may prevent the final error event from physically reaching the browser.

## 8. Canonical Error Codes

```text
VALIDATION_ERROR
MODEL_NOT_FOUND
PROVIDER_NOT_CONFIGURED
AUTH
RATE_LIMIT
TIMEOUT
UNAVAILABLE
NETWORK
CONTEXT_LIMIT
INVALID_REQUEST
CANCELLED
INTERNAL
```

Frontend logic reacts to these stable codes, not raw NVIDIA/provider strings.

## 9. Retry and Fallback Rules

Default policy:

```text
retries_per_model      = 1
max_upstream_attempts  = 4
cooldown_after_failures= 2
cooldown_seconds       = 60
```

Eligible same-model retry:

```text
NETWORK
UNAVAILABLE
```

Rate limit may retry only when provider `Retry-After` fits the configured wait budget and overall request deadline.

Do not automatically retry:

```text
AUTH
INVALID_REQUEST
VALIDATION_ERROR
PROVIDER_NOT_CONFIGURED
```

Timeout does not retry the same candidate. Context limit does not retry the same model.

Most important invariant:

```text
pre-first-visible-delta failure  → fallback may occur
post-first-visible-delta failure → fallback forbidden; terminate partial answer with error
```

## 10. Configuration Contract

Use:

```text
config.toml
+
environment variables for secrets
+
strict Pydantic validation
```

All config models use `extra="forbid"` except a deliberately opaque provider-specific request-extra dictionary.

Recommended initial config shape:

```toml
[app]
name = "Project H"
host = "127.0.0.1"
port = 8000
log_level = "INFO"

[runtime]
request_timeout_seconds = 120
connect_timeout_seconds = 10
retries_per_model = 1
retry_backoff_ms = 250
retry_after_max_seconds = 2
max_upstream_attempts = 4
cooldown_after_failures = 2
cooldown_seconds = 60
max_messages_per_request = 100
max_message_characters = 100000
max_request_characters = 250000

[defaults]
routing_profile = "balanced"

[[providers]]
id = "nvidia"
label = "NVIDIA"
adapter = "openai_protocol"
api_style = "chat_completions"
base_url = "https://integrate.api.nvidia.com/v1"
api_key_env = "NVIDIA_API_KEY"
enabled = true

[providers.request_extra.chat_template_kwargs]
enable_thinking = true
force_nonempty_content = true
reasoning_budget = 8192

[[models]]
id = "nvidia:nemotron-ultra"
label = "Nemotron 3 Ultra"
provider = "nvidia"
upstream_model = "nvidia/nemotron-3-ultra-550b-a55b"
enabled = true
capabilities = ["text", "streaming"]
context_window_tokens = 1000000
max_output_tokens = 16384

[routing.balanced]
label = "Balanced"
models = ["nvidia:nemotron-ultra"]
```

If current NVIDIA hosted API behavior changes, verify the provider-specific options against official docs rather than weakening the generic contract.

Startup must fail on broken structural references (duplicate IDs, unknown provider/model references, invalid profile), but must **not** fail merely because `NVIDIA_API_KEY` is absent. The provider becomes `configured=false` instead.

## 11. Dashboard Product Requirements

The dashboard is intentionally plain and fast.

### Required primary screen

Desktop contains:

```text
Left sidebar
  Project H identity
  New chat
  recent conversations
  provider status summary

Top bar
  Auto/manual selector
  model selector
  connection state
  Settings

Main conversation area
  user messages
  assistant messages
  quiet routing/fallback events
  response metadata
  Copy / Retry

Composer
  multiline input
  Send
  Stop while streaming
  shortcut hint
```

### Required settings surface

Settings contains:

- default routing profile;
- request timeout;
- history enabled;
- persistent-history toggle;
- provider configured/status state;
- environment-variable name only, never the secret value;
- security notice that secrets remain server-side.

### Required operational states

Design and implementation must represent:

- empty/new conversation;
- request starting;
- streaming;
- completion;
- fallback before first token;
- rate limit/unavailable;
- partial-stream error;
- stopped generation;
- provider unconfigured.

No blocking whole-screen loading state.

## 12. Figma Dashboard Authority

Figma file:

`https://www.figma.com/design/32qadE21g6ZK8g5afK1bt0`

Created top-level frames:

```text
Desktop / Streaming Chat  node 2:2     1440 × 900
Desktop / Settings        node 2:80     720 × 760
Mobile / Chat             node 2:144    390 × 844
Operational States        node 2:174   1200 × 250
```

The Figma Starter MCP call quota was reached immediately after creation, so screenshot validation could not be completed in the originating session. Gemini should treat the numeric contract below plus the actual Figma nodes as authority and visually inspect the file during frontend implementation if Figma access is available.

## 13. UI Design Tokens

MVP uses one quiet dark theme. No theme switch is required initially.

```text
Background       #0F1115
Surface          #151922
Surface 2        #1B202A
Surface 3        #202631
Border           #2A313D
Text             #E8ECF3
Muted            #929BAA
Faint            #687181
Accent           #84A3FF
Accent soft      #BDD0FF
Success          #63C99C
Warning          #E9B96E
Error            #EF7A7A
Font             Inter / system sans fallback
Radius           8–12px controls; 16px major desktop frames
```

Desktop target:

```text
Viewport design  1440 × 900
Sidebar          240px
Topbar            68px
Chat content max ~760px
Composer target  ~860px wide
```

Mobile target:

```text
390 × 844 reference
no persistent sidebar
history becomes drawer
compact Auto/model selector
composer remains always reachable
```

### Visual rules

Do not add:

- avatars;
- character art;
- glassmorphism;
- gradients for decoration;
- giant marketing typography;
- 3D effects;
- animated backgrounds;
- charts;
- permanent reasoning panel;
- icon libraries just to display four simple controls.

Tiny CSS transitions and a small streaming pulse are acceptable.

## 14. Frontend Behavior

Streaming transport:

```text
fetch(POST /api/v1/chat/stream)
→ response.body.getReader()
→ incremental UTF-8 decode
→ newline buffer
→ JSON.parse each complete NDJSON line
→ dispatch by event.type
```

Stop:

```text
AbortController.abort()
```

Regenerate removes the last assistant response and resends the portable transcript from the preceding user turn.

Retry resends the same portable transcript. In Auto mode routing starts fresh against current runtime health.

### Rendering security

MVP output is plain text:

```text
textContent
white-space: pre-wrap
```

Do not inject raw model output via `innerHTML`.

## 15. Browser History

Use `localStorage` for:

```text
conversation_id
title
created_at
updated_at
messages
assistant response metadata
preferences
```

Provide:

- New chat;
- select conversation;
- delete/clear history;
- persistence toggle.

Document that localStorage is plaintext on the device.

## 16. Logging

Default structured fields:

```text
request_id
conversation_id (if present)
selection_mode
routing_profile
provider
model
attempt_number
status
error_code
first_token_latency_ms
total_latency_ms
input_tokens
output_tokens
```

Never log by default:

```text
API keys
Authorization header
prompt/body text
generated answer text
reasoning trace
raw provider request/response payload
```

## 17. Explicit MVP Non-Goals

```text
agents
autonomous planning
tool execution
MCP execution
RAG/vector DB
embeddings
files/images/audio/voice
server conversation storage
multi-user auth
billing
cost dashboards
parallel model comparison
semantic LLM router
React/Next frontend
cloud deployment architecture
```

The architecture may leave seams for these; it must not implement them now.

## 18. References Used To Freeze This Spec

NVIDIA:

- https://build.nvidia.com/nvidia/nemotron-3-ultra-550b-a55b
- https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-ultra-550b-a55b
- https://docs.api.nvidia.com/nim/re/reference/nvidia-nemotron-3-ultra-550b-a55b-infer
- https://docs.nvidia.com/nim/large-language-models/2.0.7/day-0/get-started-nemotron-3-ultra.html
- https://research.nvidia.com/labs/nemotron/Nemotron-3-Ultra/

FastAPI:

- https://fastapi.tiangolo.com/advanced/custom-response/
- https://fastapi.tiangolo.com/tutorial/stream-json-lines/
- https://fastapi.tiangolo.com/tutorial/static-files/
- https://fastapi.tiangolo.com/advanced/async-tests/

OpenAI Python client compatibility layer:

- https://github.com/openai/openai-python

The OpenAI Python SDK is used here as an OpenAI-compatible transport client for NVIDIA; Project H's public API remains provider-neutral.
