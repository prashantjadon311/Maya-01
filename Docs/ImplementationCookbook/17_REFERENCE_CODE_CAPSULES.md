# Maya Reference Code Capsules (Implementation Tier A & B)

These code capsules provide authoritative reference implementations for all security-critical, concurrency-sensitive, and failure-prone subsystems. Future implementation engineers must follow these exact algorithmic patterns without improvising architecture.

---

## Capsule 1: Single-Use Approval Broker with Atomic Grant Consumption (`CAP-001`)

```python
# app/policy/broker.py
import asyncio
import hashlib
import hmac
import time
import uuid
from typing import Protocol
from app.actions.schema import ActionRequest
from app.policy.risk import RiskLevel
from app.policy.broker_schema import (
    ApprovalDisplay,
    ApprovalGrant,
    PendingApproval,
    PopupDecision,
)

MAX_PENDING_APPROVALS = 10


class PopupBackend(Protocol):
    async def request_decision(
        self,
        pending: PendingApproval,
        display: ApprovalDisplay,
    ) -> PopupDecision: ...


class ApprovalBroker:
    def __init__(self, popup_backend: PopupBackend, timeout_seconds: float = 60.0):
        self.popup_backend = popup_backend
        self.timeout_seconds = timeout_seconds
        self._pending: dict[str, PendingApproval] = {}
        self._grants: dict[str, ApprovalGrant] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def compute_action_hash(req: ActionRequest) -> str:
        """Deterministically hash canonical serialized request payload."""
        canonical_bytes = req.model_dump_json().encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()

    async def request_decision(
        self,
        req: ActionRequest,
        reason: str,
        risk: RiskLevel,
    ) -> PopupDecision:
        action_hash = self.compute_action_hash(req)
        pending_id = str(uuid.uuid4())
        now = time.monotonic()

        pending = PendingApproval(
            pending_id=pending_id,
            action_hash=action_hash,
            created_at=now,
            expires_at=now + self.timeout_seconds,
            reason=reason,
            risk=risk,
            request=req,
        )

        async with self._lock:
            # Capacity guard: fail closed/busy when full; never silently evict active pending approval
            if len(self._pending) >= MAX_PENDING_APPROVALS:
                return PopupDecision.DENY
            self._pending[pending_id] = pending

        display = ApprovalDisplay(
            title=f"Security Approval Required ({risk.value})",
            reason=reason,
            tool=req.tool,
            action_hash=action_hash,
            timeout_seconds=int(self.timeout_seconds),
        )

        decision = PopupDecision.DENY
        try:
            async with asyncio.timeout(self.timeout_seconds):
                decision = await self.popup_backend.request_decision(pending, display)
        except (TimeoutError, asyncio.CancelledError, Exception):
            decision = PopupDecision.DENY
        finally:
            async with self._lock:
                # Remove from pending; PENDING is NEVER consumable
                self._pending.pop(pending_id, None)

                # Only explicit ALLOW_ONCE mints a single-use ApprovalGrant
                if decision == PopupDecision.ALLOW_ONCE:
                    grant_id = str(uuid.uuid4())
                    grant = ApprovalGrant(
                        grant_id=grant_id,
                        action_hash=action_hash,
                        created_at=time.monotonic(),
                        expires_at=time.monotonic() + self.timeout_seconds,
                        risk=risk,
                        source="HUMAN_ALLOW_ONCE",
                    )
                    self._grants[grant_id] = grant

        return decision

    async def consume_grant(self, grant_id: str, request: ActionRequest) -> bool:
        """Atomically verify and consume a grant in a single critical section."""
        request_hash = self.compute_action_hash(request)
        async with self._lock:
            grant = self._grants.get(grant_id)
            if grant is None:
                return False

            now = time.monotonic()
            if now > grant.expires_at:
                self._grants.pop(grant_id, None)
                return False

            # Constant-time comparison prevents timing attacks
            if not hmac.compare_digest(grant.action_hash, request_hash):
                # Hash mismatch invalidates grant immediately
                self._grants.pop(grant_id, None)
                return False

            # Valid grant: atomically pop so it cannot be replayed
            self._grants.pop(grant_id, None)
            return True

    def reset(self) -> None:
        """Invalidate all pending requests and grants upon daemon restart."""
        self._pending.clear()
        self._grants.clear()
```

---

## Capsule 2: Bounded Audio Ring Buffer (`CAP-002`)

