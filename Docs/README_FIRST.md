# Project H — Personal AI Assistant V2
**Status:** Architecture/requirements handoff for Gemini in Antigravity  
**Primary runtime AI:** NVIDIA Nemotron 3 Ultra hosted API  
**Target OS for V1:** Ubuntu/Linux  
**Hard resident-memory acceptance limit:** 300 MiB for Project H resident processes

## Purpose

Project H is not just an AI chat dashboard. It is a lightweight, permission-controlled personal computer assistant that can:

- accept text and voice commands;
- wake on a customizable assistant name without sending ambient speech to any third party;
- live in the Ubuntu top panel/system tray while the dashboard is closed;
- control only explicitly allowed browser domains;
- execute pre-approved local actions without an AI call when deterministic logic is enough;
- request an out-of-dashboard native approval popup before terminal or other sensitive actions;
- read/write files only inside configured roots;
- use browser-based ChatGPT, Gemini and Claude through site adapters when the user permits those domains;
- use Google Search and normal websites without requiring an LLM for obvious deterministic actions;
- operate as a developer assistant: work with repositories, files, tests, terminals and VS Code under permission policy;
- create logical agents/tasks while keeping them inside the same lightweight runtime rather than spawning a heavy framework per agent.

## Non-negotiable constraints

1. The assistant must work when the dashboard is closed.
2. Always-listening mode performs only local wake-word detection before activation.
3. No ambient audio is transcribed or uploaded before the wake phrase is detected.
4. Browser access is deny-by-default and domain allowlisted.
5. Shell/terminal execution is deny-by-default unless the exact action is pre-approved or the user approves a native popup.
6. `sudo`/privileged commands always require explicit approval.
7. No arbitrary model-supplied shell string may be executed directly.
8. File access is root-allowlisted with separate read/write/delete permissions.
9. The dashboard is static HTML + CSS + Bootstrap CSS + small vanilla JS. No React, Vue, Angular, Vite, npm runtime, Electron, WebView shell or separate frontend server.
10. The reference UI is inspiration only. Do not copy the human/avatar artwork. Replace it with an original lightweight geometric "AI core" animation.
11. Project H's resident processes must stay under 300 MiB RSS/cgroup memory in the target acceptance test. Browser, VS Code and commands launched by the user are external applications and are measured separately.
12. The 300 MiB target is an engineering acceptance gate, not an assumption. Memory must be measured on the target laptop and enforced by systemd resource controls.
13. Avoid LangChain, CrewAI, AutoGen, LangGraph, Redis, Celery, Electron and other heavy infrastructure unless a measured requirement later proves they are necessary.

## Recommended V1 architecture in one line

`Local daemon + local wake word + remote STT after wake + policy engine + deterministic action registry + NVIDIA Nemotron tool-calling + Firefox WebExtension/native bridge + static localhost dashboard`

## Read order for Gemini

1. `SKILL.md`
2. `DOCS.md`
3. `ARCHITECTURE.md`
4. `SECURITY.md`
5. `CONFIG.md`
6. `UI.md`
7. `PLAN.md`
8. `TASKS.md`
9. `EXECUTION.md`
10. `REFERENCES.md`

The files above are the authority. Do not redesign them casually because a library happens to offer a shinier abstraction.
