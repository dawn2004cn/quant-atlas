"""Shared runtime for strategy synthesis HTTP routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.presentation.api.common import ok_response
from app.presentation.api.v1_context import ApiV1Context


@dataclass(frozen=True)
class StrategySynthesisRuntime:
    ctx: ApiV1Context

    @property
    def synthesizer(self) -> Any:
        return getattr(self.ctx, "strategy_synthesizer_service", None)

    def unavailable_response(self):
        return ok_response(data={"available": False, "summary": "Service unavailable"})
