# Project H — Architecture

**Architecture status:** frozen for MVP  
**Implementation target:** single-process local application

## 1. System Boundary

```text
┌───────────────────────────────────────────────────────────┐
│ Browser                                                    │
│                                                           │
│  index.html + app.css + app.js                            │
│  - chat UI                                                 │
│  - model/Auto selection                                    │
│  - NDJSON parser                                            │
│  - AbortController                                         │
│  - localStorage history                                    │
└───────────────────────────┬───────────────────────────────┘
                            │ same-origin HTTP
                            ▼
┌───────────────────────────────────────────────────────────┐
│ FastAPI                                                    │
│                                                           │
│  GET  /healthz                                             │
│  GET  /api/v1/bootstrap                                    │
│  POST /api/v1/chat/stream                                  │
└───────────────────────────┬───────────────────────────────┘
                            ▼
┌───────────────────────────────────────────────────────────┐
│ Orchestrator                                               │
│                                                           │
│  validate lifecycle                                        │
│  select candidate                                          │
│  own retry/attempt budget                                  │
│  own fallback invariant                                    │
│  normalize public stream                                   │
│  update health + metrics                                   │
└───────────────┬──────────────────────┬────────────────────┘
                │                      │
                ▼                      ▼
┌────────────────────────┐   ┌──────────────────────────────┐
│ Router                 │   │ Runtime Health State         │
│                        │   │                              │
│ manual resolution      │   │ in-memory only               │
│ auto candidate order   │   │ failures/cooldown            │
│ capability filtering   │   │ last success/error           │
│ context-fit filtering  │   │ latency EMA                  │
└───────────────┬────────┘   └──────────────────────────────┘
                ▼
┌───────────────────────────────────────────────────────────┐
│ Provider Registry                                         │
│                                                           │
│ provider-id → one reusable async adapter/client           │
└───────────────────────────┬───────────────────────────────┘
                            ▼
┌───────────────────────────────────────────────────────────┐
│ ProviderAdapter                                            │
│                                                           │
│ canonical request → provider request                       │
│ provider stream → canonical provider events                │
│ provider errors → ProviderError                            │
└───────────────────────────┬───────────────────────────────┘
                            ▼
┌───────────────────────────────────────────────────────────┐
│ OpenAIProtocolAdapter                                      │
│                                                           │
│ MVP live config: NVIDIA hosted Chat Completions           │
└───────────────────────────┬───────────────────────────────┘
                            ▼
            https://integrate.api.nvidia.com/v1
            nvidia/nemotron-3-ultra-550b-a55b
```

## 2. Dependency Direction

Allowed:

```text
api.py
  ↓
orchestrator.py
  ↓
routing.py + providers/base.py
  ↓
providers/openai_protocol.py
```

`config.py` and `schemas.py` are shared foundational modules but must remain free of FastAPI request objects and provider SDK objects.

Forbidden dependency directions:

```text
provider implementation → router policy
provider implementation → frontend
router → FastAPI Request
domain schemas → OpenAI SDK types
frontend → provider SDK
```

## 3. Canonical File Tree

```text
project-h/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api.py
│   ├── schemas.py
│   ├── config.py
│   ├── orchestrator.py
│   ├── routing.py
│   ├── health.py
│   │
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── openai_protocol.py
│   │
│   └── web/
│       ├── index.html
│       ├── app.css
│       └── app.js
│
├── tests/
│   ├── conftest.py
│   ├── fakes.py
│   ├── test_schemas.py
│   ├── test_config.py
│   ├── test_provider_contract.py
│   ├── test_nvidia_adapter.py
│   ├── test_routing.py
│   ├── test_orchestrator.py
│   ├── test_api.py
│   └── test_live_nvidia.py
│
├── config.toml
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
├── SKILL.md
├── EXECUTION.md
├── DOCS.md
├── ARCHITECTURE.md
├── PLAN.md
└── TASKS.md
```

`health.py` is permitted as a tiny module because runtime health/cooldown is independently testable state. Do not grow a generic “services” layer.

## 4. Module Responsibilities

### `main.py`

Owns only:

- FastAPI app construction;
- lifespan startup/shutdown;
- loading validated config;
- creating provider registry/adapters once;
- application state wiring;
- static web mounting/root route.

No routing policy or provider request translation here.

### `api.py`

Owns:

- `/healthz`;
- `/api/v1/bootstrap`;
- `/api/v1/chat/stream`;
- request validation boundary;
- conversion of orchestrator events to one-JSON-object-per-line bytes.

### `schemas.py`

Owns public/canonical datatypes:

- chat message;
- selection discriminated union;
- chat request;
- bootstrap DTOs;
- stream event DTOs;
- normalized error/finish enums.

Provider SDK classes must not appear in public schemas.

### `config.py`

Owns:

- `tomllib` loading;
- Pydantic config models;
- env secret lookup;
- strict unknown-field rejection;
- cross-reference validation;
- provider configured/unconfigured resolution.

### `health.py`

Owns in-memory records such as:

```text
consecutive_transient_failures
last_success_at
last_failure_at
last_error_code
cooldown_until
latency_ema_ms
```

No background monitor.

### `routing.py`

Pure policy where possible:

```text
manual:
  resolve exact enabled model

auto:
  ordered profile candidates
  → enabled/configured
  → required capability
  → not cooling down
  → context fit when metadata exists
  → first remaining candidate
```

No network calls.

### `orchestrator.py`

Owns one complete generation lifecycle:

