"""Shared runtime for federated mesh HTTP routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.presentation.api.v1_context import ApiV1Context


@dataclass(frozen=True)
class MeshRuntime:
    ctx: ApiV1Context

    @property
    def legacy(self) -> bool:
        return self.ctx.enable_legacy_response_fields

    @property
    def gateway_service(self) -> Any:
        return getattr(self.ctx, "mesh_gateway_service", None)
