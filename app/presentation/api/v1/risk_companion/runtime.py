"""Shared runtime for risk companion HTTP routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.application.errors import ExternalServiceError
from app.presentation.api.common import require_ctx_service
from app.presentation.api.v1_context import ApiV1Context


@dataclass(frozen=True)
class RiskCompanionRuntime:
    ctx: ApiV1Context

    def require_service(self) -> Any:
        try:
            return require_ctx_service(self.ctx, "risk_companion_service")
        except Exception as exc:
            raise ExternalServiceError("risk_companion_unavailable") from exc
