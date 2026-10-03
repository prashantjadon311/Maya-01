# Maya Final PH-180 System Architecture

## 1. End-State Architectural Overview

Project H (Maya) is a personal local-first computer assistant for Ubuntu Linux that pairs deterministic local automation with remote reasoning models strictly when reasoning is required.

```mermaid
flowchart TD
    subgraph Inputs ["Inputs & Surfaces"]
        MIC["Microphone Audio"]
        TEXT["Text Command (CLI / Web)"]
        TRAY["StatusNotifierItem Tray (D-Bus)"]
        DASH["Local Web Dashboard (127.0.0.1)"]
    end

    subgraph VoiceSubsystem ["Voice Pipeline (Local + Remote STT)"]
        AS["AudioSource (Ring Buffer)"]
        WD["WakeDetector (openWakeWord)"]
        CR_REC["CommandRecorder (VAD)"]
        STT["STTAdapter (NVIDIA Multilingual)"]
    end

    subgraph CoreDaemon ["Resident Daemon (project-hd)"]
        STATE["AppState (State Machine)"]
        GW["InputGateway"]
        ROUTER["CommandRouter"]
        REG["ActionRegistry"]
        AI["NvidiaProvider (AsyncOpenAI)"]
        AGENT["AgentRuntime (Bounded Task Loop)"]
        POLICY["PolicyEngine (ALLOW / ASK / DENY)"]
        BROKER["ApprovalBroker"]
        DISPATCH["ActionDispatcher (Central Boundary)"]
        STORAGE["SQLiteStorage (Audit / Preferences)"]
        API["FastAPI Local Server (127.0.0.1)"]
    end

    subgraph Executors ["Safe Action Executors"]
        P_EXEC["ProcessExecutor (argv only, 64KB bound)"]
        F_EXEC["FileExecutor (Canonicalized, root bound)"]
        X_EXEC["XdgExecutor (xdg-open allowlist)"]
        D_EXEC["DeveloperToolExecutor (git, test, code)"]
        B_BRIDGE["NativeMessageBridge (Firefox)"]
    end

    subgraph ExternalSurfaces ["External Processes & Surfaces"]
        POPUP["Native Approval Popup (Transient GTK/Zenity)"]
        FX["Firefox WebExtension + Site Adapters"]
        SUBP["User Approved Subprocesses"]
    end

    MIC --> AS
    AS --> WD
    WD -->|Wake detected| CR_REC
    CR_REC -->|Command segment| STT
    STT --> GW
    TEXT --> GW
    TRAY --> GW
    DASH --> API

    API --> DISPATCH
    API --> STORAGE
    GW --> ROUTER

    ROUTER -->|1. Exact match| REG
    ROUTER -->|2. Built-in| DISPATCH
    ROUTER -->|3. AI reasoning| AI
    ROUTER -->|4. Agent task| AGENT

    AGENT --> AI
    AGENT --> DISPATCH
    REG --> DISPATCH

    DISPATCH --> POLICY
    POLICY -->|ALLOW_PREAPPROVED| EXECUTORS_GATE[Execute]
    POLICY -->|ASK_USER| BROKER
    BROKER --> POPUP
    POPUP -->|User grant + hash| BROKER
    BROKER -->|Single-use grant validated| EXECUTORS_GATE

    EXECUTORS_GATE --> P_EXEC
    EXECUTORS_GATE --> F_EXEC
    EXECUTORS_GATE --> X_EXEC
    EXECUTORS_GATE --> D_EXEC
    EXECUTORS_GATE --> B_BRIDGE

    P_EXEC --> SUBP
    B_BRIDGE <--> FX
    DISPATCH --> STORAGE
    STATE <--> TRAY
```

---

## 2. Process Architecture

### 2.1 Resident Daemon (`project-hd`)
A single, long-running resident Python process running under systemd user mode:
- Memory target: `MemoryHigh=240M`, `MemoryMax=300M`.
- Event loop: standard `asyncio`.
- Components hosted: Core state machine, input gateway, command router, action registry, policy engine, approval broker, action dispatcher, executors, FastAPI server (127.0.0.1), SQLite audit/config storage, D-Bus StatusNotifierItem client, and wake audio monitoring.

### 2.2 Transient Subprocesses
- **Native Approval Popup:** Spawned on demand when an action resolves to `ASK_USER`. Terminates immediately after user response or timeout.
- **User Commands:** Sandboxed processes spawned via `ProcessExecutor` with argv-only isolation.
- **Native Messaging Host:** Launched by Firefox via standard WebExtension native messaging stdin/stdout framing.
- **Web Browser Tab:** Optional user dashboard viewed in default browser on `http://127.0.0.1:8765`.
