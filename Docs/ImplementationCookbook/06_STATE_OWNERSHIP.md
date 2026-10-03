# Maya State Ownership & Concurrency Contract

In Maya, every mutable runtime state item has **exactly one architectural owner**. No component may mutate state owned by another component directly; all interactions occur via declared async methods or events.

---

## 1. State Ownership Matrix

| State Object | Sole Owner | Mutators | Readers | Persistence | Synchronization | Reset Conditions |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **System Lifecycle State** | `AppState` | `LifecycleManager`, `WakeDetector`, `Router` | Dashboard SSE, Tray, Dispatcher | Memory only | `asyncio.Lock` | Daemon restart |
| **Pending Approvals** | `ApprovalBroker` | `ApprovalBroker.request_approval`, `consume_grant` | `ActionDispatcher` | Memory only (Never disk) | `asyncio.Lock` | Request timeout or daemon restart |
| **Loaded Action Packs** | `ActionRegistry` | `ActionRegistry.load_pack`, `reload_packs` | `CommandRouter`, `ActionDispatcher` | Read from `actions.d/*.json` | Copy-on-write immutable snapshot | Pack file modification or restart |
| **Active Agent Task** | `AgentRuntime` | `AgentRuntime.run_task`, `step_task` | Dashboard API, Audit sink | SQLite task table | Single task execution lock | Task completion, error, or cancel |
| **Audio Ring Buffer** | `AudioSource` | `AudioSource.write_frames` (mic callback) | `WakeDetector`, `CommandRecorder` | RAM only (bounded ring) | Circular buffer with overflow drop | Wake detection or disable listening |
| **Audit Logs & History** | `SQLiteStorage` | `ActionDispatcher.audit_sink`, `API` | Dashboard API query | `~/.local/share/project-h/maya.db` | SQLite WAL mode + connection pool | Configured retention policy purge |
| **Browser IPC Connection** | `NativeMessageBridge` | `NativeMessageBridge.connect`, `disconnect` | `ActionDispatcher` | Ephemeral pipe | Async stream reader/writer locks | Extension tab close or browser exit |
| **Runtime Configuration** | `ConfigStore` | `DashboardAPI.update_config` | All subsystems (read-only snapshot) | `~/.config/project-h/config.toml` | Atomic file write + transactional reload | Reload signal or config update |

---

## 2. Invariant Synchronization Rules

1. **No Shared Mutable Dicts/Lists:** Components publish immutable snapshots (using Pydantic models or deep copied dictionaries) when sharing read state with callers.
2. **Lock Hierarchy to Prevent Deadlocks:**
   - Level 1: `AppState.lock`
   - Level 2: `ApprovalBroker.lock`
   - Level 3: `AgentRuntime.lock`
   - Level 4: `Storage.transaction_lock`
   *Rules:* Never acquire a higher-numbered lock while holding a lower-numbered lock.
