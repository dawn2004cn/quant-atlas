from __future__ import annotations
from flask import Blueprint
from flask_login import login_required
from app.core.registry import register_routes
from ...v1_context import ApiV1Context
from app.core.logger import get_logger
from app.domain.enums import MarketCode
from app.domain.dto.stock_request_dto import StockHistoryRequest

from ...common import ok_collection, ok_response, parse_market
from ...decorators import service_fallback
from ...dto_validation import validate_request

logger = get_logger(__name__)

@register_routes(name="stock_history", context="market_data", description="Stock history Kline")
def register_stock_history(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields
    stock_service = ctx.stock_service

    @blueprint.get("/stocks/<market>/<symbol>/history")





    @validate_request(StockHistoryRequest, source="args")





    def stock_history(market: str, symbol: str, req: StockHistoryRequest):





        start = req.start





        end = req.end





        max_points = req.max_points





        chart_width = req.width





        stock_service = getattr(ctx, "stock_service", None)
        if stock_service is None:
            return ok_collection(items=[], item_key="history", enable_legacy_alias=legacy, symbol=symbol, market=market.upper(), indicators={}, point_count=0, original_point_count=0, sampled=False)

        try:





            history = stock_service.get_history(symbol, parse_market(market), start, end)





            if isinstance(history, list):





                items = history





                indicators = {}





            else:





                history_dict = history.model_dump()





                items = history_dict.get("history", []) or []





                indicators = history_dict.get("indicators", {})





        except Exception as e:





            logger.error(f"stock_history error: {symbol} {market} - {e}")





            items = []





            indicators = {}





        original_count = len(items)





        sampled = False





        sample_target = None





        if max_points > 0 or chart_width > 0:





            from app.domain.shared.bar_sampler import lttb_sample_ohlcv, resolve_sample_target











            sample_target = resolve_sample_target(





                max_points if max_points > 0 else None,





                chart_width if chart_width > 0 else None,





            )





            if sample_target and original_count > sample_target:





                items = lttb_sample_ohlcv(items, sample_target)





                sampled = True





        from app.domain.shared.market_fact import enrich_history_with_facts
        items = enrich_history_with_facts(items)





        meta_kw: dict[str, object] = {





            "symbol": symbol,





            "market": market.upper(),





            "indicators": indicators,





            "point_count": len(items),





            "original_point_count": original_count,





            "sampled": sampled,





        }





        if sample_target:





            meta_kw["max_points"] = sample_target





        if not items and parse_market(market) == MarketCode.CN:





            meta_kw["empty_hint"] = (





                "CN still no K-line: ensure TDX dayk sync / MySQL stock_history_* has data. "





                "Read priority: MySQL -> qlib_bin -> TDX lday -> eastmoney."





            )





        return ok_collection(





            items=items,





            item_key="history",





            enable_legacy_alias=legacy,





            **meta_kw,





        )
