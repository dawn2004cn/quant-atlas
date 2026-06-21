"""Shared runtime for TDX base-data HTTP routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.presentation.api.route_deps import TdxBaseRouteDeps, require_tdx_base_read_service


@dataclass(frozen=True)
class TdxBaseRuntime:
    legacy: bool
    tdx_read: Any

    @classmethod
    def from_deps(cls, deps: TdxBaseRouteDeps) -> TdxBaseRuntime:
        return cls(
            legacy=deps.enable_legacy_response_fields,
            tdx_read=require_tdx_base_read_service(deps),
        )
