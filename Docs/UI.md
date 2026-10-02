# Project H — Dashboard UI Specification V2

## 1. Design intent

Reference image: `reference/PERSONAL_AI_CANONICAL_DASHBOARD_REFERENCE_V1.png`

Use the reference for:
- dark glassy control-console feeling;
- cyan/blue accent system;
- left navigation;
- clear central assistant state;
- visible voice/listening status;
- bottom command composer;
- compact operational status cards.

Do **not** copy:
- the human face/avatar;
- photographic background;
- exact branding;
- decorative density that harms performance.

Replace the avatar area with an original, lightweight, abstract **AI Core** animation.

## 2. Frontend technology

Required:
- semantic HTML5;
- local Bootstrap 5.3 CSS;
- custom CSS;
- vanilla JavaScript modules;
- inline/local SVG icons;
- optional native `<dialog>`;
- no React;
- no Vue;
- no Angular;
- no Tailwind runtime;
- no jQuery;
- no Node/Vite dev/runtime requirement;
- no frontend server;
- no WebGL/Three.js.

FastAPI serves the static files from localhost.

Bootstrap JS bundle should be omitted unless a concrete component requires it. Prefer small native JS.

## 3. Performance budget

Dashboard assets, excluding fonts/icons already on system:
- HTML + custom JS + custom CSS target: < 250 KiB;
- Bootstrap CSS may be shipped locally;
- no background video;
- no large hero image;
- no remote font dependency;
- use system font stack;
- animation pauses when page hidden;
- no continuously repainting large canvas.

## 4. Visual system

### 4.1 Color tokens

```css
:root {
  --ph-bg-0: #030A12;
  --ph-bg-1: #06111D;
  --ph-bg-2: #0A1826;
  --ph-panel: rgba(7, 25, 40, 0.82);
  --ph-panel-strong: rgba(8, 30, 48, 0.94);

  --ph-cyan: #2CB8FF;
  --ph-cyan-bright: #79DDFF;
  --ph-blue: #2A6FFF;
  --ph-line: rgba(71, 190, 255, 0.28);
  --ph-line-strong: rgba(71, 190, 255, 0.56);

  --ph-text: #EAF7FF;
  --ph-text-2: #A9C5D8;
  --ph-text-3: #6F92AA;

  --ph-success: #2EE6A6;
  --ph-warning: #FFC85A;
  --ph-danger: #FF6178;
  --ph-info: #63C8FF;

  --ph-shadow: rgba(0, 148, 255, 0.18);
}
```

Do not make every edge glow. Use glow only for:
- active nav item;
- current listening/thinking state;
- primary send/mic control;
- AI Core focal object.

### 4.2 Typography

System stack:

```css
font-family:
  Inter, ui-sans-serif, system-ui, -apple-system,
  BlinkMacSystemFont, "Segoe UI", sans-serif;
```

Scale:
- page title: 28–32px / 600;
- section title: 18–20px / 600;
- card title: 14–16px / 600;
- body: 13–15px / 400;
- metadata: 11–12px / 400;
- monospace data: `ui-monospace`, 12–13px.

### 4.3 Radius and border

- large panels: 14px;
- cards: 10px;
- buttons: 8px;
- chips: 999px;
- border: 1px `--ph-line`;
- no giant 30px rounded "mobile SaaS" blobs.

### 4.4 Background

Instead of a photographic wallpaper:
- solid radial gradient;
- very faint 40px grid using two CSS linear-gradients;
- optional vignette;
- no image asset required.

Example feel:
`#030A12` → `#071729` with subtle blue center illumination.

## 5. AI Core animation

### Goal

Take the place of the avatar in the reference while costing almost nothing.

### Recommended implementation

One SVG:
- 3 concentric circles;
- 2 partial arc strokes;
- center dot/core;
- 12–24 small radial tick marks;
- optional 16-bar waveform under/around it.

CSS transforms/stroke dash animations only.

States:

**Idle**
- almost static;
- one ring rotates 30–45s per revolution;
- faint breathing opacity.

**Listening for wake**
- thin cyan outer ring;
- tiny amplitude response from local mic level only;
- text: `Listening for <wake name>`.

**Recording command**
- brighter cyan;
- waveform visibly reactive;
- solid mic indicator.