1. create request ID;
2. resolve candidate;
3. emit public `start`;
4. call adapter;
5. normalize provider deltas into public `delta`;
6. track first visible token time;
7. apply retry/fallback budget;
8. emit `fallback` only before visible output;
9. emit optional usage;
10. emit exactly one terminal `done` or `error`;
11. update health.

### `providers/base.py`

Canonical internal contract:

```python
ProviderAdapter.stream(ProviderRequest) -> AsyncIterator[ProviderEvent]
ProviderAdapter.aclose() -> None
```

Canonical provider events:

```text
TextDelta
Usage
Completed
```

Failures use normalized `ProviderError` exceptions instead of error events.

### `providers/openai_protocol.py`

MVP concrete implementation for OpenAI-compatible endpoints.

Owns:

- async client setup;
- Chat Completions request translation;
- stream chunk normalization;
- NVIDIA `reasoning_content` suppression;
- usage extraction;
- finish-reason normalization;
- status/exception → `ProviderError` mapping;
- provider-specific opaque `extra_body` injection.

Does not own:

- model choice;
- fallback candidate choice;
- global attempt budget;
- public NDJSON sequence numbering.

## 5. Provider Client Lifecycle

Create one reusable client per configured provider in FastAPI lifespan.

Conceptual lifecycle:

```text
startup
  load config
  construct ProviderRegistry
  construct AsyncOpenAI per usable OpenAI-compatible provider

requests
  reuse clients

shutdown
  await adapter.aclose()
```

Do not construct an HTTP/OpenAI client per user message.

SDK retry must be disabled so Project H controls the retry count.

## 6. Internal Provider Contract

### ProviderRequest

```text
request_id
upstream_model
messages
timeout_seconds
max_output_tokens
provider_request_extra
```

Do not pass routing profile, browser health UI state, fallback chain, or FastAPI objects into the adapter.

### Provider events

```text
TextDelta(text)
Usage(input_tokens?, output_tokens?, total_tokens?)
Completed(finish_reason, provider_request_id?)
```

Nemotron reasoning deltas are not canonical `TextDelta` events.

## 7. Public Stream State Machine

```text
                ┌───────────────┐
                │ request valid │
                └──────┬────────┘
                       ▼
                    start
                       │
              ┌────────┴─────────┐
              │                  │
      pre-token failure       visible delta
              │                  │
      retry/fallback legal        │
              │                  │
         fallback*                │
              │                  │
              └────────┬─────────┘
                       ▼
                    delta*
                       │
                 [usage optional]
                       │
              ┌────────┴────────┐
              ▼                 ▼
             done              error
```

Once the first visible `delta` leaves the backend, fallback is irreversibly disabled for that request.

## 8. Cancellation

Browser:

```text
AbortController.abort()
```

Backend:

- async generator must contain actual await points;
- cancellation propagates through FastAPI/Starlette streaming task;
- adapter should close/exit the upstream stream context promptly;
- health should not count explicit user cancellation as provider failure.

No `/cancel` endpoint in MVP.

## 9. Context Handling

Browser sends portable full transcript every turn.

Advantages:

- switch provider next turn;
- Auto routing remains provider-neutral;
- no provider conversation IDs;
- no server DB.

Tradeoff:

- longer conversations resend more context and increase latency/tokens.

MVP accepts this tradeoff. Context trimming/summarization is future work.

A conservative approximate context estimator may use characters/3 plus safety margin for routing. Do not add provider tokenizer packages solely for routing.

## 10. NVIDIA Stream Normalization

Expected conceptual upstream chunk categories include:

```text
reasoning_content  → ignore in MVP public output
content            → canonical TextDelta when non-empty
usage              → canonical Usage when available
finish_reason      → canonical Completed
```

Provider-specific tool-call fields are ignored/rejected for MVP because tools are out of scope.

If NVIDIA returns a valid final answer after reasoning-only chunks, public TTFT is time to first visible `content`, not time to first SSE packet.

## 11. Error Mapping Boundary

Adapter maps provider/transport failure into canonical `ProviderError`:

```text
code
retryable
provider_id
model_id
status_code?
retry_after_seconds?
safe_message
```

Raw error body stays internal and should be redacted in logs.

Orchestrator decides whether a normalized error gets retried, falls back, or becomes a public terminal error.

## 12. Frontend Architecture

No frontend framework.

`app.js` may be divided internally into small functions/objects but stays one file for MVP unless it genuinely becomes hard to maintain.

Suggested conceptual sections:

```text
state
bootstrap
history/localStorage
rendering
NDJSON streaming parser
request lifecycle
settings dialog
mobile drawer
DOM event binding
```

Do not create a frontend class hierarchy.

### Browser state

Minimal state:

```text
bootstrap data
active conversation ID
conversations
selection mode/model/profile
active AbortController
active request ID
streaming boolean
settings open
history drawer open
```

## 13. Security Boundary

Secrets exist only in backend process environment.

Browser may know:

```text
provider ID/name
configured boolean
health
model IDs
public latency/token metadata
```

Browser must never receive:

```text
API key
Authorization header
raw environment value
provider raw request
provider raw reasoning trace
```

Same-origin local app means no permissive CORS is needed.

## 14. Evolution Without Rewrite

Future provider:

```text
OpenAI-compatible → config only when protocol behavior fits
non-compatible    → new ProviderAdapter implementation
```

Future server history:

```text
add repository/persistence behind browser/API changes later
SQLite before Postgres for single-user local mode
```

Future tools/agents:

```text
add an execution layer above provider adapters
```

Do not put tool execution inside `OpenAIProtocolAdapter`.

Future frontend framework migration, if ever justified, can preserve `/api/v1` and stream grammar.
