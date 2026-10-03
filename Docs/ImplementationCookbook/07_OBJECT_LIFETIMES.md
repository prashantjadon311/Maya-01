# Maya Object Lifetimes & Resource Disposal

Maya strictly manages the lifespans of all in-memory structures to guarantee that resident memory remains within the hard `MemoryHigh=240M` and `MemoryMax=300M` cgroup boundaries.

---

## 1. Object Lifetime Categories

| Component / Object | Lifetime Category | Creator | Closer / Cleanup Owner | Disposal Behavior |
| :--- | :--- | :--- | :--- | :--- |
| `ActionDispatcher` | `DAEMON` | `LifecycleManager.start()` | `LifecycleManager.stop()` | Close executors, flush pending audits |
| `PolicyEngine` | `DAEMON` | `LifecycleManager.start()` | `LifecycleManager.stop()` | Clear cached rules |
| `AppState` | `DAEMON` | `LifecycleManager.start()` | `LifecycleManager.stop()` | Cancel listeners, transition to `DISABLED` |
| `NvidiaProvider` | `DAEMON` | `LifecycleManager.start()` | `NvidiaProvider.aclose()` | Close underlying `httpx.AsyncClient` session |
| `AudioSource` | `DAEMON` | `VoiceSubsystem.start()` | `AudioSource.close()` | Terminate audio input stream, release ring buffer |
| `SQLiteStorage` | `DAEMON` | `StorageSubsystem.start()` | `SQLiteStorage.close()` | Close connection pool, execute WAL checkpoint |
| `StatusNotifierTray` | `DAEMON` | `TraySubsystem.start()` | `StatusNotifierTray.unregister()` | Release D-Bus bus name and path |
| `FastAPI Application` | `DAEMON` | `DashboardSubsystem.start()` | Uvicorn server lifespan exit | Terminate active SSE streams |
| `ApprovalRequest` | `COMMAND` | `ActionDispatcher.dispatch()` | `ApprovalBroker.consume_grant()` | Purged immediately upon consumption or timeout |
| `AgentTaskState` | `TASK` | `AgentRuntime.run_task()` | `AgentRuntime._finish_task()` | Write final state to SQLite, release context window |
| `Subprocess Handle` | `TRANSIENT` | `ProcessExecutor.execute()` | `ProcessExecutor` context manager | `wait()` or `terminate()`/`kill()` on timeout |
| `Command Audio Segment` | `COMMAND` | `CommandRecorder.record()` | `STTAdapter.transcribe()` | Explicitly deleted from RAM post-transcription |
| `Browser Native Pipe` | `SESSION` | Firefox Native Messaging Host | Extension tab disconnect | Flush pending queues, terminate pipe |

---

## 2. Leak-Prevention Rules

1. **Explicit Client Disposal:** Network clients (`AsyncOpenAI`, `httpx.AsyncClient`) must be closed explicitly via `aclose()` during shutdown.
2. **Audio Buffer Release:** Post-wake command audio byte arrays must not be retained in variables or closures after `STTAdapter` completes.
3. **Subprocess Cleanup Escalation:** Every spawned process has an explicit timeout. If `proc.wait()` times out, Maya issues `SIGTERM`, waits 500ms, and escalates to `SIGKILL`.