```python
# app/voice/audio.py
import asyncio

class AudioRingBuffer:
    def __init__(self, max_seconds: float = 3.0, sample_rate: int = 16000, sample_width: int = 2):
        self.bytes_per_second = sample_rate * sample_width
        self.max_bytes = int(max_seconds * self.bytes_per_second)
        self._buffer = bytearray()
        self._lock = asyncio.Lock()

    async def write(self, pcm_chunk: bytes) -> None:
        async with self._lock:
            self._buffer.extend(pcm_chunk)
            if len(self._buffer) > self.max_bytes:
                # Drop oldest audio frames (FIFO) to enforce hard memory cap
                excess = len(self._buffer) - self.max_bytes
                del self._buffer[:excess]

    async def read_snapshot(self) -> bytes:
        async with self._lock:
            return bytes(self._buffer)

    async def clear(self) -> None:
        async with self._lock:
            self._buffer.clear()
```

---

## Capsule 3: Continuous Stream Drain Subprocess Execution (`CAP-003`)

```python
# app/executors/process.py
import asyncio
from pathlib import Path

MAX_OUTPUT_BYTES = 1_048_576  # 1 MiB per stream


async def _read_stream_bounded(stream: asyncio.StreamReader, limit: int) -> str:
    """Continuously drain stream chunks into bounded memory without unbounded buffering."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await stream.read(4096)
        if not chunk:
            break
        if total < limit:
            remaining = limit - total
            chunks.append(chunk[:remaining])
            total += len(chunk[:remaining])
        # Continue draining stream until EOF so child process does not block on write pipe
    return b"".join(chunks).decode("utf-8", errors="replace")


async def run_sandboxed_subprocess(
    argv: list[str],
    cwd: Path,
    env: dict[str, str],
    timeout: float = 30.0,
) -> tuple[int, str, str]:
    """Execute subprocess with bounded stream draining, timeout escalation, and child reaping."""
    proc = await asyncio.create_subprocess_exec(
        *argv,
        cwd=cwd,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.DEVNULL,
    )

    stdout_task = asyncio.create_task(_read_stream_bounded(proc.stdout, MAX_OUTPUT_BYTES))
    stderr_task = asyncio.create_task(_read_stream_bounded(proc.stderr, MAX_OUTPUT_BYTES))

    try:
        async with asyncio.timeout(timeout):
            await proc.wait()
    except (TimeoutError, asyncio.CancelledError):
        if proc.returncode is None:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=0.5)
            except TimeoutError:
                proc.kill()
                await proc.wait()
        raise
    finally:
        # Guarantee child process is reaped and stream reader tasks complete
        if proc.returncode is None:
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass
        stdout_str = await stdout_task
        stderr_str = await stderr_task

    return proc.returncode or 0, stdout_str, stderr_str
```

---

## Capsule 4: Native Messaging Host Protocol Framing (`CAP-004`)

```python
# app/browser/native_bridge.py
import struct
import json
import asyncio

MAX_MESSAGE_BYTES = 1_048_576  # 1 MiB Project H limit


async def read_native_message(reader: asyncio.StreamReader) -> dict:
    raw_length = await reader.readexactly(4)
    message_length = struct.unpack("=I", raw_length)[0]
    if message_length > MAX_MESSAGE_BYTES:
        raise ValueError(f"Message size {message_length} exceeds 1MB limit")
    message_bytes = await reader.readexactly(message_length)
    return json.loads(message_bytes.decode("utf-8"))


def write_native_message(writer: asyncio.StreamWriter, message: dict) -> None:
    encoded = json.dumps(message, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_MESSAGE_BYTES:
        raise ValueError(f"Outbound message size {len(encoded)} exceeds 1MB limit")
    header = struct.pack("=I", len(encoded))
    writer.write(header + encoded)
```

---

## Capsule 5: Typed Allowlisted Audit Persistence (`CAP-005`)

```python
# app/storage/sqlite.py
import sqlite3
from app.storage.schema import AuditEvent


def record_audit_event_safe(conn: sqlite3.Connection, event: AuditEvent) -> None:
    """Persist typed allowlisted audit event metadata only.

    SECURITY INVARIANT:
    Never persists stdout/stderr, content, environment, raw exceptions, prompts, or DOM.
    """
    with conn:
        conn.execute(
            """
            INSERT INTO audit_log (
                timestamp, request_id, actor, tool, policy_decision,
                approval_result, target, result_code, duration_ms, error_code
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.timestamp,
                event.request_id,
                event.actor,
                event.tool,
                event.policy_decision,
                event.approval_result,
                event.target,
                event.result_code,
                event.duration_ms,
                event.error_code,
            ),
        )
```
