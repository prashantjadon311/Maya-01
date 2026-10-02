# Project H — Execution Tasks

This is the mutable execution checklist for Gemini/Antigravity. Update checkboxes and evidence as work proceeds. Do not mark complete from code inspection alone.

## Status Legend

```text
[ ] not started
[~] in progress
[x] verified complete
[!] blocked
```

---

## PH-000 — Repository Baseline

- [ ] Confirm repository root and Git status.
- [ ] Add/verify `pyproject.toml` with minimal runtime/test dependencies.
- [ ] Add/verify `.gitignore` excludes `.env`, virtualenvs, caches, coverage artifacts.
- [ ] Add `.env.example` containing `NVIDIA_API_KEY=` only as placeholder.
- [ ] Create `app/`, `app/providers/`, `app/web/`, and `tests/` package/tree.
- [ ] Verify `pytest` launches without import/collection failure.

**Evidence:**

```text
COMMANDS:
RESULT:
COMMIT:
```

---

## PH-010 — Public and Canonical Schemas

Depends on: PH-000

- [ ] Write failing schema tests first.
- [ ] Implement canonical chat messages.
- [ ] Implement Auto/manual selection discriminated union.
- [ ] Implement chat request validation.
- [ ] Implement bootstrap DTOs.
- [ ] Implement `start/delta/fallback/usage/done/error` event models.
- [ ] Implement normalized error and finish-reason enums.
- [ ] Forbid unknown public request fields.
- [ ] Run targeted schema tests.

**Acceptance:** public shapes match `DOCS.md` exactly.

**Evidence:**

```text
TESTS:
RESULT:
COMMIT:
```

---

## PH-020 — Strict Configuration

Depends on: PH-010

- [ ] Write config RED tests.
- [ ] Implement `tomllib` loader.
- [ ] Implement strict Pydantic config models.
- [ ] Implement provider/model/profile cross-reference validation.
- [ ] Implement env secret presence resolution.
- [ ] Ensure absent NVIDIA key does not crash startup/config parse.
- [ ] Add canonical `config.toml` for NVIDIA Nemotron 3 Ultra.
- [ ] Preserve provider `request_extra` mapping for NVIDIA-only chat-template fields.
- [ ] Verify typo/unknown config fields fail.

**Acceptance:** structural config errors fail early; missing key only marks provider unconfigured.

---

## PH-030 — Provider Base Contract + Fake

Depends on: PH-010

- [ ] Write provider-contract tests.
- [ ] Implement `ProviderRequest`.
- [ ] Implement `TextDelta`, `Usage`, `Completed`.
- [ ] Implement `ProviderError`.
- [ ] Implement `ProviderAdapter` protocol.
- [ ] Implement scriptable fake provider for tests.
- [ ] Fake supports pre-token fail, post-token fail, timeout, usage, cancellation, call counting.

**Acceptance:** later router/orchestrator tests need no live network.

---

## PH-040 — OpenAI-Compatible NVIDIA Adapter

Depends on: PH-020, PH-030

- [ ] Write adapter RED tests with mocked upstream client/stream.
- [ ] Create reusable async client with custom NVIDIA base URL.
- [ ] Set SDK retries to zero.
- [ ] Use Chat Completions streaming.
- [ ] Pass configured NVIDIA request extras.
- [ ] Normalize non-empty assistant content to `TextDelta`.
- [ ] Ignore `reasoning_content`.
- [ ] Normalize usage.
- [ ] Normalize finish reason.
- [ ] Map auth/rate-limit/timeout/network/5xx/invalid-request errors.
- [ ] Parse `Retry-After` when available.
- [ ] Implement adapter/client close.
- [ ] Add opt-in live NVIDIA smoke test.

**Live target:**

```text
https://integrate.api.nvidia.com/v1
nvidia/nemotron-3-ultra-550b-a55b
```

**Acceptance:** a live key can stream visible content while no reasoning trace crosses the adapter boundary.

---

## PH-050 — Runtime Health Store

Depends on: PH-030

- [ ] Write deterministic health-state tests.
- [ ] Implement last success/failure state.
- [ ] Implement transient failure count.
- [ ] Implement cooldown threshold/expiry.
- [ ] Implement latency EMA.
- [ ] Ensure cancellation does not penalize provider health.

---

## PH-060 — Router

Depends on: PH-020, PH-050

- [ ] Write manual routing RED tests.
- [ ] Resolve exact manual model.
- [ ] Reject unknown/disabled/unconfigured manual target.
- [ ] Write Auto routing RED tests using fake config/models.
- [ ] Filter by enabled/configured.
- [ ] Filter by required capability.
- [ ] Skip cooldown candidate.
- [ ] Implement conservative context-fit estimate.
- [ ] Preserve configured profile order.
- [ ] Do not use an LLM to route an LLM.

---

## PH-070 — Orchestrator

Depends on: PH-030, PH-050, PH-060

- [ ] Write normal-stream test.
- [ ] Emit `start` first with seq=0.
- [ ] Normalize visible provider deltas.
- [ ] Measure first visible token latency.
- [ ] Emit optional usage at most once.
- [ ] Emit exactly one terminal event.
- [ ] Implement eligible same-model retry.
- [ ] Implement max upstream attempt budget.
- [ ] Implement Auto fallback before first visible delta.
- [ ] Prove manual mode never cross-model fallbacks.
- [ ] Prove post-delta fallback is forbidden.
- [ ] Post-delta failure emits `error(partial_output=true)`.
- [ ] Handle cancellation without unhealthy penalty.
- [ ] Keep seq monotonic across retry/fallback.

