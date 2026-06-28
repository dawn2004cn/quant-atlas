from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Stock analysis composition service."""


from typing import Any

from app.application.dto.market_data_dto import StockDetailDTO


class StockAnalysisService:
    """Build frontend-oriented stock analysis payload from stock detail data."""

    def build_analysis(
        self,
        symbol: str,
        detail: StockDetailDTO | dict[str, Any],
        *,
        user_hypothesis: str | None = None,
        hypothesis_id: str | None = None,
    ) -> GenericResponseDTO[str, object]:
        if hasattr(detail, 'model_dump'):
            detail = detail.model_dump()
        profile = detail.get("profile", {})
        realtime = profile.get("realtime", {})
        indicators = detail.get("indicators", {})
        news = detail.get("news", [])
        price = float(realtime.get("price", 0) or 0)
        ma20 = float(indicators.get("ma20") or price)
        trend = "看多" if ma20 <= price else "中性"
        payload: GenericResponseDTO[str, object] = {
            "stockCode": symbol,
            "stockName": realtime.get("name") or profile.get("detail", {}).get("name", symbol),
            "currentPrice": f"{price:.2f}",
            "changePct": f"{float(realtime.get('change_pct', 0) or 0):.2f}",
            "rating": 4 if trend == "看多" else 3,
            "technicalIndicators": {
                "ma5": indicators.get("ma20") or price,
                "ma10": indicators.get("ema12") or price,
                "ma20": indicators.get("ma20") or price,
                "ma60": indicators.get("ma20") or price,
                "dif": indicators.get("macd") or 0,
                "dea": indicators.get("macd_signal") or 0,
                "rsi": indicators.get("rsi14") or 50,
                "macd": indicators.get("macd") or 0,
                "kdj": {
                    "k": indicators.get("stoch_k") or 50,
                    "d": indicators.get("stoch_d") or 50,
                    "j": (indicators.get("stoch_k") or 50) * 1.5 - (indicators.get("stoch_d") or 50) * 0.5,
                },
            },
            "supportResistance": {
                "resistance3": f"{price * 1.15:.2f}",
                "resistance2": f"{price * 1.10:.2f}",
                "resistance1": f"{price * 1.05:.2f}",
                "support1": f"{price * 0.95:.2f}",
                "support2": f"{price * 0.90:.2f}",
                "support3": f"{price * 0.85:.2f}",
            },
            "analysis": {
                "trend": trend,
                "newsCount": len(news),
                "summary": f"当前共抓取到 {len(news)} 条相关新闻，指标面偏{trend}。",
            },
            "tradingPlan": {
                "buyPrice": f"{price * 0.97:.2f}",
                "sellPrice": f"{price * 1.05:.2f}",
                "stopLoss": f"{price * 0.92:.2f}",
            },
        }
        from app.modules.ai_agent.services.analysis.hypothesis_evaluation_service import (
            HypothesisEvaluationService,
        )

        hypo = HypothesisEvaluationService().evaluate(
            symbol=symbol,
            detail={"profile": profile, "indicators": indicators, "news": news},
            hypothesis_id=hypothesis_id,
            user_hypothesis=user_hypothesis,
            market=str(detail.get("market") or "CN"),
        )
        from app.domain.shared.market_fact import enrich_quote_with_facts

        payload["quote_fact"] = enrich_quote_with_facts(
            realtime,
            indicators,
            symbol=symbol,
            market=str(detail.get("market") or "CN"),
        )
        if hypo is not None:
            payload["hypothesis_evaluation"] = hypo.model_dump()
        return payload
