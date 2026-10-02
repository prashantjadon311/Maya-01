# Project H — TDD Implementation Plan V2

**Target:** Gemini in Antigravity  
**Method:** incremental TDD, security boundaries first, memory measurement throughout.

## Phase 0 — Repository and measurement harness

1. Create Python package skeleton.
2. Add pytest + anyio.
3. Add `psutil` only to test/dev tooling if not needed at runtime.
4. Create memory measurement script/test.
5. Add config fixtures.
6. Add CI/local commands.
7. Add `.gitignore` for secrets/audio/temp.

Acceptance:
- empty daemon starts/stops;
- baseline RSS recorded;
- no dashboard/voice/provider yet.

## Phase 1 — Config and schemas

Implement:
- `config.toml` model;
- browser/file/agent settings;
- JSON action-pack schema;
- duplicate/unknown/invalid reference validation;
- atomic config writes.

Tests first:
- valid config;
- unknown field fails;
- invalid action executor fails;
- duplicate action id fails;
- invalid browser capability fails;
- invalid memory limits fail.

## Phase 2 — Policy engine

Implement pure policy code before executors.

Tests:
- deterministic ALLOW/ASK/DENY;
- high-risk action cannot silently preapprove;
- `sudo` always asks;
- file outside root denies;
- browser outside domain denies;
- action hash changes invalidate approval.

No shell/browser execution yet.

## Phase 3 — Deterministic action registry

Implement:
- action loading;
- phrase patterns;
- slots;
- exact confidence;
- composite action validation.

Tests:
- English/Hinglish phrase match;
- ambiguous phrase does not execute;
- disabled action ignored;
- malformed JSON keeps last valid pack.

## Phase 4 — Safe executors

### Process
- argv only;
- no shell;
- cwd root enforcement;
- timeout;
- bounded output;
- controlled env.

### File
- canonicalization;
- root containment;
- read/write;
- atomic write;
- delete behind stronger policy.

### xdg/app
- open URL/file/app with typed arguments.

Security tests before integration.

## Phase 5 — Approval popup

Implement `ApprovalBroker` and native/transient UI.

Tests:
- timeout denies;
- stale token denies;
- wrong hash denies;
- allow once consumed once;
- daemon restart clears pending.

Integration test with fake popup first. Real popup manual test second.

## Phase 6 — NVIDIA Nemotron provider

Implement one reusable async client:
- custom base URL;
- model config;
- streaming;
- tool calls;
- `max_retries=0`;
- timeout;
- error normalization;
- reasoning controls;
- content only returned to user.

Use fake HTTP provider in tests.

Do not hit paid/live API in default test suite.

## Phase 7 — Command router + agent runtime

Router order:
1. action registry;
2. built-ins;
3. AI.

Agent runtime:
- one logical active task;
- bounded steps/API calls;
- tool proposal -> policy -> executor;
- verification step.

Tests:
- exact local action causes zero AI calls;
- ambiguous command may call AI;
- model cannot bypass policy;
- agent step/budget caps enforced.

## Phase 8 — Voice wake pipeline

Implement:
- audio source abstraction;
- fake source;
- wake detector abstraction;
- openWakeWord implementation;
- command recorder;
- VAD/end-of-command.

Critical tests:
- no network callback before wake;
- no STT before wake;
- ring buffer bounded;
- command segment starts after wake window;
- disabling listen closes stream.

Memory test after real wake engine is added.

## Phase 9 — STT adapter

Implement NVIDIA hosted multilingual ASR adapter after verifying current API details.

Tests with fake adapter:
- wake -> record -> STT;
- STT failure -> no execution;
- transcript normalized;
- audio buffer released.

Manual live test:
- English;
- Hindi;
- Hinglish sample set.

## Phase 10 — Tray/StatusNotifierItem

Implement D-Bus item:
- state;
- push-to-talk;
- always listen toggle;
- open dashboard;
- pause/quit.

Manual Ubuntu test required because tray hosts differ.

Measure RSS delta.

## Phase 11 — Firefox extension + native bridge

First build protocol tests.

Then:
- Native Messaging host;
- extension background;
- optional host permissions;
- content-script registration;
- generic adapter.

Security tests:
- wrong origin denied;
- unlisted domain denied by daemon;
- ungranted host permission fails;
- password field not readable/typeable by generic adapter.

## Phase 12 — Site adapters

In order:
1. Google Search
2. Amazon search
3. ChatGPT
4. Gemini
5. Claude
6. Google AI result/mode if current UI can be reliably targeted.

Each adapter gets:
- fixture DOM tests when feasible;
- current live smoke test;
- graceful "adapter outdated" failure.

## Phase 13 — Dashboard backend

FastAPI:
- localhost only;
- static files;
- same-origin API;
- state/event stream;
- config CRUD;
- action CRUD;
- audit pagination;
- agent controls.

No wildcard CORS.

## Phase 14 — Dashboard frontend

Implement `UI.md` with:
- Bootstrap CSS local;
- custom CSS;
- vanilla JS;
- SVG AI Core;
- no large assets;
- no framework.

Screen order:
1. shell/Home
2. Voice
3. Browser
4. Actions/Permissions
5. Chat
6. Tasks/Agents
7. Files/Developer
8. Settings

Run browser performance sanity check.

## Phase 15 — Developer workflows

Implement:
- repo registration;
- git status/diff;
- code CLI open;
- test command execution under policy;
- edit/test/verify task flow.

Never auto-commit by default.

## Phase 16 — Resource hardening

Stress scenario:
- daemon running;
- always listen on;
- dashboard open;
- one browser bridge connected;
- one streaming Nemotron request;
- one logical coding agent;
- audit writes occurring.

Record:
- idle RSS;
- wake-listen RSS;
- dashboard active RSS;
- peak RSS;
- CPU.

Acceptance:
- Project H cgroup peak <= 300 MiB.
- systemd MemoryMax remains 300M.
- no component killed during normal scenario.

If failing:
- measure first;
- remove/replace biggest resident dependency;
- do not increase cap.

## Phase 17 — Packaging

- user systemd unit;
- config install;
- Firefox native manifest;
- extension packaging;
- desktop/tray icon;
- first-run setup;
- uninstall procedure.

## Phase 18 — Final acceptance

Run:
- full unit suite;
- integration suite;
- permission red-team;
- browser allowlist tests;
- voice privacy test;
- memory stress test;
- clean install on target Ubuntu;
- restart/login autostart;
- offline deterministic actions while NVIDIA unavailable.

Only after this may V1 be called complete.
