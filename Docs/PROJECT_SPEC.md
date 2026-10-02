# Project H — Consolidated V2 Specification

## Product objective

Build a resident Ubuntu personal assistant that feels immediately available like a system utility, not like a website that happens to contain a chatbot.

The assistant must combine:
- local wake/name detection;
- deterministic local actions;
- strict permission controls;
- browser integration;
- file/terminal/developer tools;
- remote intelligence only when necessary.

## Success criteria

A V1 acceptance demo should prove all of the following:

1. Log into Ubuntu and see Project H panel icon.
2. Dashboard remains closed.
3. Enable Always Listen from tray.
4. Speak unrelated conversation: no STT/API request occurs.
5. Say the configured wake name and command: command is transcribed and handled.
6. Say "VS Code kholo": configured local action opens VS Code without Nemotron.
7. Say "Google par Python 3.14 changes search karo": Firefox opens/searches because Google is allowed.
8. Ask for a disallowed domain: assistant refuses/asks user to add permission.
9. Ask "Amazon par iPhone cover search karo": it may search/read products, but not purchase.
10. Ask to run a non-preapproved terminal command: native approval popup appears even if dashboard is closed.
11. Deny popup: command does not run.
12. Preapprove a test command in dashboard: eligible future execution runs without popup inside allowed repo.
13. Ask coding task: agent edits allowed repository, runs permitted tests, shows diff/evidence.
14. Attempt file escape via symlink/`..`: denied.
15. Attempt model-generated raw shell injection: denied.
16. Run stress scenario with wake + dashboard + browser bridge + streaming AI: Project H cgroup stays <= 300 MiB.
17. Disconnect NVIDIA: deterministic actions still work.

## Primary architectural choices

- Python asyncio daemon.
- FastAPI same-process localhost control API.
- static Bootstrap/HTML/CSS/JS dashboard.
- openWakeWord local wake model.
- remote STT after wake.
- NVIDIA Nemotron 3 Ultra for reasoning/tools.
- Firefox WebExtension + Native Messaging.
- freedesktop StatusNotifierItem for tray.
- SQLite for local metadata.
- versioned JSON action packs.
- native transient approval popup.
- user systemd service with hard memory cap.

## Important product distinction

The assistant has three levels of intelligence:

### Level 0: direct deterministic
No AI call.
Examples: open app, open URL, Google search, run explicitly mapped action.

### Level 1: local parsing/policy
No generative AI.
Examples: fill action slots, validate domain/path/command, permission decision.

### Level 2: remote reasoning
Nemotron.
Examples: coding, planning, ambiguous request, multi-step task, tool choice.

The router always attempts the cheapest safe level first.

## V1 scope boundaries

The project is ambitious. V1 must not become "control every pixel on the desktop". Use explicit integrations:
- file APIs;
- process APIs;
- browser extension;
- `code` CLI;
- D-Bus/XDG.

Desktop vision/mouse automation can be a later subsystem after the permission model is mature.
