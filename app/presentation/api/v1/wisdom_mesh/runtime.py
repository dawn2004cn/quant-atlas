"""Shared runtime for wisdom mesh HTTP routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.application.errors import ExternalServiceError
from app.presentation.api.common import require_ctx_service
from app.presentation.api.v1_context import ApiV1Context


@dataclass(frozen=True)
class WisdomMeshRuntime:
    ctx: ApiV1Context

    def require_service(self) -> Any:
        try:
            return require_ctx_service(self.ctx, "wisdom_mesh_service")
        except Exception as exc:
            raise ExternalServiceError("wisdom_mesh_unavailable") from exc
