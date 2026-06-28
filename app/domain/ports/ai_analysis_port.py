from __future__ import annotations

"""Port for AI equity analysis adapters."""

from typing import Any, Protocol


class AiAnalysisPort(Protocol):
    def analyze(self, *, symbol: str, market: str, context: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        ...
