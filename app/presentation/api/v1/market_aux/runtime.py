"""Shared runtime for market auxiliary HTTP routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.presentation.api.v1_context import ApiV1Context


@dataclass(frozen=True)
class MarketAuxRuntime:
    ctx: ApiV1Context

    @property
    def legacy(self) -> bool:
        return self.ctx.enable_legacy_response_fields

    @property
    def enable_celery(self) -> bool:
        return bool(self.ctx.enable_celery)

    @property
    def task_dispatcher(self) -> Any:
        return self.ctx.task_dispatcher

    @property
    def task_message_store(self) -> Any:
        return self.ctx.task_message_store

    @property
    def basic_market_data_service(self) -> Any:
        return getattr(self.ctx, "basic_market_data_service", None)

    @property
    def market_narrative_service(self) -> Any:
        return getattr(self.ctx, "market_narrative_service", None)
