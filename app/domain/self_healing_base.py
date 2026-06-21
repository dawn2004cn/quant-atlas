from __future__ import annotations

from typing import Any


class SelfHealingErrorMixin:
    """Optional mixin for AppError subclasses that can self-report repair hints."""

    hints: list[dict[str, str]] | None = None
    degraded_tag: str | None = None

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base["hints"] = list(self.hints or [])
        return base
