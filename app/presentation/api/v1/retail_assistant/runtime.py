"""Shared runtime for retail-assistant HTTP routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.presentation.api.common import ok_response
from app.presentation.api.v1_context import ApiV1Context


@dataclass(frozen=True)
class RetailAssistantRuntime:
    ctx: ApiV1Context

    @property
    def legacy(self) -> bool:
        return self.ctx.enable_legacy_response_fields

    @property
    def hub_service(self) -> Any:
        return getattr(self.ctx, "retail_assistant_hub_service", None)

    def hub_unavailable_response(self):
        return ok_response(
            data={"available": False, "summary": "Service unavailable"},
            legacy_alias_key=None,
            enable_legacy_alias=self.legacy,
        )
