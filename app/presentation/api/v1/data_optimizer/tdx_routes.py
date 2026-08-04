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
