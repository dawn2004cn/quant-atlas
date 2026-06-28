from __future__ import annotations

"""TDX connector protocol."""


from typing import Any, Protocol


class TdxClient(Protocol):
    """Minimal TDX client contract used by market provider."""

    @property
    def is_available(self) -> bool:
        """Whether the client backend exists."""

    @property
    def is_connected(self) -> bool:
        """Whether the client is connected to server."""

    def reconnect(self) -> None:
        """Try to reconnect if disconnected."""

    def execute(self, method: str, *args: Any) -> Any:
        """Execute a low-level TDX call."""
