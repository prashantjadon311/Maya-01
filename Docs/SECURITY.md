# Project H — Security, Permission and Privacy Contract

## 1. Core rule

**No capability is granted merely because the user asked the AI to be powerful. Capability is explicit, scoped and revocable.**

## 2. Permission decision

Every action resolves to exactly one:

- `ALLOW_PREAPPROVED`
- `ASK_USER`
- `DENY`

No implicit fourth state.

## 3. Risk model

### Low
- open configured app;
- read allowed file;
- list allowed directory;
- open allowlisted URL;
- read allowlisted webpage;
- git status/diff.

### Medium
- edit an allowed file;
- type/submit into ordinary allowlisted webpage;
- run test/build command;
- rename/move allowed file;
- create task/agent.

### High
- delete file;
- package install/remove;
- service control;
- privileged command;
- sending external messages;
- upload;
- account changes;
- financial/cart/checkout actions.

High risk is never silently pre-approved in V1.

## 4. Terminal safety

Requirements:
- `asyncio.create_subprocess_exec` / argv execution;
- `shell=False`;
- controlled env;
- timeout;
- working-directory allowlist;
- bounded stdout/stderr capture;
- terminate/kill escalation;
- no inherited stdin by default;
- no model-chosen redirection/pipes unless a separately approved shell executor is introduced.

Preapproval must match structured executable+arguments.

## 5. Native approval popup

The popup is outside the dashboard so approval still works with dashboard closed.

Fail closed:
- no popup backend -> deny;
- timeout -> deny;
- daemon restarts -> pending approvals invalid;
- hash mismatch -> deny.

Default buttons:
- Allow once
- Deny

Optional:
- Allow for session for low/medium eligible rule.

Do not provide "always allow" directly from a surprise popup. Permanent preapproval belongs in dashboard settings where the user can inspect scope.

## 6. Browser policy

Two independent permissions:
1. application allowlist;
2. browser host permission.

Per-domain capability policy:
- `open`
- `read`
- `click`
- `type`
- `submit`
- `download`
- `upload`

Default:
- open/read may be enabled by user;
- submit/type separate;
- upload/download separate.

The extension must re-check `location.origin` before executing a command received for a tab.

## 7. Browser secrets

Do not:
- read password fields;
- read browser password manager;
- scrape cookies;
- export session tokens;
- log auth headers;
- send DOM snapshots containing hidden secrets to Nemotron by default.

When page understanding is needed, extract the smallest visible relevant text.

## 8. File policy

Every file request:
1. expand user path;
2. normalize;
3. resolve symlinks/realpath;
4. ensure path is within allowed root;
5. check operation permission;
6. enforce file-size/type policy;
7. execute.

Delete is independent from write.

Sensitive defaults denied:
- `~/.ssh`
- `~/.gnupg`
- browser profiles
- keyrings
- `/etc`
- `/root`
- `/proc`
- `/sys`
- `/dev`
- credential files unless explicitly added.

## 9. Voice privacy

Pre-wake:
- local only;
- memory-only;
- no transcript;
- no file;
- no network.

Post-wake:
- only command segment may leave the device for STT;
- visible mic/listening state;
- audio discarded after STT by default.

## 10. AI data minimization

Nemotron receives:
- user request;
- minimum conversation context;
- allowed tool schemas;
- only file/page snippets needed for task;
- no API keys;
- no hidden browser credentials;
- no raw ambient audio.

## 11. Audit

Record metadata:
- timestamp;
- request id;
- actor/agent;
- tool;
- policy decision;
- approval result;
- target domain/path/executable;
- exit/result code;
- duration.

Do not log full sensitive content by default.

## 12. Agent containment

Agents inherit a subset of user-granted capabilities.

An agent cannot:
- grant itself a new root/domain;
- modify policy;
- approve its own action;
- change its own API budget;
- spawn unlimited peer agents.

## 13. Default deny for ambiguity

If a command can plausibly target multiple dangerous things, ask rather than guess.

## 14. Update trust

Future plugin/action packages need:
- explicit user install;
- version;
- declared capabilities;
- hash/signature strategy before third-party distribution.

Never allow action packs to be remote code.