**Thinking**
- rotating arcs at different slow speeds;
- inner pulse;
- no frantic particle storm.

**Acting**
- blue/cyan directional sweep.

**Needs approval**
- core becomes amber;
- animation pauses except a slow pulse.

**Error**
- danger accent, no flashing.

**Speaking**
- bars respond to TTS output level if available.

Rules:
- `prefers-reduced-motion` disables rotations/pulse.
- `document.visibilityState !== "visible"` pauses JS/audio visualizer.
- no 60fps full-screen rendering.

## 6. Desktop shell

Target reference viewport: 1366x768 upward.

Layout:

```text
┌─────────────────────────────────────────────────────┐
│ Top Status Bar                                      │
├──────────┬──────────────────────────────────────────┤
│ Sidebar  │ Current screen                           │
│          │                                          │
│          │                                          │
├──────────┴──────────────────────────────────────────┤
│ optional command composer on Home/Chat              │
└─────────────────────────────────────────────────────┘
```

Sidebar width: 208–224px.

Collapsed mode at <= 1050px:
- icon-only 64px rail.

Mobile:
- sidebar becomes hidden drawer using lightweight vanilla JS.

## 7. Global top bar

Contains:
- Project H mark + configured assistant name;
- state chip;
- mic state;
- current AI provider/model short name;
- memory RSS/cap compact indicator;
- approval pending indicator;
- profile/menu.

No decorative system clock duplication; Ubuntu already has one.

## 8. Screen: Home

Purpose: at-a-glance assistant state and fastest actions.

### Left/center content

Header:
- `Good evening, <user>` optional;
- assistant status;
- short hint.

Four quick actions:
- Talk
- Chat
- Browser
- New Task

Recent activity:
- last 5–8 actions/tasks;
- icon + title + result + time;
- no expensive charts.

### AI Core panel

Central/right panel:
- AI Core SVG;
- current state;
- wake phrase;
- current step;
- compact indicators:
  - Voice
  - Browser bridge
  - Nemotron
  - Policy engine.

### Bottom composer

Always visible on Home:
- text box;
- mic button;
- send;
- stop/cancel while active;
- keyboard hint.

## 9. Screen: Chat

Components:
- conversation list left or compact dropdown;
- stream output center;
- provider/model pill;
- tool/action event cards inline;
- Stop;
- Regenerate/Retry;
- copy.

Tool event examples:
- `Reading: src/api.py`
- `Waiting for approval: pytest`
- `Browser: google.com`
- `Edited: 2 files`

Do not expose raw model reasoning.

## 10. Screen: Tasks / Agents

Use one screen, not separate heavy dashboards.

### Task list
Columns/cards:
- status;
- task;
- agent role;
- workspace;
- current step;
- API calls;
- duration;
- approval waiting.

Actions:
- start;
- pause;
- cancel;
- open evidence;
- inspect diff/log.

### Agent settings drawer
- name/role;
- objective;
- workspace;
- allowed tools;
- max steps;
- max API calls;
- timeout.

Default max active agents visibly set to `1`.

## 11. Screen: Browser

### Domain allowlist table

Columns:
- domain;
- enabled;
- adapter;
- Project H access;
- Firefox permission;
- capabilities;
- last used.

Edit modal/panel:
- URL pattern;
- open/read/click/type/submit/download/upload toggles;
- adapter;
- require approval for submit;
- test permission.

### Browser bridge status
- Firefox extension detected;
- native host detected;
- version;
- active tab domain;
- last command.

### Site adapter cards
- Google
- Amazon
- ChatGPT
- Gemini
- Claude
- Generic

Each shows: enabled / healthy / needs update.

## 12. Screen: Voice

### Assistant identity
- display name;
- wake phrase;
- wake model;
- retrain/import custom wake model.

### Listening
- Always Listen toggle;
- Push-to-talk hotkey;
- sensitivity slider;
- VAD;
- command max seconds;
- noise suppression if supported.

### STT
- provider;
- model;
- language;
- API key status only, never the key;
- test transcription.

### Privacy card
Must clearly state:
- pre-wake audio stays local;
- no STT/API before wake;
- audio retention disabled by default.

### TTS
- on/off;
- provider;
- voice;
- speed;
- test.

## 13. Screen: Actions

This is where deterministic no-AI automation is managed.

