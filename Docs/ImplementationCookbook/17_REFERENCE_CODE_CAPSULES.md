# Maya Reference Code Capsules (Implementation Tier A & B)

These code capsules provide authoritative reference implementations for all security-critical, concurrency-sensitive, and failure-prone subsystems. Future implementation engineers must follow these exact algorithmic patterns without improvising architecture.

---

## Capsule 1: Single-Use Approval Broker with Atomic Grant Consumption (`CAP-001`)

```python
# app/policy/broker.py
import asyncio
import hashlib
import html
import hmac
from pathlib import Path
import re
import time
from typing import Any, Protocol
import uuid

from app.actions.schema import ActionRequest
from app.policy.risk import RiskLevel
from app.policy.broker_schema import (
    ApprovalDisplay,
    ApprovalGrant,
    ApprovalOutcome,
    PendingApproval,
    PopupDecision,
)

MAX_PENDING_APPROVALS = 10
MAX_ACTIVE_GRANTS = 10
ZENITY = Path("/usr/bin/zenity")

SENSITIVE_FLAGS = {
    "--password",
    "--passwd",
    "--token",
    "--api-key",
    "--apikey",
    "--authorization",
    "--cookie",
    "--secret",
}

SENSITIVE_KEY_RE = re.compile(
    r"(password|passwd|token|api[_-]?key|authorization|cookie|secret)",
    re.IGNORECASE,
)


def redact_argv(argv: list[str]) -> tuple[str, ...]:
    output: list[str] = []
    redact_next = False
    for item in argv:
        if redact_next:
            output.append("<redacted>")
            redact_next = False
            continue
        if "=" in item:
            flag, value = item.split("=", 1)
            if flag.lower() in SENSITIVE_FLAGS:
                output.append(f"{flag}=<redacted>")
                continue
        if item.lower() in SENSITIVE_FLAGS:
            output.append(item)
            redact_next = True
            continue
        output.append(item)
    return tuple(output)


def redact_mapping(value: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, item in value.items():
        if SENSITIVE_KEY_RE.search(key):
            safe[key] = "<redacted>"
        else:
            safe[key] = item
    return safe


class PopupBackend(Protocol):
    async def request_decision(
        self,
        pending: PendingApproval,
        display: ApprovalDisplay,
    ) -> str: ...

    async def cancel_request(
        self,
        pending_id: str,
    ) -> None: ...


class ZenityPopupBackend:
    def __init__(self) -> None:
        self._active: dict[str, asyncio.subprocess.Process] = {}
        self._lock = asyncio.Lock()

    async def request_decision(
        self,
        pending: PendingApproval,
        display: ApprovalDisplay,
    ) -> str:
        if not ZENITY.is_file():
            return "DENY"

        body_lines = [
            display.reason,
            "",
            f"Tool: {display.tool}",
            f"Target: {display.target}",
            f"Risk: {display.risk.value}",
            f"Fingerprint: {display.action_fingerprint}",
        ]
        if display.argv_preview:
            body_lines.append("Command: " + " ".join(display.argv_preview))
        if display.cwd:
            body_lines.append(f"Workspace: {display.cwd}")

        body = html.escape("\n".join(body_lines), quote=False)
        proc = await asyncio.create_subprocess_exec(
            str(ZENITY),
            "--question",
            "--title",
            display.title,
            "--text",
            body,
            "--ok-label",
            "Allow once",
            "--cancel-label",
            "Deny",
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

        async with self._lock:
            self._active[pending.pending_id] = proc

        try:
            rc = await proc.wait()
            return "ALLOW_ONCE" if rc == 0 else "DENY"
        finally:
            async with self._lock:
                self._active.pop(pending.pending_id, None)

    async def cancel_request(self, pending_id: str) -> None:
        async with self._lock:
            proc = self._active.get(pending_id)
        if proc is None or proc.returncode is not None:
            return
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=1.0)
        except TimeoutError:
            proc.kill()
            await proc.wait()


class ApprovalBroker:
    def __init__(
        self,
        popup_backend: PopupBackend,
        *,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.popup_backend = popup_backend
        self._popup_backend = popup_backend
        self.timeout_seconds = timeout_seconds
        self._timeout_seconds = timeout_seconds
        self._pending: dict[str, PendingApproval] = {}
        self._grants: dict[str, ApprovalGrant] = {}
        self._lock = asyncio.Lock()
        self._closed = False

    @staticmethod
    def compute_action_hash(request: ActionRequest) -> str:
        """Deterministically hash canonical serialized request payload."""
        return hashlib.sha256(request.to_canonical_bytes()).hexdigest()

    def _prune_expired_grants_locked(self, now: float) -> None:
        expired = [
            gid for gid, g in self._grants.items()
            if now > g.expires_at
        ]
        for gid in expired:
            self._grants.pop(gid, None)

    async def request_decision(
        self,
        req: ActionRequest,
        reason: str,
        risk: RiskLevel,
    ) -> ApprovalOutcome:
        action_hash = self.compute_action_hash(req)
        display = ApprovalDisplay(
            title=f"Security Approval Required ({risk.value})",
            tool=req.tool,
            target=req.workspace or req.arguments.get("path") or req.arguments.get("command") or "local",
            argv_preview=redact_argv(req.arguments.get("argv", [])) if "argv" in req.arguments else (),
            cwd=req.workspace,
            reason=reason,
            risk=risk,
            timeout_seconds=int(self._timeout_seconds),
            action_fingerprint=action_hash[:16],
        )
        return await self.request_approval(req, display, risk)

    async def request_approval(
        self,
        request: ActionRequest,
        display: ApprovalDisplay,
        risk: RiskLevel,
    ) -> ApprovalOutcome:
        action_hash = self.compute_action_hash(request)
        pending_id = str(uuid.uuid4())
        now = time.monotonic()

        pending = PendingApproval(
            pending_id=pending_id,
            action_hash=action_hash,
            created_at=now,
            expires_at=now + self._timeout_seconds,
            risk=risk,
        )

        async with self._lock:
            if self._closed:
                return ApprovalOutcome(decision="DENY", grant=None)
            self._prune_expired_grants_locked(now)
            if len(self._pending) >= MAX_PENDING_APPROVALS:
                return ApprovalOutcome(decision="DENY", grant=None)
            self._pending[pending_id] = pending

        try:
            async with asyncio.timeout(self._timeout_seconds):
                decision = await self._popup_backend.request_decision(pending, display)
        except asyncio.CancelledError:
            await self._popup_backend.cancel_request(pending_id)
            async with self._lock:
                self._pending.pop(pending_id, None)
            raise
        except TimeoutError:
            await self._popup_backend.cancel_request(pending_id)
            decision = "DENY"
        except Exception:
            await self._popup_backend.cancel_request(pending_id)
            decision = "DENY"
        finally:
            async with self._lock:
                self._pending.pop(pending_id, None)

        if decision != "ALLOW_ONCE":
            return ApprovalOutcome(decision="DENY", grant=None)

        now = time.monotonic()
        async with self._lock:
            if self._closed:
                return ApprovalOutcome(decision="DENY", grant=None)
            self._prune_expired_grants_locked(now)
            if len(self._grants) >= MAX_ACTIVE_GRANTS:
                return ApprovalOutcome(decision="DENY", grant=None)
            grant = ApprovalGrant(
                grant_id=str(uuid.uuid4()),
                action_hash=action_hash,
                created_at=now,
                expires_at=now + self._timeout_seconds,
                risk=risk,
                source="HUMAN_ALLOW_ONCE",
            )
            self._grants[grant.grant_id] = grant

        return ApprovalOutcome(decision="ALLOW_ONCE", grant=grant)

    async def consume_grant(
        self,
        grant_id: str,
        request: ActionRequest,
    ) -> bool:
        current_hash = self.compute_action_hash(request)
        now = time.monotonic()
        async with self._lock:
            grant = self._grants.get(grant_id)
            if grant is None:
                return False
            if now > grant.expires_at:
                self._grants.pop(grant_id, None)
                return False
            if not hmac.compare_digest(grant.action_hash, current_hash):
                self._grants.pop(grant_id, None)
                return False
            self._grants.pop(grant_id, None)
            return True

    async def aclose(self) -> None:
        async with self._lock:
            self._closed = True
            pending_ids = tuple(self._pending.keys())
            self._pending.clear()
            self._grants.clear()
        await asyncio.gather(
            *(self._popup_backend.cancel_request(pid) for pid in pending_ids),
            return_exceptions=True,
        )

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

## Capsule 4A: Firefox Native Messaging Host (stdio) (`CAP-004A`)

```python
# app/browser/native_host.py
import asyncio
import json
import os
from pathlib import Path
import struct
import sys

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


