# Maya Failure Mode Matrix & Disaster Recovery Specifications

Maya designs for failure across every integration boundary. The system must fail safely, cleanly release all acquired resources, log a structured audit event, and preserve deterministic operation.

---

## 1. Subsystem Failure Matrix

| Failure Scenario | Detection Mechanism | Immediate State Transition | Cleanup & Resource Recovery | User Feedback | Recovery / Fallback Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Daemon Crash / Reboot with Approvals Pending** | Startup sequence checks memory state | Starts fresh in `READY_WAKE` | Grant memory was RAM-only; zero lingering grants | None needed | Any unexecuted action remains aborted |
| **NVIDIA AI Provider Unavailable** | `httpx.ConnectError` or HTTP 503 | `ERROR` (transient) ➔ `READY_WAKE` | Cancel active streaming task, close client session | "AI reasoning is temporarily offline" | Deterministic actions continue working 100% locally |
| **STT Network Timeout** | `asyncio.TimeoutError` (>10.0s) | `TRANSCRIBING` ➔ `ERROR` ➔ `READY_WAKE` | Drop PCM audio buffer from RAM immediately | "Could not transcribe audio command" | Discard command; zero downstream action execution |
| **Firefox Extension Disconnects** | EOF on native messaging stdin/stdout | Browser status set to `DISCONNECTED` | Close pipe stream, clear pending browser commands | "Browser extension disconnected" | Re-attempt connection on next browser command |
| **Microphone Hardware Unplugged** | ALSA/PulseAudio error in `AudioSource` | `READY_WAKE` ➔ `ERROR` | Close audio stream handle, purge ring buffer | "Microphone disconnected" | Retry device connection every 5s with backoff |
| **Corrupted Config File on Disk** | `tomllib.TOMLDecodeError` on startup | Halt startup / Retain LKG in memory | Do not overwrite disk file; reject reload | "Configuration file syntax error" | Retain last known good configuration |
| **SQLite Disk Full / Lock Timeout** | `sqlite3.OperationalError` | Log locally to stderr / `ERROR` | Roll back active transaction | "Storage write failed: disk full" | Drop non-essential audit events, preserve memory |
| **Cgroup Memory Pressure (MemoryHigh)** | Memory monitor detects RSS > 240 MB | Issue warning event to dashboard | Trigger Python `gc.collect()`, prune SSE queues | Warning banner on dashboard | Drop oldest cache entries, cap agent step buffers |
| **Prompt Injection via Web/Chat** | PolicyEngine classifies command as high risk | `ROUTING` ➔ `AWAITING_APPROVAL` | Hold command in broker; do not execute | Native popup requires human confirmation | If user denies or ignores, action is killed |
| **Site Adapter Broken by DOM Change**| Selector query returns zero elements | `ADAPTER_OUTDATED` result | Release tab content script context | "Site layout changed; adapter outdated" | Fall back to generic visible text extractor |

---

## 2. Fail-Closed Guarantees

1. **Network Partition Guarantee:** When all external internet connectivity is severed, Maya remains fully operational for all registered local actions, process executions, file operations, and desktop launcher tasks.
2. **Crash Invalidation Guarantee:** A grant issued before a crash or restart can NEVER execute post-recovery.
3. **No Phantom Subprocesses:** On daemon termination or task cancellation, child subprocesses receive `SIGTERM` followed by `SIGKILL` escalation.
