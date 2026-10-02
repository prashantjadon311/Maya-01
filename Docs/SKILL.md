---
name: project-h-implementation
# This skill is intentionally project-scoped because it is the execution contract for this repository.
description: Use when implementing, testing, debugging, reviewing, or resuming Project H in Gemini/Antigravity.
---

# Project H Implementation Skill

## Purpose

Project H is a **small, local-first, multi-provider AI chat/orchestration application**. Gemini in Antigravity is the implementation agent. The first live runtime provider is **NVIDIA Nemotron 3 Ultra** through NVIDIA's hosted OpenAI-compatible API.

The implementation must remain small enough to understand as one Python application and light enough to run comfortably on modest hardware. Do not turn it into an agent platform, framework showcase, or miniature cloud company.

## Authority Order

Before changing code, read these files in order:

1. `DOCS.md` — product requirements and API/UI contract.
2. `ARCHITECTURE.md` — module boundaries and data flow.
3. `PLAN.md` — implementation sequence and test strategy.
4. `TASKS.md` — current executable checklist.
5. `EXECUTION.md` — exact Antigravity operating procedure.
6. Figma dashboard file referenced in `DOCS.md` when implementing frontend UI.

When documents conflict, use this precedence:

`DOCS.md > ARCHITECTURE.md > PLAN.md > TASKS.md > implementation code`

Do not silently redesign an authority document to make existing code easier.

## Non-Negotiable Boundaries

- One FastAPI process.
- Vanilla HTML + CSS + JavaScript frontend. No React/Vite/Next/Tailwind build chain in MVP.
- No database, Redis, Celery, Kafka, microservices, WebSocket, LangChain, or LiteLLM in MVP.
- Browser owns conversation history via `localStorage`.
- Backend owns API keys, provider clients, routing, retry/fallback, health state, and normalized events.
- Public generation endpoint is `POST /api/v1/chat/stream` using NDJSON.
- Provider-specific response objects must never reach the browser.
- SDK retries must be disabled; Project H owns the retry budget.
- Automatic provider/model fallback is allowed only **before the first visible output delta**.
- Never expose or log raw reasoning traces from Nemotron.
- Never log API keys, authorization headers, prompts, or generated content by default.
- Bind locally to `127.0.0.1` by default.

## NVIDIA Runtime Rule

First live model:

- Provider: `nvidia`
- Hosted base URL: `https://integrate.api.nvidia.com/v1`
- Model: `nvidia/nemotron-3-ultra-550b-a55b`
- Protocol: OpenAI-compatible Chat Completions
- Streaming: enabled
- Secret env var: `NVIDIA_API_KEY`

Use an async OpenAI-compatible client and set SDK `max_retries=0`.

Nemotron may stream provider-specific reasoning fields such as `reasoning_content`. Ignore those for the MVP user-visible stream. Measure TTFT from the first non-empty **visible content** delta.

For NVIDIA-only request options, use adapter/config-owned provider extras rather than adding provider-specific fields to the public Project H request schema.

## Development Discipline

For every task:

1. Read the relevant authority section.
2. Write or identify the failing test first.
3. Run it and capture the failure.
4. Implement the smallest code required to pass.
5. Run targeted tests.
6. Run the relevant regression set.
7. Update `TASKS.md` with evidence before moving on.

Never claim a feature works because the code looks correct. Evidence means an actual test, command, HTTP call, or browser behavior check.

## Stop Conditions

Stop and report instead of guessing when:

- a required contract is ambiguous;
- the NVIDIA API behavior differs materially from the authority docs;
- a requested change requires breaking the frozen `/api/v1` contract;
- implementation would require a new heavy dependency;
- a secret is missing for a live-provider test;
- a Figma detail cannot be inspected and the implementation choice would materially alter layout/behavior.

Minor visual details may use the numeric design tokens in `DOCS.md` without blocking.
