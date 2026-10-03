# Maya Resource Budget & Memory Enforcement Specifications

Project H operates under strict Linux cgroup memory constraints configured via systemd user services:
- **`MemoryHigh`:** `240M` (`FROZEN_LIMIT`)
- **`MemoryMax`:** `300M` (`FROZEN_LIMIT`)

Under no circumstances may `MemoryMax` be silently raised. Every internal queue, buffer, cache, and history list must enforce a hard upper bound.

---

## 1. System Memory Budget Table

| Subsystem / Component | Budget Label | Target RAM | Lifetime Status | Enforcement Mechanism | Behavior on Limit |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Python Daemon Core** (asyncio loop, config, dispatcher, policy) | `ESTIMATED_BUDGET` | 55 MiB | `RESIDENT` | Compact data structures | Garbage collection |
| **Voice & Wake Pipeline** (openWakeWord, audio capture, VAD) | `ESTIMATED_BUDGET` | 100 MiB | `RESIDENT` | Single CPU thread, 3s ring | Drop oldest audio frames |
| **Dashboard Backend** (FastAPI, Starlette, Uvicorn) | `ESTIMATED_BUDGET` | 30 MiB | `RESIDENT` | Max 50 SSE events | Drop oldest events |
| **System Tray** (StatusNotifierItem, D-Bus connection) | `ESTIMATED_BUDGET` | 10 MiB | `RESIDENT` | D-Bus event rate limiter | Rate limit updates (10/s) |
| **Browser Bridge & Native Pipes** | `ESTIMATED_BUDGET` | 20 MiB | `EPHEMERAL` | 1MB max message framing | Reject oversized messages |
| **Safety Margin** | `ESTIMATED_BUDGET` | 85 MiB | `HEADROOM` | Kernel cgroup ceiling | Throttles at 240M, OOM kill at 300M |
| **Total Resident Daemon Cap** | **`FROZEN_LIMIT`** | **300 MiB** | `RESIDENT` | systemd `MemoryMax=300M` | Service restart on failure |

*External processes (Firefox, VS Code, and user-approved subprocesses) run in separate cgroups and are accounted for independently.*

---

## 2. In-Memory Data Structure Bounds

| Data Structure | Hard Maximum Bound | Enforcement Location | Behavior at Limit |
| :--- | :--- | :--- | :--- |
| **Audio Ring Buffer** | 96,000 bytes (3.0 seconds PCM) | `app/voice/audio.py` | Drop oldest 1280-byte frame |
| **Command Audio Buffer** | 320,000 bytes (10.0 seconds PCM) | `app/voice/recorder.py` | Terminate recording, proceed to STT |
| **Subprocess Output Buffer** | 65,536 bytes (64 KB) | `app/executors/process.py` | Truncate output, append warning flag |
| **Model Context Window** | 32 messages (~128 KB text) | `app/ai/nvidia.py` | Slide window, prune oldest user turns |
| **Agent Step Limit** | 15 execution steps | `app/agents/runtime.py` | Terminate task loop, return partial evidence |
| **Agent API Call Budget** | 20 external API calls | `app/agents/runtime.py` | Fail closed with `AgentBudgetExceeded` |
| **Agent Transcript Buffer** | 65,536 bytes (64 KB) | `app/agents/runtime.py` | Summarize intermediate steps |
| **Pending Approval Grants** | 10 concurrent requests | `app/policy/broker.py` | Reject oldest unhandled request |
| **Action Pack Cache** | 50 packs, 500 actions, 2000 phrases | `app/actions/registry.py` | Reject new pack with `PackLimitExceeded` |
| **DOM Extraction Payload** | 100,000 characters (~100 KB) | `extension/firefox/generic.js` | Truncate extracted text |
| **SSE Event Queue** | 50 queued events | `app/api/app.py` | Drop oldest non-critical state event |
| **SQLite Audit Retention** | 10,000 events / 30 days | `app/storage/sqlite.py` | Purge rows exceeding retention window |
