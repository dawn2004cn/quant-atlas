"""Hot sector members and preload routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.presentation.api.common import ok_response
from app.presentation.api.request_parsers import parse_int_param
from app.presentation.api.v1.hot_sectors.runtime import HotSectorRuntime
from app.presentation.api.v1_context import ApiV1Context


def register_hot_sector_member_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: HotSectorRuntime,
) -> None:
    _ = ctx
    legacy = runtime.legacy
    storage = runtime.storage

    @blueprint.get("/hot-sectors/<sector_code>/members")
    @login_required
    def hot_sector_members(sector_code: str):
        """板块成分股；优先读 MySQL 最新快照，``source=mysql`` 强制读库。"""
        limit = parse_int_param(request.args.get("limit"), name="limit", default=80, min_value=1, max_value=200)
        source = (request.args.get("source") or "auto").strip().lower()
        snapshot_at = (request.args.get("snapshot_at") or "").strip() or None
        board_kind = (request.args.get("board_kind") or request.args.get("kind") or "concept").strip().lower()
        sector_name = (request.args.get("name") or "").strip() or None
        provider = (request.args.get("provider") or "").strip().lower() or None
        members, mode = storage.resolve_members(
            sector_code,
            limit=limit,
            source=source,  # type: ignore[arg-type]
            snapshot_at=snapshot_at,
            board_kind=board_kind,
            sector_name=sector_name,
            provider=provider,
        )
        return ok_response(
            data={"items": members, "count": len(members), "source_mode": mode},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/hot-sectors/<sector_code>/preload-plan")
    @login_required
    def hot_sector_preload_plan(sector_code: str):
        """Top member preload plan for predictive sector navigation."""
        from app.modules.system.services.ui.predictive_preload_service import PredictivePreloadService

        limit = parse_int_param(request.args.get("limit"), name="limit", default=5, min_value=1, max_value=10)
        source = (request.args.get("source") or "auto").strip().lower()
        board_kind = (request.args.get("board_kind") or request.args.get("kind") or "concept").strip().lower()
        sector_name = (request.args.get("name") or "").strip() or None
        provider = (request.args.get("provider") or "").strip().lower() or None
        market = (request.args.get("market") or "CN").strip().upper()
        payload = PredictivePreloadService(hot_sector_storage_service=storage).build_sector_plan(
            sector_code=sector_code,
            market=market,
            limit=limit,
            source=source,
            sector_name=sector_name,
            board_kind=board_kind,
            provider=provider,
        )
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
            count=len(payload["candidates"]),
        )
