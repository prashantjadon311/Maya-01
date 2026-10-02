# Project H — TDD Implementation Plan

**Executor:** Gemini in Antigravity  
**Plan type:** sequential, dependency-driven  
**Primary live API:** NVIDIA Nemotron 3 Ultra  
**Frontend authority:** Figma + `DOCS.md`

## Planning Principles

- Build from contracts inward, not UI inward.
- Every phase has tests before implementation.
- Fake providers prove deterministic retry/fallback/cancellation behavior.
- Live NVIDIA calls are smoke tests, not ordinary unit tests.
- Keep commits small enough that a failed phase can be reverted cleanly.
- Do not implement future providers merely because the interface supports them.

---

## Phase 0 — Repository Bootstrap

### Goal

Create the smallest reproducible Python project capable of running tests and FastAPI.

### Files

```text
pyproject.toml
.gitignore
.env.example
app/__init__.py
tests/conftest.py
```

### Dependencies

Runtime target:

```text
fastapi
uvicorn
pydantic
openai
```

Developer/test target:

```text
pytest
pytest-anyio or compatible async test support
httpx / framework-required async testing transport if not transitively usable
```

Do not add optional packages before a test/use case requires them.

### Acceptance

```text
python import of app succeeds
pytest starts with zero collection/import errors
no secret-bearing file is tracked
```

---

## Phase 1 — Canonical Schemas

### Goal

Freeze runtime datatypes before provider/network code.

### Files

```text
app/schemas.py
tests/test_schemas.py
```

### RED tests

Cover:

- valid user/assistant messages;
- empty message rejected;
- Auto selection shape;
- Manual selection shape;
- invalid mixed selection rejected;
- allowed error codes;
- allowed finish reasons;
- stream event required fields;
- sequence number non-negative;
- forbidden unknown request fields.

### GREEN implementation

Use Pydantic v2 models and discriminated selection schema.

Do not add provider SDK types.

### Acceptance

All schema tests pass and the public data model matches `DOCS.md`.

---

## Phase 2 — Strict Configuration

### Goal

Parse `config.toml`, resolve env secrets safely, and validate references.

### Files

```text
app/config.py
config.toml
.env.example
tests/test_config.py
```

### RED tests

- canonical NVIDIA config loads;
- unknown top-level/config field fails;
- duplicate provider IDs fail;
- duplicate model IDs fail;
- model referencing unknown provider fails;
- profile referencing unknown model fails;
- missing default profile fails;
- non-positive runtime limits fail;
- absent `NVIDIA_API_KEY` does not crash startup model validation;
- provider becomes `configured=false` when key is absent;
- provider request-extra nested mapping is retained.

### GREEN implementation

Use stdlib `tomllib` plus Pydantic models.

Do not require `python-dotenv` unless the desired local workflow explicitly needs automatic `.env` loading. A shell-exported key is sufficient for MVP.

### Acceptance

Malformed structural config fails early with precise errors. Missing provider secret disables only that provider.

---

## Phase 3 — Provider Contract + Fake Provider

### Goal

Create an SDK-independent provider seam and deterministic test double.

### Files

```text
app/providers/__init__.py
app/providers/base.py
tests/fakes.py
tests/test_provider_contract.py
```

### Define

```text
ProviderRequest
TextDelta
Usage
Completed
ProviderError
ProviderAdapter Protocol
```

### Fake provider capabilities

Fake must be scriptable to:

- emit deltas;
- emit usage;
- complete normally;
- fail before first token;
- fail after N deltas;
- sleep/timeout;
- observe cancellation;
- record call count and request payload.

### Acceptance

The rest of the routing/orchestration test suite can run without external API/network access.

---

## Phase 4 — NVIDIA/OpenAI-Compatible Adapter

### Goal

Stream Nemotron through one generic OpenAI-compatible adapter without leaking provider details upward.

### Files

```text
app/providers/openai_protocol.py
tests/test_nvidia_adapter.py
```

### Client construction

Use one reusable `AsyncOpenAI`-style client per provider with:

```text
api_key from env
base_url from config
max_retries = 0
configured timeout
```

### RED adapter tests with mocked transport/client

- non-empty content delta → `TextDelta`;
- empty content ignored;
- `reasoning_content` ignored;
- reasoning-only chunks do not create visible delta;
- usage normalized when present;
- missing usage allowed;
- finish reason normalized;
- provider request ID retained internally when available;
- 401/403 → AUTH;
- 429 → RATE_LIMIT + retry-after when parseable;
- timeout → TIMEOUT;
- transport error → NETWORK;
- 5xx → UNAVAILABLE;
- invalid provider request → INVALID_REQUEST;
- adapter close closes reusable client.

### NVIDIA request behavior

Use Chat Completions with `stream=true`.

Provider-only request extras from config may include NVIDIA chat-template reasoning controls. Keep them opaque to public request schema.

### Live test

`tests/test_live_nvidia.py` must be skipped unless explicitly enabled and `NVIDIA_API_KEY` is present.

Live test proves visible text can be streamed from:

```text
https://integrate.api.nvidia.com/v1
nvidia/nemotron-3-ultra-550b-a55b
```

It must also assert the application-facing event path does not expose reasoning trace.

---

## Phase 5 — Runtime Health

### Goal

Track enough state for deterministic Auto routing without background infrastructure.

### Files

```text
app/health.py
tests/test_routing.py   # or dedicated test_health.py if clearer
```

### Behaviors

- initial health unknown;
- success resets consecutive transient failures;
- transient failure increments count;
- threshold enters cooldown;
- cooldown expires by timestamp;
- explicit user cancellation is not provider failure;
- latency EMA updates after successful generation.

