# Maya Concurrency Model & Backpressure Specifications

Maya operates on a single-threaded cooperative multitasking model powered by Python's `asyncio` event loop. All I/O operations (HTTP requests, subprocess execution, file I/O, IPC pipes) are non-blocking.

---

## 1. Task Ownership & Supervision

| Long-Running Task | Task Owner | Supervisor Policy | Cancellation Behavior |
| :--- | :--- | :--- | :--- |
| **Audio Ingestion Loop** | `AudioSource` | Restart with exponential backoff on mic disconnect | Terminate PyAudio/sounddevice stream |
| **Wake Word Detector** | `WakeDetector` | Runs synchronously in dedicated thread or async worker | Release audio frame buffer |
| **FastAPI Dashboard Server**| `DashboardServer`| Lifespan managed by daemon startup | Graceful drain of active HTTP connections |
| **Agent Step Loop** | `AgentRuntime` | Bounded execution (max 15 steps); cancels on error | Terminate child subprocesses, flush partial evidence |
| **Native Messaging Host** | `NativeMessageBridge`| Managed subprocess with async pipe reader | Terminate stdin/stdout pipes, disconnect session |

---

## 2. Bounded Queues & Backpressure

To prevent memory leaks and runaway buffering, all asynchronous queues are strictly bounded:

```python
# 1. Audio Ring Buffer (Voice Pipeline)
MAX_AUDIO_RING_SECONDS = 3.0
MAX_AUDIO_RING_BYTES = 96000  # 16kHz * 2 bytes * 3s
# Backpressure: Oldest frames dropped when buffer reaches capacity.

# 2. Subprocess Output Buffer (ProcessExecutor)
MAX_SUBPROCESS_OUTPUT_BYTES = 65536  # 64 KB
# Backpressure: Additional subprocess stdout/stderr truncated, warning logged.

# 3. Dashboard Event Queue (SSE Streams)
MAX_SSE_EVENT_QUEUE_SIZE = 50
# Backpressure: Slow web clients drop oldest non-critical events.

# 4. Agent Step Transcript Buffer
MAX_TRANSCRIPT_BYTES = 65536  # 64 KB
# Backpressure: Middle dialogue turns summarized/compressed when ceiling hit.
```

---

## 3. Lock Hierarchy & Deadlock Prevention

To eliminate concurrency deadlocks, locks must be acquired strictly in order:

`AppState.lock` (1) ➔ `ApprovalBroker.lock` (2) ➔ `AgentRuntime.lock` (3) ➔ `Storage.lock` (4)

- Never hold an `asyncio.Lock` across an external network call (`NvidiaProvider`, `STTAdapter`).
- Never perform blocking synchronous file I/O while holding a state lock.
