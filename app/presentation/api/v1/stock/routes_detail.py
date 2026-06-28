from __future__ import annotations
from flask import Blueprint
from flask_login import login_required
from app.core.logger import get_logger
from app.core.registry import register_routes
from ...v1_context import ApiV1Context
from ...common import ok_resource, parse_market
from ...decorators import service_fallback
from ...stock_route_helpers import build_sector_context

logger = get_logger(__name__)

@register_routes(name="stock_detail", context="market_data", description="Stock detail")
def register_stock_detail(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields
    stock_service = ctx.stock_service

    @blueprint.get("/stocks/<market>/<symbol>")





    @login_required
    @service_fallback("stock_service")





    def stock_detail(market: str, symbol: str):






        m = parse_market(market)




        try:





            detail = stock_service.get_stock_detail(symbol, m)





            from app.domain.shared.market_fact import enrich_quote_with_facts











            if isinstance(detail, dict):





                profile = detail.get("profile", {}) or {}





                realtime = profile.get("realtime", {}) if isinstance(profile, dict) else {}





                detail["quote_fact"] = enrich_quote_with_facts(





                    realtime,





                    detail.get("indicators") or {},





                    symbol=symbol,





                    market=m.value,





                )





                from app.modules.market_data.services.data_coverage_service import DataCoverageService











                detail["data_coverage"] = DataCoverageService(stock_service).assess_symbol(





                    symbol, m





                ).model_dump()





                detail["sector_context"] = build_sector_context(





                    symbol=symbol,





                    market=m,





                    industry_chain_service=ctx.industry_chain_service,





                )





                return ok_resource(





                    resource=detail,





                    resource_key="stock",





                    enable_legacy_alias=legacy,





                    profile=detail.get("profile", {}),





                )





            payload = detail.model_dump() if hasattr(detail, "model_dump") else (detail.to_dict() if hasattr(detail, "to_dict") else detail)





            profile = payload.get("profile", {}) or {}





            realtime = profile.get("realtime", {}) if isinstance(profile, dict) else {}





            payload["quote_fact"] = enrich_quote_with_facts(





                realtime,





                payload.get("indicators") or {},





                symbol=symbol,





                market=m.value,





            )





            from app.modules.market_data.services.data_coverage_service import DataCoverageService











            payload["data_coverage"] = DataCoverageService(stock_service).assess_symbol(





                symbol, m





            ).model_dump()





            payload["sector_context"] = build_sector_context(





                symbol=symbol,





                market=m,





                industry_chain_service=ctx.industry_chain_service,





            )





            return ok_resource(





                resource=payload,





                resource_key="stock",





                enable_legacy_alias=legacy,





                profile=detail.profile,





            )





        except Exception as e:





            logger.error(f"stock_detail error: {symbol} {market} - {e}")





            raise
