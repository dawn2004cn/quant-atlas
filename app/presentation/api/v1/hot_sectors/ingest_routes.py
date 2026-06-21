"""Hot sector ingest routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ExternalServiceError, ValidationError
from app.presentation.api.common import ok_response, require_data_ingestion_role
from app.presentation.api.request_parsers import parse_int_param
from app.presentation.api.v1.hot_sectors.runtime import HotSectorRuntime
from app.presentation.api.v1_context import ApiV1Context


def register_hot_sector_ingest_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: HotSectorRuntime,
) -> None:
    _ = ctx
    legacy = runtime.legacy
    storage = runtime.storage

    @blueprint.post("/hot-sectors/ingest-ths")
    @login_required
    def ingest_hot_sectors_ths():
        """拉取同花顺四类板块（概念/地域/行业/证监会）及成分股写入 MySQL。"""
        require_data_ingestion_role()
        body = request.get_json(silent=True) or {}
        limit_per_kind = parse_int_param(
            body.get("limit_per_kind"),
            name="limit_per_kind",
            default=60,
            min_value=1,
            max_value=120,
        )
        ingest_members = bool(body.get("ingest_members", True))
        top_n = parse_int_param(
            body.get("top_sectors_for_members"),
            name="top_sectors_for_members",
            default=30,
            min_value=0,
            max_value=120,
        )
        members_limit = parse_int_param(
            body.get("members_limit"),
            name="members_limit",
            default=80,
            min_value=1,
            max_value=200,
        )
        try:
            result = storage.ingest_ths_snapshot(
                limit_per_kind=limit_per_kind,
                ingest_members=ingest_members,
                top_sectors_for_members=top_n,
                members_limit=members_limit,
            )
        except ValidationError:
            raise
        except (OSError, RuntimeError, TypeError, ValueError, KeyError) as exc:
            raise ExternalServiceError(
                "hot_sector_ths_ingest_failed",
                details={"reason": str(exc)},
            ) from exc
        return ok_response(data=result.to_dict(), legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/hot-sectors/ingest")
    @login_required
    def ingest_hot_sectors():
        """拉取多源榜单并写入 MySQL（``em_hot_sectors`` + Top 板块 ``em_hot_sector_members``）。"""
        require_data_ingestion_role()
        body = request.get_json(silent=True) or {}
        limit = parse_int_param(body.get("limit"), name="limit", default=80, min_value=1, max_value=100)
        kind = str(body.get("kind") or "all").strip().lower()
        ingest_members = bool(body.get("ingest_members", True))
        top_n = parse_int_param(
            body.get("top_sectors_for_members"),
            name="top_sectors_for_members",
            default=25,
            min_value=0,
            max_value=80,
        )
        members_limit = parse_int_param(
            body.get("members_limit"),
            name="members_limit",
            default=80,
            min_value=1,
            max_value=200,
        )
        try:
            result = storage.ingest_snapshot(
                limit=limit,
                kind=kind,
                ingest_members=ingest_members,
                top_sectors_for_members=top_n,
                members_limit=members_limit,
            )
        except ValidationError:
            raise
        except (OSError, RuntimeError, TypeError, ValueError, KeyError) as exc:
            raise ExternalServiceError(
                "hot_sector_ingest_failed",
                details={"reason": str(exc)},
            ) from exc
        return ok_response(data=result.to_dict(), legacy_alias_key=None, enable_legacy_alias=legacy)
