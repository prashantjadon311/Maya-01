# Project H — Product Requirements and Functional Contract V2

## 1. Product statement

Project H is a local-first personal computer assistant for Ubuntu. It combines deterministic local automation with a remote reasoning model only when reasoning is actually needed.

The product has four user surfaces:

1. **Voice** — push-to-talk or wake-name activation, available while the dashboard is closed.
2. **Tray/panel menu** — always available in the Ubuntu top panel.
3. **Dashboard** — configuration, chat, tasks, permissions, activity and diagnostics.
4. **Native approval popup** — independent from the dashboard and shown for sensitive actions.

## 2. Primary runtime AI

Initial provider:

- Provider: NVIDIA
- Base URL: `https://integrate.api.nvidia.com/v1`
- Model: `nvidia/nemotron-3-ultra-550b-a55b`
- Protocol: OpenAI-compatible Chat Completions
- Secret: `NVIDIA_API_KEY`
- Streaming: enabled
- Tool/function calling: enabled
- SDK automatic retries: disabled; Project H owns retry policy.
- Reasoning output is internal metadata. Do not expose or persist raw reasoning traces by default.
- For coding-agent/tool workflows, support NVIDIA's `force_nonempty_content` chat-template behavior as an adapter option.

Future providers must implement the same internal provider interface.

## 3. Voice behavior

### 3.1 Push-to-talk

From the tray or dashboard:
- user presses/toggles microphone;
- command recording starts;
- recording stops by VAD silence, explicit stop or configured duration;
- audio is transcribed;
- command router handles it;
- optional TTS speaks the result.

Push-to-talk does not require the wake phrase.

### 3.2 Always-listening mode

When enabled:
- microphone is continuously sampled locally;
- only the local wake detector receives pre-wake audio;
- wake phrase is customizable and is normally the assistant's configured name;
- before wake, do not run cloud STT or call Nemotron;
- after wake, capture only the command segment;
- command audio may then be sent to configured STT;
- command audio is deleted from memory after transcription unless the user explicitly enables diagnostics;
- return to wake-only state after command completion.

### 3.3 Wake word

The wake phrase is configurable, e.g. `"Maya"` or `"Hey Maya"`.

Recommended engine:
- openWakeWord with one custom small model;
- TFLite/LiteRT backend on Linux when supported;
- one CPU thread;
- optional local VAD/noise suppression only if memory profiling permits.

Training a new name is an offline setup operation, not resident runtime work.

### 3.4 Speech-to-text

Default V1 strategy: remote STT **after wake only**.

Recommended initial hosted STT:
- NVIDIA Parakeet multilingual ASR where available;
- Hindi (`hi-IN`) is supported by NVIDIA's multilingual model;
- English is supported;
- Hinglish should be treated as a product test case rather than assumed perfect. The transcript may be normalized by the command parser/Nemotron after STT.

Do not use Vosk as the default resident STT: its own documentation says small models can require around 300 MB at runtime, which consumes the entire Project H budget.

### 3.5 Text-to-speech

TTS is optional and independently toggleable:
- default off in V1 unless a small solution is chosen;
- remote TTS is allowed only after a user command;
- no TTS library should be resident if it materially threatens the memory budget.

## 4. Tray/panel behavior

Project H runs as a user-level background service.

Ubuntu top-panel item should provide:

- status icon;
- current state: Ready / Listening for Wake / Recording / Thinking / Acting / Needs Approval / Error;
- **Push to Talk** action;
- **Always Listen** on/off;
- **Voice Output** on/off;
- **Open Dashboard**;
- **Pause Assistant**;
- **Quit/Stop Service**.

Preferred technical direction: expose a freedesktop StatusNotifierItem over the user session D-Bus rather than maintaining a heavyweight resident GUI window.

## 5. Command router

Every command is classified in this order:

1. **Exact/local action match**  
   Resolve against enabled action packs. No AI call if confidence/rule is exact.

