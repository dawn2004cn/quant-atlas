"""Shared runtime for swarm topology HTTP routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.middleware.request_context import require_authenticated_user_id
from app.presentation.api.v1_context import ApiV1Context


@dataclass(frozen=True)
class SwarmTopologyRuntime:
    ctx: ApiV1Context

    @property
    def legacy(self) -> bool:
        return self.ctx.enable_legacy_response_fields

    @property
    def topology_service(self) -> Any:
        return getattr(self.ctx, "swarm_topology_service", None)

    @property
    def adaptive_service(self) -> Any:
        return getattr(self.ctx, "adaptive_topology_service", None)

    @staticmethod
    def user_id() -> int:
        return require_authenticated_user_id()
