from __future__ import annotations

"""Stock financial data routes."""

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ValidationError
from app.core.registry import register_routes
from app.domain.enums import MarketCode
from app.modules.data.services.gpcw_service import get_gpcw_service
from ...common import ok_response, parse_market
from ...decorators import service_fallback


@register_routes(name="stock_financials", context="market_data", description="Stock fundamentals & TDX financials")
def register_stock_financials(blueprint: Blueprint, ctx) -> None:


    legacy = ctx.enable_legacy_response_fields
    fundamental_access = ctx.fundamental_access

    @blueprint.get("/stocks/<market>/<symbol>/fundamentals")
    @login_required
    @service_fallback("fundamental_access")
    def stock_fundamentals(market: str, symbol: str):
        from app.domain.enums import MarketCode





        m = parse_market(market)






        if m != MarketCode.CN:






            raise ValidationError("fundamentals endpoint supports CN market only")






        bundle = fundamental_access.cn_financial_bundle(symbol)






        return ok_response(






            data=bundle,






            legacy_alias_key=None,






            enable_legacy_alias=legacy,






            symbol=bundle.get("symbol"),






            em_symbol=bundle.get("em_symbol"),






        )


    @blueprint.get("/stocks/<market>/<symbol>/tdx-financial")
    @login_required
    def stock_tdx_financial(market: str, symbol: str):
        from app.domain.enums import MarketCode





        m = parse_market(market)






        if m != MarketCode.CN:






            raise ValidationError("tdx-financial endpoint supports CN market only")






        incoming = symbol.strip()






        code6 = incoming[-6:] if len(incoming) >= 6 else incoming






        market_tag = "sh"






        if len(incoming) >= 6:






            prefix3 = incoming[-6:][:3]






            if prefix3 in ("000", "002", "003", "300", "301", "302"):






                market_tag = "sz"






            elif prefix3 in ("920", "921"):






                market_tag = "bj"






        indexed_code = f"CN:{market_tag}{code6}"






        service = get_gpcw_service()






        periods_meta = service.get_stock_periods(code6)






        if not periods_meta:






            return ok_response(






                data={






                    "indexed_code": indexed_code,






                    "code": code6,






                    "market": market_tag,






                    "periods": [],






                    "source": "mysql",






                    "has_data": False,






                },






                legacy_alias_key=None,






                enable_legacy_alias=legacy,






            )






        result = []






        for pm in periods_meta:






            report_date = pm["report_date"]






            period_str = f"{report_date // 10000}/{report_date % 10000 // 100:02d}"






            payload = service.get_stock_data(code6, report_date)






            result.append({






                "report_date": report_date,






                "period": period_str,






                "source_file": pm["source_file"],






                "fields": payload or {},






                "non_zero_count": pm.get("non_zero_count", 0),






            })






        return ok_response(






            data={






                "indexed_code": indexed_code,






                "code": code6,






                "market": market_tag,






                "periods": result,






                "source": "mysql",






                "has_data": bool(result),






            },






            legacy_alias_key=None,






            enable_legacy_alias=legacy,






        )