Use injectable clock/time in tests where useful rather than sleeping.

---

## Phase 6 — Router

### Goal

Resolve manual and Auto candidates purely from configuration + runtime health.

### Files

```text
app/routing.py
tests/test_routing.py
```

### Manual tests

- exact known enabled model resolves;
- unknown model → MODEL_NOT_FOUND equivalent domain error;
- disabled/unconfigured provider is rejected;
- cooldown does not silently substitute another model in manual mode.

### Auto tests

Ordered pipeline:

```text
profile order
→ enabled model
→ enabled/configured provider
→ capability fit
→ not cooldown
→ context fit when metadata available
→ first candidate
```

Initial live config may have one candidate. Tests should use multiple fake configured models to prove ordering/fallback selection without configuring additional commercial APIs.

### Context estimate

Use a conservative approximate function such as characters/3 + margin. Keep it isolated and documented as routing estimate only.

---

## Phase 7 — Orchestrator

### Goal

Implement the hardest correctness rules before HTTP/UI.

### Files

```text
app/orchestrator.py
tests/test_orchestrator.py
```

### Required RED cases

1. Normal successful stream:

```text
start → delta* → usage? → done
```

2. Pre-token transient failure with retry.

3. Pre-token failure exhausting same-model retry then Auto fallback.

4. Manual mode never cross-model fallbacks.

5. First visible delta permanently disables fallback.

6. Post-delta provider failure:

```text
start → delta... → error(partial_output=true)
```

7. Attempt budget cannot be exceeded.

8. Auth failure not retried.

9. Timeout skips same-candidate retry according to contract.

10. Cancellation terminates upstream iteration and does not mark provider unhealthy.

11. Sequence numbers remain monotonic across retry/fallback events.

12. Exactly one terminal public event.

13. TTFT starts at first visible content, not provider reasoning packet.

### Acceptance

No HTTP/FastAPI object is necessary to test orchestrator behavior.

---

## Phase 8 — FastAPI Application/API

### Goal

Expose the frozen `/api/v1` contract and lifecycle.

### Files

```text
app/main.py
app/api.py
tests/test_api.py
```

### Lifespan

Startup:

```text
load validated config
create health store
create provider registry
create configured adapters/clients
create orchestrator
```

Shutdown:

```text
await all adapter/client closes
```

### Endpoint tests

`GET /healthz`

- returns `{"status":"ok"}`;
- no provider call.

`GET /api/v1/bootstrap`

- shows configured false when key missing;
- never includes env secret value;
- contains public routing/model data.

`POST /api/v1/chat/stream`

- content type NDJSON;
- one valid JSON object per newline;
- preserves event order;
- pre-stream validation uses proper HTTP error JSON;
- post-start failure becomes stream `error` event;
- disconnect/cancellation closes generation task where test harness permits verification.

---

## Phase 9 — Static Dashboard Shell

### Goal

Match the frozen Figma hierarchy with zero frontend build tooling.

### Files

```text
app/web/index.html
app/web/app.css
app/web/app.js
```

### First UI milestone

Static, no generation yet:

- desktop sidebar;
- topbar model/routing controls;
- conversation area;
- composer;
- settings dialog;
- mobile responsive rules;
- provider status display.

Use Figma tokens and dimensions from `DOCS.md`.

No framework, icon library, Markdown package, or charting package.

### Acceptance

Page works directly from FastAPI static serving. No `npm`, `node_modules`, frontend bundling, or generated CSS.

---

## Phase 10 — Browser Streaming Lifecycle

### Goal

Wire real API behavior into the UI.

### `app.js` behaviors

- bootstrap load;
- Auto/manual selection;
- construct chat request;
- POST with `fetch`;
- incremental UTF-8 decode;
- NDJSON partial-line buffer;
- event dispatcher;
- streaming assistant message update;
- Stop via AbortController;
- Retry;
- Regenerate;
- metadata update;
- fallback/status presentation;
- normalized error rendering.

### Parser robustness tests

If JavaScript unit infrastructure would require a frontend toolchain, do not add one just for MVP. Instead keep NDJSON parser functions simple, and verify with browser/manual integration plus Python API tests. A tiny browserless JS test is optional only if it can use existing runtime without adding a heavy build stack.

### Security

Never render model output with raw `innerHTML`.

---

## Phase 11 — Local History and Settings

### Goal

Complete the single-user local product flow.

### Browser storage

Store:

```text
conversations
active conversation
preferences
history persistence setting
```

Never store:

```text
API keys
reasoning traces
raw provider response bodies
```

### Behaviors

- New chat;
- recent list;
- open conversation;
- retry/regenerate state update;
- clear/delete history;
- persistence toggle;
- mobile drawer;
- Settings open/close.

---

## Phase 12 — Hardening

### Required regression scenarios

- missing NVIDIA key;
- invalid key/auth failure;
- 429;
- 5xx;
- timeout;
- network disconnect;
- malformed provider chunk;
- provider closes without content;
- partial stream failure;
- cancellation;
- large conversation near configured request-size limit;
- context estimate rejects unsuitable fake model;
- provider usage fields absent;
- config typo rejected;
- browser localStorage unavailable/quota exception handled without breaking active chat.

### Logging audit

Search codebase and test that secrets/prompts/reasoning are not intentionally logged.

---

## Phase 13 — Final Verification

Run:

```text
full pytest suite
local uvicorn startup
healthz
bootstrap
manual browser chat with live NVIDIA key
Stop
Retry
history refresh
mobile responsive check
```

Then inspect Git diff for accidental dependency/scope expansion.

Final result packet follows `EXECUTION.md`.
