# Maya Reference Code Capsules (Implementation Tier A & B)

These code capsules provide near-complete (70–95%) reference implementations for all security-critical, concurrency-sensitive, and failure-prone subsystems. Future implementation engineers must follow these exact algorithmic patterns without improvising architecture.

---

## Capsule 1: Single-Use Approval Broker with Cryptographic Hash Binding (`CAP-001`)

```python
# app/policy/broker.py
import asyncio
import hashlib
import hmac
import time
import uuid
from typing import Mapping
from app.actions.schema import ActionRequest
from app.policy.risk import RiskLevel
from app.policy.broker_schema import ApprovalGrant

class ApprovalBroker:
    def __init__(self, timeout_seconds: float = 60.0):
        self.timeout_seconds = timeout_seconds
        self._pending_grants: dict[str, ApprovalGrant] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def compute_action_hash(req: ActionRequest) -> str:
        """Deterministically hash canonical serialized request payload."""
        canonical_bytes = req.model_dump_json().encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()

    async def request_approval(self, req: ActionRequest, reason: str, risk: RiskLevel) -> ApprovalGrant:
        action_hash = self.compute_action_hash(req)
        grant_id = str(uuid.uuid4())
        now = time.monotonic()
        grant = ApprovalGrant(
            grant_id=grant_id,
            action_hash=action_hash,
            created_at=now,
            expires_at=now + self.timeout_seconds,
            risk=risk,
            status="PENDING",
        )
        async with self._lock:
            # Enforce maximum 10 pending requests bound
            if len(self._pending_grants) >= 10:
                oldest_id = min(self._pending_grants, key=lambda k: self._pending_grants[k].created_at)
                del self._pending_grants[oldest_id]
            self._pending_grants[grant_id] = grant

        # In real runtime, spawns native popup; in tests, backend handles it
        return grant

    def verify_grant(self, grant_id: str, action_hash: str) -> bool:
        grant = self._pending_grants.get(grant_id)
        if not grant or grant.status != "PENDING":
            return False
        if time.monotonic() > grant.expires_at:
            grant.status = "EXPIRED"
            return False
        # Constant-time comparison prevents timing attacks
        return hmac.compare_digest(grant.action_hash, action_hash)

    def consume_grant(self, grant_id: str, action_hash: str) -> bool:
        if not self.verify_grant(grant_id, action_hash):
            return False
        # Atomically remove so grant cannot be replayed
        grant = self._pending_grants.pop(grant_id)
        grant.status = "CONSUMED"
        return True

    def reset(self) -> None:
        """Invalidate all grants upon daemon restart."""
        self._pending_grants.clear()
```

---

## Capsule 2: Bounded Audio Ring Buffer (`CAP-002`)

```python
# app/voice/audio.py
import collections
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

## Capsule 3: Subprocess Escalation & Bounded Output Capture (`CAP-003`)

```python
# app/executors/process.py
import asyncio
from pathlib import Path

MAX_OUTPUT_BYTES = 65536  # 64 KB

async def run_sandboxed_subprocess(argv: list[str], cwd: Path, timeout: float = 30.0) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *argv,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.DEVNULL,
    )
    try:
        async with asyncio.timeout(timeout):
            stdout_data, stderr_data = await proc.communicate()
    except (TimeoutError, asyncio.CancelledError):
        if proc.returncode is None:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=0.5)
            except TimeoutError:
                proc.kill()
                await proc.wait()
        raise

    # Bounded truncation
    stdout_str = stdout_data[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
    stderr_str = stderr_data[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
    return proc.returncode or 0, stdout_str, stderr_str
```

---

## Capsule 4: Native Messaging Host Protocol Framing (`CAP-004`)

```python
# app/browser/native_bridge.py
import struct
import sys
import json
import asyncio

MAX_MESSAGE_BYTES = 1048576  # 1 MB

async def read_native_message(reader: asyncio.StreamReader) -> dict:
    raw_length = await reader.readexactly(4)
    message_length = struct.unpack("=I", raw_length)[0]
    if message_length > MAX_MESSAGE_BYTES:
        raise ValueError(f"Message size {message_length} exceeds 1MB limit")
    message_bytes = await reader.readexactly(message_length)
    return json.loads(message_bytes.decode("utf-8"))

def write_native_message(writer: asyncio.StreamWriter, message: dict) -> None:
    encoded = json.dumps(message, separators=(",", ":")).encode("utf-8")
    header = struct.pack("=I", len(encoded))
    writer.write(header + encoded)
```

---

## Capsule 5: Secret-Safe SQLite Audit Transaction Pattern (`CAP-005`)

```python
# app/storage/sqlite.py
import sqlite3
from typing import Any

def record_audit_event_safe(conn: sqlite3.Connection, event: dict[str, Any]) -> None:
    # Filter out potential secret keys before persisting
    sanitized = {k: v for k, v in event.items() if not any(s in k.lower() for s in ("key", "token", "password", "secret"))}
    with conn:
        conn.execute(
            """
            INSERT INTO audit_log (timestamp, request_id, actor, tool, policy_decision, target, exit_code, duration_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sanitized.get("timestamp"),
                sanitized.get("request_id"),
                sanitized.get("actor"),
                sanitized.get("tool"),
                sanitized.get("policy_decision"),
                sanitized.get("target"),
                sanitized.get("exit_code"),
                sanitized.get("duration_ms"),
            ),
        )
```
