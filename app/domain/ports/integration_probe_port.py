from __future__ import annotations

from typing import Any, Protocol


class IntegrationProbePort(Protocol):
    """Read-only integration table probes for stack status."""

    def count_tables(self, tables: tuple[tuple[str, str], ...]) -> dict[str, Any]:
        ...
