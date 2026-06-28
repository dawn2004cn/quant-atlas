from __future__ import annotations

"""Industry chain API routes."""


from flask import Blueprint, request
from flask_login import login_required

from app.core.registry import register_routes

from ...application.errors import ValidationError
from .common import ok_response, parse_market
from .decorators import service_fallback
from .v1_context import ApiV1Context


@register_routes(name="industry_chain", context="market_data", description="Industry chain API routes")
def register_industry_chain_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    @blueprint.get("/industry-chain")
    @login_required
    @service_fallback("industry_chain_service")
    def industry_chain():
        svc = getattr(ctx, "industry_chain_service", None)
        symbol = request.args.get("symbol")
        if not symbol:
            raise ValidationError("symbol_required")
        market = parse_market(request.args.get("market", "CN"))
        if hasattr(svc, "build_chain"):
            chain = svc.build_chain(symbol=symbol, market=market)
        else:
            chain = svc.get_chain_map(symbol, market)
        return ok_response(
            data=chain,
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )

    @blueprint.get("/industry-chain/tree")
    @login_required
    @service_fallback("industry_chain_service")
    def industry_chain_tree():
        svc = getattr(ctx, "industry_chain_service", None)
        data = svc.get_full_tree() if hasattr(svc, "get_full_tree") else {"tree": [], "industries": []}
        return ok_response(
            data=data,
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )
