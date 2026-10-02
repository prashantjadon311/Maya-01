# Project H — Gemini / Antigravity Execution Protocol

**Execution Agent:** Gemini in Antigravity  
**Runtime AI Provider:** NVIDIA Nemotron 3 Ultra  
**Project type:** lightweight local Python web application  
**Mode:** test-driven, checkpointed, architecture-preserving

## 1. Start / Resume Procedure

At the start of every Antigravity session:

1. Locate the repository root.
2. Read `SKILL.md`.
3. Read `DOCS.md`, `ARCHITECTURE.md`, `PLAN.md`, and `TASKS.md`.
4. Inspect the actual repository tree and current Git status.
5. Do not assume a task is incomplete merely because the plan says so. Verify code/tests first.
6. Create or update Antigravity's task artifact from `TASKS.md` and keep it current throughout the session.
7. Resume at the first genuinely unfinished task whose dependencies are satisfied.

Antigravity task tracking rule: use a task artifact/checklist, not background-process management, as the source of truth for execution progress.

## 2. Before Writing Code

For the current task, state internally:

- exact task ID from `TASKS.md`;
- files expected to change;
- tests that prove success;
- authority sections that constrain the change;
- whether a live NVIDIA call is required or a fake provider is sufficient.

Use Context7 MCP for current FastAPI, Pydantic, and OpenAI Python SDK APIs when an API detail is uncertain. Prefer official NVIDIA documentation for Nemotron/NIM behavior.

Do not browse for architecture inspiration after the architecture is frozen. Research is for verifying changing APIs, not reopening solved design decisions.

## 3. TDD Loop

For each behavior:

### RED

- Add the smallest test proving the missing behavior.
- Run that test alone.
- Confirm it fails for the expected reason.

### GREEN

- Implement the minimal code required.
- Do not add unrelated abstractions or future features.
- Re-run the targeted test until it passes.

### REFACTOR

- Simplify names, duplication, or boundaries only when behavior stays unchanged.
- Run targeted tests again.
- Run the phase regression set.

A task is not complete until acceptance criteria in `TASKS.md` are demonstrably satisfied.

## 4. Commit / Checkpoint Policy

Prefer one coherent commit per completed task or tightly coupled task group.

Before a commit:

```text
pytest <targeted tests>
pytest
```

When frontend work exists, additionally verify the local app manually in a browser for the specific flow being changed.

Commit messages should be descriptive, e.g.:

```text
feat(config): add strict Project H config validation
feat(provider): stream Nemotron chat completions
feat(router): enforce pre-token fallback invariant
feat(ui): implement lightweight streaming dashboard
```

Do not commit `.env`, local secrets, generated caches, virtualenvs, or browser history data.

## 5. Exact Implementation Order

Do not start with the dashboard.

Execute in this order:

```text
Repository/bootstrap
→ canonical schemas
→ strict config loader
→ provider protocol + fake provider
→ NVIDIA OpenAI-compatible adapter
→ routing + health state
→ orchestrator + retry/fallback
→ FastAPI endpoints + NDJSON
→ dashboard shell
→ browser streaming/cancel/history
→ hardening/integration tests
→ final documentation and verification
```

If a later layer seems to require changing an earlier public contract, stop and report the incompatibility rather than patching around it.

## 6. NVIDIA Integration Procedure

Use NVIDIA's hosted endpoint for the first real provider.

Environment:

```bash
export NVIDIA_API_KEY="..."
```

Never place the real key in source-controlled TOML.

Provider defaults:

```text
base_url      = https://integrate.api.nvidia.com/v1
model          = nvidia/nemotron-3-ultra-550b-a55b
api_style      = chat_completions
stream         = true
sdk retries    = 0
```

NVIDIA supports reasoning controls and may emit `reasoning_content` separately from user-visible content. Project H MVP must:

- never send reasoning trace to the browser;
- never persist reasoning trace in browser history;
- never log reasoning trace by default;
- calculate visible TTFT from first content delta, not first reasoning delta;
- preserve only final assistant content in portable conversation history.

NVIDIA's current model documentation notes a coding-agent compatibility option `force_nonempty_content`. Keep NVIDIA-only chat-template options in provider configuration/adapter internals, not in public API schemas.

## 7. Retry / Fallback Execution Rules

Project H owns all retry policy. Configure OpenAI SDK clients with `max_retries=0`.

A single user request has a hard maximum upstream-attempt budget.

Same-model retry may be used only for eligible transient conditions defined in `DOCS.md`.

Critical rule:

```text
Before first visible delta: fallback may occur.
After first visible delta: fallback is forbidden.
```

After partial output, terminate with a normalized error and let the user Retry from scratch. Never concatenate two models' answers.

## 8. Frontend Execution Rules

Authority: Figma file + numeric UI contract in `DOCS.md`.

Implementation constraints:

- `index.html`
- `app.css`
- `app.js`
- no build step;
- no frontend framework;
- no icon package;
- no chart package;
- no Markdown renderer in MVP;
- render model text using safe text nodes / `textContent` and `white-space: pre-wrap`;
- use `fetch()` + `ReadableStream` for NDJSON;
- use `AbortController` for Stop;
- use native `<dialog>` or similarly lightweight markup for Settings;
- use `localStorage` only for local conversation history/preferences.

The dashboard must remain usable with only NVIDIA configured. Other providers may appear as `Not configured` placeholders if defined in bootstrap/config.

## 9. Frontend Required States

Gemini must explicitly implement and test these UI states:

```text
initial / empty
request starting
streaming
completed
fallback before first visible token
rate limited / unavailable
partial-stream error
stopped by user
provider not configured
history empty / populated
mobile history drawer
settings open / closed
```

Do not invent a global spinner that blocks the whole app. Streaming is local to the active assistant message.

## 10. Verification Matrix

### Unit

- Pydantic schemas
- config references/invariants
- router filtering/order
- retry decisions
- health/cooldown state
- event sequence invariants
- provider error mapping

### Fake-provider integration

- normal streaming
- pre-token failure then fallback
- partial output then failure
- cancellation
- usage event
- timeout
- rate limit
- auth failure

### Live NVIDIA smoke tests

Only when `NVIDIA_API_KEY` exists:

- bootstrap shows NVIDIA configured;
- manual Nemotron request streams visible content;
- Auto route selects Nemotron when it is the only live candidate;
- usage/latency are handled without crashing if optional fields are missing;
- Stop cancels the browser stream cleanly;
- no reasoning trace appears in browser payload/history/logs.

Live tests should be opt-in/marked so normal `pytest` does not consume API quota.

## 11. Definition of Done

Project H MVP is done only when:

- all normal tests pass;
- live NVIDIA smoke test passes when a key is supplied;
- the dashboard works without a frontend build tool;
- Stop works;
- browser refresh restores history when persistence is enabled;
- missing API key does not crash startup;
- raw secrets/reasoning/provider payloads do not leak;
- fallback invariant is proven by tests;
- app binds to `127.0.0.1` by default;
- repository contains no unnecessary service/dependency introduced during implementation.

## 12. Final Gemini Result Packet

When implementation is finished, return a concise result packet containing:

```text
STATUS: PASS / PARTIAL / BLOCKED
COMPLETED_TASKS:
FILES_CHANGED:
TESTS_RUN:
TEST_RESULTS:
LIVE_NVIDIA_TEST:
MANUAL_UI_CHECK:
KNOWN_LIMITATIONS:
ARCHITECTURE_DEVIATIONS: none | explicit list
GIT_STATUS:
LAST_COMMIT:
NEXT_EXACT_ACTION:
```

Never report `PASS` while known required tests are failing or unexecuted.
