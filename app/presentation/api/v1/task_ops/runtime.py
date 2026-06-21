"""Shared runtime for task ops HTTP routes."""

from __future__ import annotations

from dataclasses import dataclass

from app.presentation.api.v1_context import ApiV1Context


@dataclass(frozen=True)
class TaskOpsRuntime:
    ctx: ApiV1Context

    @property
    def legacy(self) -> bool:
        return self.ctx.enable_legacy_response_fields