2. **Built-in deterministic capability**  
   Examples: open configured app, open URL, Google search, show file, list directory, open project.

3. **Structured parser**  
   Parse low-ambiguity commands with local patterns.

4. **Nemotron reasoning/tool selection**  
   Used for ambiguous, multi-step, conversational, planning, coding or research tasks.

The user can configure which deterministic actions are available and which require approval.

## 6. Action registry

Use versioned JSON action packs, not one giant unvalidated free-form JSON file.

Directory example:

```text
~/.config/project-h/
  actions.d/
    core.json
    developer.json
    personal.json
    browser.json
```

Why JSON remains the recommended format:
- Python stdlib parser;
- no executable semantics;
- strict and easy to validate;
- safe to edit from the dashboard;
- diff-friendly;
- multiple packs avoid one enormous file;
- schema versioning is straightforward.

Do not let JSON contain arbitrary Python or shell scripts. It references typed executors.

Supported executor types in V1:
- `process`
- `xdg_open`
- `browser`
- `file`
- `composite`

Future:
- `dbus`
- `vscode`
- signed local plugins.

## 7. Browser control

### 7.1 Browser architecture

V1 target: Firefox WebExtension + Native Messaging bridge.

Capabilities:
- open URL/tab;
- close/focus tab;
- search Google;
- read visible/accessible page text;
- find text;
- click an allowed element;
- fill an allowed field;
- submit;
- scroll;
- wait for content;
- extract assistant response from supported AI sites.

### 7.2 Domain allowlist

Deny by default.

Dashboard configuration stores domains, e.g.:
- `google.com`
- `amazon.in`
- `chatgpt.com`
- `gemini.google.com`
- `claude.ai`

Each domain has granular capabilities:
- open
- read
- click
- type
- submit
- download
- upload
- clipboard

Adding a domain in Project H does not magically grant browser extension permission. The extension must also receive Firefox host permission.

### 7.3 Site adapters

Dedicated adapters for:
- Google Search;
- Google AI results/mode where the visible authenticated UI permits it;
- Amazon search;
- ChatGPT;
- Gemini;
- Claude.

Adapters should rely on resilient semantic/accessibility cues when possible, not brittle absolute CSS paths.

A generic adapter handles simple pages.

UI changes on third-party websites are expected to break adapters occasionally. Treat adapter maintenance as normal, not as a reason to give the model unrestricted arbitrary browsing.

### 7.4 Sensitive browser actions

Never automatically:
- submit a payment;
- place an order;
- send a message/email as the user;
- change account security settings;
- accept legal terms;
- bypass CAPTCHA/MFA.

These require explicit policy and typically user confirmation/takeover.

Example "Amazon par phone cover dhoondo":
- allowed: open Amazon, search, read result titles/prices;
- not automatically allowed: add to cart or buy unless separately approved.

## 8. Files

Dashboard defines allowed roots. Example:

```text
~/Projects
~/Documents/ProjectHShared
~/Downloads
```

Permissions are independent:
- read;
- create;
- edit;
- rename/move;
- delete.

Requirements:
- resolve real path before policy check;
- prevent `..` and symlink escape;
- protect hidden/system paths by default;
- atomic file write where practical;
- size limit;
- binary-file policy;
- deletion requires stronger policy than read/write;
- source repositories should expose diff before/after edits.

## 9. Terminal / Linux commands

### 9.1 Default behavior

A command is not executed merely because an LLM generated it.

Flow:
`proposal -> schema -> policy -> approval/preapproval -> execution -> bounded output -> audit`

### 9.2 Approval popup

Approval UI is not part of the dashboard.

Popup shows:
- command/executable;
- arguments;
- working directory;
- reason;
- risk level;
- proposed agent/task;
- timeout;
- buttons: `Allow once`, `Deny`;
- optional `Allow for this session` only for eligible low/medium-risk commands.

The approval token is tied to an immutable action hash and expires quickly.