**Critical acceptance:** no test can produce `delta → fallback`.

---

## PH-080 — FastAPI Lifespan + API

Depends on: PH-020, PH-040, PH-070

- [ ] Write API RED tests.
- [ ] Build FastAPI app factory/construction.
- [ ] Use lifespan for config/registry/client startup and close.
- [ ] Implement `GET /healthz` with zero upstream calls.
- [ ] Implement `GET /api/v1/bootstrap`.
- [ ] Ensure bootstrap never includes secret values.
- [ ] Implement `POST /api/v1/chat/stream`.
- [ ] Encode each public event as one NDJSON line.
- [ ] Use `application/x-ndjson`.
- [ ] Handle pre-stream validation with normal JSON HTTP errors.
- [ ] Handle post-start failures as stream `error` events.
- [ ] Verify async cancellation path.

---

## PH-090 — Static Dashboard Layout

Depends on: PH-080

Figma authority: `https://www.figma.com/design/32qadE21g6ZK8g5afK1bt0`

- [ ] Implement `index.html` semantic structure.
- [ ] Implement `app.css` using frozen design tokens.
- [ ] Desktop sidebar 240px reference.
- [ ] Topbar with Auto/model selector and Settings.
- [ ] Conversation viewport.
- [ ] Composer with Send/Stop states.
- [ ] Provider status block.
- [ ] Settings dialog.
- [ ] Mobile layout at 390px reference.
- [ ] History drawer on mobile.
- [ ] No framework/build chain/icon package.

**Acceptance:** UI hierarchy matches Figma frames 2:2, 2:80, 2:144, and 2:174 closely without adding visual complexity.

---

## PH-100 — Browser Bootstrap + Streaming

Depends on: PH-090

- [ ] Fetch `/api/v1/bootstrap` on startup.
- [ ] Populate Auto/profile/model controls.
- [ ] Build portable request body.
- [ ] Implement `fetch` POST stream.
- [ ] Implement UTF-8 incremental decoder.
- [ ] Implement robust newline buffer for split NDJSON chunks.
- [ ] Dispatch all six event types.
- [ ] Stream assistant text incrementally.
- [ ] Show quiet fallback event.
- [ ] Update usage/latency metadata.
- [ ] Implement Stop using AbortController.
- [ ] Ensure Stop does not display a fake provider failure.
- [ ] Render output through safe text nodes / `textContent`.

---

## PH-110 — Conversation History + Retry/Regenerate

Depends on: PH-100

- [ ] Define browser-local conversation schema.
- [ ] Persist conversations to `localStorage` when enabled.
- [ ] Restore on refresh.
- [ ] New chat.
- [ ] Open recent conversation.
- [ ] Delete/clear history.
- [ ] Persistence toggle.
- [ ] Retry failed request.
- [ ] Regenerate last assistant answer from prior user turn.
- [ ] Handle localStorage exceptions without breaking live chat.
- [ ] Never store API keys or reasoning traces.

---

## PH-120 — UI Error / Operational States

Depends on: PH-100

- [ ] Empty state.
- [ ] Starting state.
- [ ] Streaming state.
- [ ] Completed state.
- [ ] Pre-token fallback state.
- [ ] Rate-limit state.
- [ ] Provider unavailable state.
- [ ] Partial-stream error state.
- [ ] Stopped state.
- [ ] Provider-not-configured state.
- [ ] Settings open/closed.
- [ ] Mobile history drawer open/closed.

**Acceptance:** no global blocking spinner; active message owns its own progress state.

---

## PH-130 — Hardening Regression

Depends on: PH-080, PH-110, PH-120

- [ ] Missing NVIDIA key.
- [ ] Invalid NVIDIA key / AUTH.
- [ ] 429 / RATE_LIMIT.
- [ ] 5xx / UNAVAILABLE.
- [ ] timeout.
- [ ] transport/network failure.
- [ ] malformed chunk.
- [ ] provider completes with no visible content.
- [ ] partial stream then failure.
- [ ] user cancellation.
- [ ] context-fit rejection on fake model.
- [ ] usage absent.
- [ ] request-size validation.
- [ ] config typo.
- [ ] logging redaction audit.

---

## PH-140 — Final Verification

Depends on: all previous

- [ ] Full `pytest` PASS.
- [ ] Local Uvicorn start PASS.
- [ ] `/healthz` PASS.
- [ ] `/api/v1/bootstrap` PASS.
- [ ] Live NVIDIA manual stream PASS with opt-in key.
- [ ] Auto with NVIDIA as only configured candidate PASS.
- [ ] Stop PASS.
- [ ] Retry/Regenerate PASS.
- [ ] Refresh history PASS.
- [ ] Mobile responsive manual check PASS.
- [ ] No secret/reasoning leakage found.
- [ ] Git diff reviewed for scope/dependency creep.
- [ ] README/run instructions updated.
- [ ] Final result packet generated per `EXECUTION.md`.

---

# Current Checkpoint

```text
CURRENT_TASK: PH-000
STATUS: READY_FOR_GEMINI_EXECUTION
ARCHITECTURE_FROZEN: yes
FIGMA_CREATED: yes
LIVE_PROVIDER: NVIDIA Nemotron 3 Ultra
NEXT_EXACT_ACTION: Gemini reads authority files, inspects repo, creates/updates Antigravity task artifact, and begins PH-000 without redesigning the system.
```
