---
name: project-h-engineering
description: Use when implementing, reviewing, debugging or extending Project H, a lightweight Ubuntu personal AI assistant with voice wake, permission-controlled browser/files/terminal actions, NVIDIA Nemotron, and a hard 300 MiB resident-memory acceptance limit.
---

# Project H Engineering Skill

## Authority order

When instructions conflict, use this order:

1. `DOCS.md` — product requirements and frozen behavior.
2. `SECURITY.md` — permission/security invariants.
3. `ARCHITECTURE.md` — component boundaries and allowed dependencies.
4. `CONFIG.md` — canonical configuration/action schemas.
5. `UI.md` — dashboard and tray UI contract.
6. `PLAN.md` — implementation sequencing.
7. `TASKS.md` — task checklist and acceptance evidence.
8. `EXECUTION.md` — execution procedure.

Do not silently change a higher-authority contract to make a lower-level implementation easier.

## Engineering principles

- Keep one long-lived Python process wherever practical.
- Prefer stdlib and small libraries.
- Use `asyncio`; do not create a thread/process per agent.
- A "logical agent" is state in the existing process, not another Python runtime.
- Never run a local LLM in V1.
- Use NVIDIA-hosted Nemotron for complex reasoning/tool selection.
- Do not call an LLM when a deterministic action resolver can answer safely.
- The policy engine must approve an action before any executor receives it.
- Every executor receives typed validated arguments, not raw natural language.
- Use argv-based subprocess execution; `shell=False` by default.
- Treat browser, terminal, file write/delete, clipboard secrets and credentials as capability boundaries.
- Do not log prompts, ambient audio, passwords, API keys, page secrets or full file contents by default.
- All browser actions must carry the current tab URL and pass domain policy before execution.
- All file paths must be canonicalized and checked against configured roots after symlink resolution.
- All state-changing tool calls must generate an audit event.

## Memory discipline

The target is not "probably lightweight". It is measurable:

- `MemoryHigh=240M`
- `MemoryMax=300M`
- one worker
- no resident Chromium instance owned by Project H;
- no Vosk/Whisper resident model in the default profile;
- no heavy agent framework;
- no dashboard WebView/Electron shell;
- no unnecessary provider SDKs loaded at startup;
- lazy-load optional adapters;
- bounded queues, bounded history, bounded audio ring buffer.

Do not claim the 300 MiB gate passes until it has been measured on the target machine under the defined stress scenario.

## Voice privacy invariant

Before wake detection:

`microphone -> local audio frames -> local wake model -> discard`

After wake detection:

`microphone -> bounded command recording -> configured STT -> command text`

Ambient audio before wake MUST NOT:
- be sent to STT;
- be sent to Nemotron;
- be written to disk;
- be retained beyond the tiny wake-word ring buffer.

## AI/tool invariant

Nemotron may propose a typed tool call. It may not bypass policy.

Correct:
`User -> intent -> Nemotron tool proposal -> schema validation -> policy -> approval if needed -> executor`

Wrong:
`User -> Nemotron -> os.system(model_text)`

## Browser invariant

Use a Firefox WebExtension plus Native Messaging bridge for V1, with two gates:

1. Project H dashboard allowlist says the domain/action is allowed.
2. Firefox extension has the corresponding host permission.

Both must pass.

## Terminal invariant

Preapproval is based on structured executable/argument rules, not substring matching.

Examples:
- safe rule: executable `git`, args prefix `["status"]`
- unsafe rule: `"command contains git"`

`sudo`, privilege escalation, destructive filesystem commands, package installation/removal, service changes and commands outside configured workspaces require explicit user approval unless a future higher-security rule says BLOCKED.

## Definition of done for every implementation task

A task is complete only when:
- code exists;
- unit/integration test exists where applicable;
- test was run;
- negative/security case was tested;
- memory-impact note was recorded for new resident dependencies;
- docs/config are updated if the behavior changed;
- no architecture invariant was violated;
- `TASKS.md` evidence is updated.

## Red flags

Stop and re-evaluate if implementation introduces:
- Electron;
- React/Vite for the dashboard;
- wildcard browser host permissions;
- `shell=True` for model-supplied data;
- permanent ambient audio recording;
- API call before wake in always-listen mode;
- arbitrary Python code inside action JSON;
- full-home-directory file access by default;
- multiple always-on Python services doing overlapping work;
- a local STT model whose runtime alone approaches the 300 MiB limit;
- an "agent framework" that spawns separate workers by default.
