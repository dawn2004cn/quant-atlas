"""Watchlist Risk Radar - 全站级风险雷达与止盈止损建议."""

from __future__ import annotations
from datetime import datetime
from typing import Any, List, Optional, Dict
from app.domain.enums import MarketCode
from app.domain.ports import MarketDataProvider, IndicatorProvider
from app.domain.dto.risk_dto import RiskAlertDTO, WatchlistRiskReportDTO, RiskLevel
from app.domain.dto.service_result import GenericResponseDTO


class SupportResistanceCalculator:
    """支撑位和压力位计算器."""

    @staticmethod
    def calculate_levels(
        history: List[Dict[str, Any]],
        current_price: float,
    ) -> Dict[str, Any]:
        """计算支撑位和压力位."""
        if not history or current_price <= 0:
            return {
                "support": [],
                "resistance": [],
                "current_position": "unknown",
            }

        prices = [float(h.get("close", 0)) for h in history if h.get("close", 0) > 0]
        if not prices:
            return {
                "support": [],
                "resistance": [],
                "current_position": "unknown",
            }

        high = max(prices)
        low = min(prices)
        avg = sum(prices) / len(prices)

        fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786]
        range_val = high - low

        supports = []
        resistances = []

        for fib in fib_levels:
            level = low + range_val * fib
            if level < current_price:
                supports.append(round(level, 2))
            else:
                resistances.append(round(level, 2))

        sma_20 = sum(prices[-20:]) / min(20, len(prices)) if len(prices) >= 20 else avg
        if sma_20 < current_price:
            supports.append(round(sma_20, 2))
        else:
            resistances.append(round(sma_20, 2))

        supports.append(round(low * 1.02, 2))
        resistances.append(round(high * 0.98, 2))

        if current_price > high * 0.95:
            position = "near_resistance"
        elif current_price < low * 1.05:
            position = "near_support"
        elif current_price > avg:
            position = "above_average"
        else:
            position = "below_average"

        return {
            "support": sorted(set(supports))[-3:],
            "resistance": sorted(set(resistances))[:3],
            "current_position": position,
        }


class RiskAlertService:
    """风险预警服务 - 多维预警."""

    def __init__(
        self,
        market_provider: MarketDataProvider,
        indicator_provider: IndicatorProvider | None = None,
    ):
        self._market = market_provider
        self._indicators = indicator_provider

    # ... (rest of methods)

class StopLossTakeProfitCalculator:
    """止盈止损建议计算器."""
    # ... (methods)

    def analyze_watchlist(
        self,
        symbols: List[str],
        market: MarketCode = MarketCode.CN,
    ) -> WatchlistRiskReportDTO:
        """分析自选股列表的风险状况."""
        alerts = []
        summary = RiskLevel(high_risk=0, medium_risk=0, low_risk=0, opportunities=0)

        for symbol in symbols:
            alert = self._analyze_symbol(symbol, market)
            if alert:
                alerts.append(alert)
                if alert.risk_level == "high":
                    summary.high_risk += 1
                elif alert.risk_level == "medium":
                    summary.medium_risk += 1
                else:
                    summary.low_risk += 1
                
                if alert.signal == "opportunity":
                    summary.opportunities += 1

        return WatchlistRiskReportDTO(
            symbols_analyzed=len(symbols),
            alerts_count=len(alerts),
            summary=summary,
            alerts=alerts,
        )

    def _analyze_symbol(
        self,
        symbol: str,
        market: MarketCode,
    ) -> RiskAlertDTO | None:
        """分析单只股票的风险状况."""
        try:
            profile = self._market.get_stock_profile(symbol, market)
            if not profile: return None

            price = float(profile.get("price", 0) or 0)
            if price <= 0: return None

            history = self._market.get_stock_history(symbol, market, "2023-01-01", datetime.now().strftime("%Y-%m-%d"))
            levels = SupportResistanceCalculator.calculate_levels(history, price)
            indicators = self._indicators.calculate(history) if self._indicators and history else {}

            return self._generate_alert(symbol, profile, price, levels, indicators)
        except Exception:
            return None

    def _generate_alert(self, symbol: str, profile: dict, price: float, levels: dict, indicators: dict) -> RiskAlertDTO:
        """生成标准化风险预警 DTO."""
        name = profile.get("name", symbol)
        change_pct = float(profile.get("change_pct", 0) or 0)
        
        # 简化版预警逻辑
        risk_level = "low"
        signal = "hold"
        
        return RiskAlertDTO(
            symbol=symbol,
            name=name,
            risk_level=risk_level,
            signal=signal,
            message="正常",
            support_levels=levels.get("support", []),
            resistance_levels=levels.get("resistance", []),
            current_position=levels.get("current_position", "unknown")
        )
