"""Shared runtime for hot-sector HTTP routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flask import request

from app.presentation.api.common import ok_response
from app.presentation.api.request_parsers import parse_int_param
from app.presentation.api.route_deps import HotSectorRouteDeps, require_hot_sector_storage_service


@dataclass(frozen=True)
class HotSectorRuntime:
    legacy: bool
    storage: Any

    @classmethod
    def from_deps(cls, deps: HotSectorRouteDeps) -> HotSectorRuntime:
        return cls(
            legacy=deps.enable_legacy_response_fields,
            storage=require_hot_sector_storage_service(deps),
        )

    def sectors_response(self):
        limit = parse_int_param(request.args.get("limit"), name="limit", default=50, min_value=1, max_value=100)
        kind = (request.args.get("kind") or "all").strip().lower()
        source = (request.args.get("source") or "auto").strip().lower()
        snapshot_at = (request.args.get("snapshot_at") or "").strip() or None
        payload = self.storage.resolve_sectors(
            limit=limit,
            kind=kind,
            source=source,  # type: ignore[arg-type]
            snapshot_at=snapshot_at,
        )
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=self.legacy)