async def main() -> int:
    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    w_transport, w_protocol = await loop.connect_write_pipe(asyncio.streams.FlowControlMixin, sys.stdout)
    writer = asyncio.StreamWriter(w_transport, w_protocol, reader, loop)

    runtime_dir = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    socket_path = Path(runtime_dir) / "project-h" / "browser.sock"

    uds_reader, uds_writer = await asyncio.open_unix_connection(str(socket_path))
    try:
        while True:
            msg = await read_native_message(reader)
            write_native_message(uds_writer, msg)
            await uds_writer.drain()
            resp = await read_native_message(uds_reader)
            write_native_message(writer, resp)
            await writer.drain()
    except (asyncio.IncompleteReadError, ConnectionResetError):
        return 0
    finally:
        uds_writer.close()
        await uds_writer.wait_closed()
```

---

## Capsule 4B: Daemon Authenticated UDS Listener (`CAP-004B`)

```python
# app/browser/native_bridge.py
import asyncio
import os
from pathlib import Path
import socket
import struct
from typing import Callable, Awaitable
from app.browser.protocol import BrowserCommand, BrowserResponse

MAX_MESSAGE_BYTES = 1_048_576  # 1 MiB Project H limit


class NativeMessageBridge:
    def __init__(self, dispatch_fn: Callable[[BrowserCommand], Awaitable[BrowserResponse]]):
        self.dispatch_fn = dispatch_fn
        self.server: asyncio.Server | None = None

    async def start(self) -> None:
        runtime_dir = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "project-h"
        runtime_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        socket_path = runtime_dir / "browser.sock"
        if socket_path.exists():
            socket_path.unlink()

        self.server = await asyncio.start_unix_server(self._handle_client, path=str(socket_path))
        os.chmod(socket_path, 0o600)

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        sock = writer.get_extra_info("socket")
        if sock:
            creds = sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
            pid, uid, gid = struct.unpack("3i", creds)
            if uid != os.getuid():
                writer.close()
                await writer.wait_closed()
                return

        try:
            while True:
                raw_len = await reader.readexactly(4)
                msg_len = struct.unpack("=I", raw_len)[0]
                if msg_len > MAX_MESSAGE_BYTES:
                    break
                payload = await reader.readexactly(msg_len)
                cmd = BrowserCommand.model_validate_json(payload)
                resp = await self.dispatch_fn(cmd)
                encoded = resp.model_dump_json().encode("utf-8")
                writer.write(struct.pack("=I", len(encoded)) + encoded)
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionResetError):
            pass
        finally:
            writer.close()
            await writer.wait_closed()
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
