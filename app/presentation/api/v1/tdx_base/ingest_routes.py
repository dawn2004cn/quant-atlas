"""TDX base data ingest routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ValidationError
from app.core.logger import get_logger
from app.modules.data.services.tdx_base_data_service import TdxBaseDataService
from app.presentation.api.common import ok_response, require_data_ingestion_role
from app.presentation.api.v1.tdx_base.runtime import TdxBaseRuntime
from app.presentation.api.v1_context import ApiV1Context

logger = get_logger(__name__)


def register_tdx_base_ingest_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: TdxBaseRuntime,
) -> None:
    _ = ctx
    legacy = runtime.legacy

    @blueprint.post("/tdx/base-data/ingest")
    @login_required
    def tdx_base_ingest():
        """从本机通达信 hq_cache 导入基础数据到 MySQL（股票名称、板块与成分股）。"""
        require_data_ingestion_role()
        body = request.get_json(silent=True) or {}
        ingest_finance = bool(body.get("finance")) or bool(body.get("ingest_finance"))
        ingest_watchlists = bool(body.get("watchlists")) or bool(body.get("ingest_watchlists"))
        finance_max_symbols = body.get("finance_max_symbols")
        try:
            finance_max_symbols_int = (
                int(finance_max_symbols) if finance_max_symbols is not None else None
            )
        except (TypeError, ValueError):
            finance_max_symbols_int = None

        out = TdxBaseDataService().ingest_all_to_mysql(
            ingest_finance=ingest_finance,
            ingest_watchlists=ingest_watchlists,
            finance_max_symbols=finance_max_symbols_int,
        )
        ok = bool(out.get("ok"))
        if not ok:
            raise ValidationError(str(out.get("error") or "ingest_failed"))
        try:
            from app.modules.data.services.tdx_block_membership_cache import (
                get_tdx_block_membership_cache,
            )

            get_tdx_block_membership_cache().invalidate()
        except Exception as exc:
            logger.warning("tdx_base ingest cache invalidate failed: %s", exc)
        return ok_response(data=out, legacy_alias_key=None, enable_legacy_alias=legacy)
