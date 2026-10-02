"""Project H Browser Bridge Interface Protocol Stub (PH-040).

Browser execution in PH-040 fails closed until the authenticated
Unix-domain socket Native Messaging bridge is implemented in PH-110.
"""

from typing import Any, Protocol, runtime_checkable
from app.actions.schema import ActionResult


@runtime_checkable
class BrowserBridge(Protocol):
    """Protocol for browser interaction (to be implemented in PH-110)."""

    async def execute(self, action: str, url: str, params: dict[str, Any]) -> ActionResult:
        """Execute a browser action against the specified URL/tab."""
        ...