Tabs:
- Action Packs
- Command Phrases
- Dry Run
- Raw JSON

Action row:
- enabled;
- id;
- phrases;
- executor;
- approval mode;
- risk;
- edit;
- test.

Create action form:
- ID;
- phrase patterns;
- executor;
- typed arguments;
- timeout;
- approval;
- risk.

Raw JSON:
- code textarea;
- validate;
- format;
- save;
- error path/line.

No syntax-highlighting library in V1. Plain monospace textarea is enough.

## 14. Screen: Permissions

Three panels:

### Terminal
- preapproved rules;
- session approvals;
- always-ask categories;
- denied categories.

### Files
- allowed roots;
- per-root read/write/delete;
- hidden files;
- max size.

### Browser
- same domain policy shortcut.

Audit shortcut:
- view last approvals/denials.

## 15. Screen: Files / Workspaces

Purpose is permission/configuration, not a replacement file manager.

- allowed roots;
- recent assistant-touched files;
- repository cards;
- changed files;
- open in VS Code;
- show diff.

No recursive tree loaded for huge roots until user opens one.

## 16. Screen: Developer

### Repositories
- path;
- branch;
- dirty status;
- default test command;
- build/lint commands;
- allowed command rules.

### VS Code
- `code` CLI detected;
- open workspace;
- optional future bridge status.

### Coding agent defaults
- max steps;
- test-before-finish;
- require clean verification;
- auto-open diff;
- commit policy (`never` default).

## 17. Screen: Settings

Sections:

### General
- assistant name;
- language;
- start on login;
- notifications;
- theme density.

### AI
- provider/model;
- reasoning effort/budget;
- timeout;
- output token cap;
- key environment variable status.

### Voice
Shortcut to Voice screen.

### Browser
Shortcut to Browser screen.

### Actions & permissions
Shortcut.

### Privacy
- chat retention;
- audit retention;
- content logging off;
- audio retention off;
- clear history.

### Resource limits
- current RSS;
- MemoryHigh;
- MemoryMax;
- queue sizes;
- optional component memory notes.

### System
- service status;
- tray status;
- extension status;
- version;
- diagnostics export.

## 18. Native approval popup

Not rendered inside dashboard.

Visual:
- 420–520px compact native dialog;
- dark system-compatible background if practical;
- amber shield icon;
- action title;
- exact command/target in monospace;
- reason;
- workspace/domain/path;
- risk;
- expiry countdown.

Buttons:
- Deny (default focus for high risk);
- Allow once;
- Allow session (only eligible operations).

Never show an `Always allow` button in this surprise popup.

## 19. Tray menu UI

Menu:
- `<Assistant Name> — Ready`
- separator
- Push to Talk
- Always Listen ✓
- Voice Output ✓
- separator
- Open Dashboard
- Pause Assistant
- separator
- Quit

Tray icon states:
- neutral cyan = ready;
- cyan pulse/alternate icon = recording/listening;
- blue = thinking/acting;
- amber = approval;
- red = error.

Do not animate the actual tray icon continuously; panel animations are distracting and may cost more than they deserve.

## 20. Responsive behavior

- >= 1200px: full sidebar, two-column Home.
- 900–1199px: compact sidebar, AI Core smaller.
- 600–899px: one column, AI Core 140px, recent activity below.
- < 600px: drawer navigation, full-width cards, composer sticky.

## 21. Accessibility

- keyboard reachable;
- visible focus ring;
- minimum 4.5:1 text contrast where practical;
- state not encoded by color alone;
- motion reduction;
- button labels/tooltips;
- no tiny 9px critical text.

## 22. Dashboard settings inventory

The complete settings set is:

- assistant display name;
- wake phrase/model/sensitivity;
- always listen;
- push-to-talk hotkey;
- VAD/noise suppression;
- STT provider/model/language;
- TTS provider/voice;
- AI provider/model/reasoning/budgets/timeouts;
- browser domain allowlist/capabilities/adapters;
- file roots/permissions;
- terminal preapproval rules;
- deterministic action packs;
- agent limits/tools/budgets;
- repo/dev defaults;
- chat/audit retention;
- audio retention;
- logs;
- autostart/tray;
- resource/memory limits;
- diagnostics.

Anything not in this list needs a product reason before it becomes another settings toggle. Humans can create an infinite settings page if left unsupervised.
