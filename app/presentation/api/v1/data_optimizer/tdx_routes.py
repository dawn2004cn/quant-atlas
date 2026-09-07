"""TDX symbol list and preload routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.domain.enums import MarketCode
from app.modules.data.services.helpers.data_optimizer_access import (
    build_tdx_history_adapter,
    build_tdx_optimized_adapter,
)
from app.presentation.api.common import ok_resource
from app.presentation.api.v1.data_optimizer._helpers import (
    parse_symbols_param,
    require_symbols,
    resolve_tdx_root,
)
from app.presentation.api.v1_context import ApiV1Context


def register_data_optimizer_tdx_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
) -> None:
    _ = ctx

    @blueprint.get("/tdx/symbols")
    @login_required
    def tdx_list_symbols():
        """List all symbols available in TDX."""
        tdx_root = resolve_tdx_root()
        adapter = build_tdx_history_adapter(tdx_root)
        symbols = adapter.get_symbols_list()

        return ok_resource(
            resource={"total": len(symbols), "symbols": symbols[:100]},
            resource_key="tdx_symbols",
            enable_legacy_alias=False,
        )

    @blueprint.get("/tdx/preload")
    @login_required
    def tdx_preload():
        """Preload symbols into TDX cache."""
        symbols = parse_symbols_param(request.args.get("symbols", ""))
        require_symbols(symbols)

        tdx_root = resolve_tdx_root()
        adapter = build_tdx_optimized_adapter(tdx_root)
        loaded = adapter.preload_symbols(symbols, MarketCode.CN)

        return ok_resource(
            resource={
                "requested": len(symbols),
                "loaded": loaded,
                "cache_size": adapter.cache_size,
            },
            resource_key="tdx_preload",
            enable_legacy_alias=False,
        )

    @blueprint.get("/tdx/status")
    @login_required
    def tdx_status():
        """通达信 PC 对等状态：本机 vipdoc + HQ 连接。"""
        from app.infrastructure.providers.cn_tdx_provider import create_tdx_provider
        from app.infrastructure.tdx_local.paths import resolve_tdx_root_configured

        root = resolve_tdx_root_configured()
        provider = create_tdx_provider()
        return ok_resource(
            resource={
                "tdx_root": str(root) if root else None,
                "local_available": root is not None,
                "hq_connected": provider.is_realtime_connected(),
                "symbol_count": len(provider.get_all_symbols(MarketCode.CN)) if root else 0,
            },
            resource_key="tdx_status",
            enable_legacy_alias=False,
        )

    @blueprint.get("/tdx/quotes")
    @login_required
    def tdx_quotes():
        """实时行情（通达信 HQ 批量 get_security_quotes）。"""
        from app.infrastructure.providers.cn_tdx_provider import create_tdx_provider

        symbols = parse_symbols_param(request.args.get("symbols", ""))
        require_symbols(symbols)
        provider = create_tdx_provider()
        rows = provider.get_quotes(symbols, MarketCode.CN)
        return ok_resource(
            resource={"items": rows, "count": len(rows), "source": "tdx"},
            resource_key="tdx_quotes",
            enable_legacy_alias=False,
        )

    @blueprint.get("/tdx/history")
    @login_required
    def tdx_history():
        """历史日 K：本地 vipdoc/lday 优先，缺失则 HQ 下载。"""
        from app.infrastructure.providers.cn_tdx_provider import create_tdx_provider

        symbol = (request.args.get("symbol") or "").strip()
        if not symbol:
            from app.application.errors import ValidationError

            raise ValidationError("symbol_required")
        start = request.args.get("start") or "2010-01-01"
        end = request.args.get("end")
        provider = create_tdx_provider()
        rows = provider.get_history(symbol, MarketCode.CN, start, end)
        return ok_resource(
            resource={
                "symbol": symbol,
                "items": rows,
                "count": len(rows),
                "source": rows[0].get("source") if rows else None,
            },
            resource_key="tdx_history",
            enable_legacy_alias=False,
        )