### 9.3 Pre-approved commands

Configured in dashboard.

Preapproval rules are structured:
- executable;
- allowed argv prefixes/patterns;
- allowed working roots;
- timeout;
- environment allowlist;
- risk;
- whether network is allowed.

Examples that may be pre-approved:
- `pwd`
- `ls` within allowed roots
- `git status`
- `git diff`
- `pytest` inside selected repos
- `python -m pytest` inside selected repos

Do not preapprove by arbitrary substring.

### 9.4 Always-approval examples

- `sudo`
- package install/remove
- service modification
- chmod/chown on broad paths
- network/firewall changes
- destructive filesystem operations
- commands outside configured roots
- secret/credential operations

## 10. Developer assistant / VS Code

V1 should be a competent coding assistant without pretending UI clicking is the best engineering interface.

Preferred capabilities:
- read repository;
- search files;
- modify files;
- create files;
- run tests/linters/build commands under policy;
- inspect git diff/status;
- open workspace/file in VS Code via `code` CLI;
- open terminal at repo;
- use browser adapters for docs/ChatGPT/Gemini/Claude;
- create logical task agents;
- plan → edit → test → inspect → retry loops;
- produce evidence.

Future VS Code bridge:
- optional tiny VS Code extension;
- selected text/editor context;
- execute approved editor commands;
- diagnostics/problems;
- diff preview.
This is future because it adds another integration surface and is not required for useful V1 coding.

## 11. Agents

Agent = task state, not a heavyweight process.

Each agent stores:
- id;
- name/role;
- objective;
- workspace;
- allowed tools;
- approval policy;
- step count;
- API-call budget;
- status;
- artifacts/evidence.

Default:
- one active agent at a time;
- bounded steps;
- bounded transcript;
- same provider client;
- same tool/policy engine;
- no separate worker process unless an external command itself is being run.

## 12. Dashboard

Dashboard is configuration/control, not the assistant's only operating surface.

Implementation:
- HTML;
- CSS;
- Bootstrap 5.3 CSS stored locally;
- vanilla JavaScript;
- native browser APIs;
- no Node frontend runtime;
- no React/Vue/Angular;
- no frontend build server.

FastAPI may serve static assets from the local backend on `127.0.0.1`. That is not a separate frontend server.

See `UI.md`.

## 13. History and memory

V1 categories:
- chat history;
- task history;
- action audit;
- user preferences;
- optional short assistant notes.

Do not call this "self-learning". No hidden model retraining.

Storage:
- SQLite is acceptable for structured local state and audit metadata;
- secrets are not stored in SQLite;
- content retention is configurable;
- audio retention default: none;
- ambient/pre-wake audio retention: forbidden.

## 14. Resource budget

Hard target:
- resident Project H cgroup <= 300 MiB.

Recommended operational budget:

| Component | Design budget |
|---|---:|
| Python daemon/core + config + HTTP client | 55 MiB |
| wake/audio runtime | 100 MiB |
| local dashboard server when active | 30 MiB |
| tray/D-Bus integration | 10 MiB |
| browser native bridge + queues | 20 MiB |
| safety margin | 85 MiB |
| **Total cap** | **300 MiB** |

These are engineering budgets, not measured claims.

External processes such as Firefox, VS Code and user-approved command processes must be reported separately.

Systemd acceptance controls:
- `MemoryHigh=240M`
- `MemoryMax=300M`

If `MemoryMax` is crossed, the failure is real and must be fixed; do not raise the limit silently.

## 15. V1 non-goals

- local LLM;
- autonomous purchase/payment;
- mobile app;
- Windows/macOS parity;
- arbitrary unrestricted web automation;
- background keylogging/screen recording;
- self-modifying security policy;
- model-controlled `sudo`;
- unbounded multi-agent swarm;
- computer-vision desktop automation as primary interface;
- RAG/vector DB by default;
- cloud account/multi-user server.
