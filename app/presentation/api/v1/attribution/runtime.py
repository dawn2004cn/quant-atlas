"""Shared runtime for attribution HTTP routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.presentation.api.v1_context import ApiV1Context


@dataclass(frozen=True)
class AttributionRuntime:
    ctx: ApiV1Context | None

    @property
    def market_service(self) -> Any:
        if self.ctx is None:
            return None
        return self.ctx.market_service or self.ctx.stock_service
