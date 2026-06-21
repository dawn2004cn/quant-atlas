from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Visual Data Reducer - 可视化数据降维服务.

将复杂的财务报表和K线指标转换为直观易懂的红黄绿三色灯显示，
并提供技术指标共振计功能."""


from datetime import datetime
from typing import Any

from app.domain.enums import MarketCode
from app.domain.ports import MarketDataProvider, IndicatorProvider


import logging
logger = logging.getLogger(__name__)
class FinancialTrafficLight:
    """财务三色灯 - 将关键财务指标转换为红黄绿颜色."""

    THRESHOLDS = {
        "debt_ratio": {"good": 30, "warning": 60},  # 资产负债率
        "profit_growth": {"good": 20, "warning": 0},  # 利润增长率
        "cash_flow": {"good": 0, "warning": -10},  # 经营现金流
        "roe": {"good": 15, "warning": 8},  # ROE
        "gross_margin": {"good": 30, "warning": 15},  # 毛利率
    }

    @classmethod
    def evaluate(
        cls,
        fundamentals: dict[str, Any],
    ) -> GenericResponseDTO:
        """评估财务健康度并返回三色灯结果."""
        results = {}

        # 资产负债率
        debt_ratio = fundamentals.get("debt_ratio", 100)
        if debt_ratio is None:
            debt_ratio = 100
        if debt_ratio < cls.THRESHOLDS["debt_ratio"]["good"]:
            results["debt_ratio"] = {"value": debt_ratio, "status": "green", "label": "低负债"}
        elif debt_ratio < cls.THRESHOLDS["debt_ratio"]["warning"]:
            results["debt_ratio"] = {"value": debt_ratio, "status": "yellow", "label": "中等负债"}
        else:
            results["debt_ratio"] = {"value": debt_ratio, "status": "red", "label": "高负债"}

        # 利润增长
        profit_growth = fundamentals.get("profit_growth", -100)
        if profit_growth >= cls.THRESHOLDS["profit_growth"]["good"]:
            results["profit_growth"] = {"value": profit_growth, "status": "green", "label": "高增长"}
        elif profit_growth >= cls.THRESHOLDS["profit_growth"]["warning"]:
            results["profit_growth"] = {"value": profit_growth, "status": "yellow", "label": "低速增长"}
        else:
            results["profit_growth"] = {"value": profit_growth, "status": "red", "label": "负增长"}

        # 经营现金流
        cash_flow = fundamentals.get("cash_flow", -999)
        if cash_flow >= cls.THRESHOLDS["cash_flow"]["good"]:
            results["cash_flow"] = {"value": cash_flow, "status": "green", "label": "现金流充裕"}
        elif cash_flow >= cls.THRESHOLDS["cash_flow"]["warning"]:
            results["cash_flow"] = {"value": cash_flow, "status": "yellow", "label": "现金流一般"}
        else:
            results["cash_flow"] = {"value": cash_flow, "status": "red", "label": "现金流紧张"}

        # ROE
        roe = fundamentals.get("roe", 0)
        if roe >= cls.THRESHOLDS["roe"]["good"]:
            results["roe"] = {"value": roe, "status": "green", "label": "高ROE"}
        elif roe >= cls.THRESHOLDS["roe"]["warning"]:
            results["roe"] = {"value": roe, "status": "yellow", "label": "中等ROE"}
        else:
            results["roe"] = {"value": roe, "status": "red", "label": "低ROE"}

        # 毛利率
        gross_margin = fundamentals.get("gross_margin", 0)
        if gross_margin >= cls.THRESHOLDS["gross_margin"]["good"]:
            results["gross_margin"] = {"value": gross_margin, "status": "green", "label": "高毛利"}
        elif gross_margin >= cls.THRESHOLDS["gross_margin"]["warning"]:
            results["gross_margin"] = {"value": gross_margin, "status": "yellow", "label": "中等毛利"}
        else:
            results["gross_margin"] = {"value": gross_margin, "status": "red", "label": "低毛利"}

        # 综合评分
        green_count = sum(1 for v in results.values() if v["status"] == "green")
        if green_count >= 4:
            overall = "green"
        elif green_count >= 2:
            overall = "yellow"
        else:
            overall = "red"

        results["_overall"] = overall
        return results


class TechnicalResonanceMeter:
    """技术指标共振计 - 汇总多个技术指标信号."""

    def __init__(self, indicator_provider: IndicatorProvider | None = None):
        self._indicators = indicator_provider

    def calculate_resonance(
        self,
        history: list[dict],
    ) -> GenericResponseDTO:
        """计算技术指标共振分数."""
        if not history or len(history) < 30:
            return {
                "ok": False,
                "error": "数据不足",
                "resonance_score": 0,
                "signal": "unknown",
                "details": [],
            }

        indicators = {}
        if self._indicators:
            try:
                indicators = self._indicators.calculate(history)
            except Exception as e:
                logger.warning("visual_data_reducer_service.py.calculate_resonance: %s", e)

        signals = []

        # RSI 信号
        rsi = indicators.get("rsi", 50)
        if rsi:
            if rsi < 30:
                signals.append({"indicator": "RSI", "value": rsi, "signal": "buy", "weight": 1.0})
            elif rsi > 70:
                signals.append({"indicator": "RSI", "value": rsi, "signal": "sell", "weight": 1.0})
            else:
                signals.append({"indicator": "RSI", "value": rsi, "signal": "neutral", "weight": 0.5})

        # MACD 信号
        macd = indicators.get("macd", 0)
        macd_signal = indicators.get("macd_signal", 0)
        if macd and macd_signal:
            if macd > macd_signal:
                signals.append({"indicator": "MACD", "value": macd, "signal": "buy", "weight": 1.0})
            elif macd < macd_signal:
                signals.append({"indicator": "MACD", "value": macd, "signal": "sell", "weight": 1.0})
            else:
                signals.append({"indicator": "MACD", "value": macd, "signal": "neutral", "weight": 0.5})

        # KD 指标
        k = indicators.get("k", 50)
        d = indicators.get("d", 50)
        if k and d:
            if k < 20 and d < 20:
                signals.append({"indicator": "KD", "value": f"k={k:.0f}", "signal": "buy", "weight": 1.0})
            elif k > 80 and d > 80:
                signals.append({"indicator": "KD", "value": f"k={k:.0f}", "signal": "sell", "weight": 1.0})
            elif k > d:
                signals.append({"indicator": "KD", "value": f"k={k:.0f},d={d:.0f}", "signal": "buy", "weight": 0.8})
            else:
                signals.append({"indicator": "KD", "value": f"k={k:.0f},d={d:.0f}", "signal": "sell", "weight": 0.8})

        # 均线信号
        ma5 = indicators.get("ma5")
        ma10 = indicators.get("ma10")
        ma20 = indicators.get("ma20")
        if ma5 and ma20:
            if ma5 > ma20:
                signals.append({"indicator": "MA", "value": "5日线上穿20日线", "signal": "buy", "weight": 0.8})
            else:
                signals.append({"indicator": "MA", "value": "5日线下穿20日线", "signal": "sell", "weight": 0.8})

        # BOLL 信号
        boll_upper = indicators.get("boll_upper")
        boll_lower = indicators.get("boll_lower")
        close_prices = [h.get("close", 0) for h in history if h.get("close", 0) > 0]
        if boll_upper and boll_lower and close_prices:
            current = close_prices[-1]
            if current < boll_lower:
                signals.append({"indicator": "BOLL", "value": "触及下轨", "signal": "buy", "weight": 0.8})
            elif current > boll_upper:
                signals.append({"indicator": "BOLL", "value": "触及上轨", "signal": "sell", "weight": 0.8})

        # 计算共振分数
        buy_score = sum(s["weight"] for s in signals if s["signal"] == "buy")
        sell_score = sum(s["weight"] for s in signals if s["signal"] == "sell")
        total = buy_score + sell_score

        if total > 0:
            resonance_score = buy_score / total
        else:
            resonance_score = 0.5

        # 确定信号
        if resonance_score >= 0.7:
            signal = "strong_buy"
            signal_label = "强烈买入"
        elif resonance_score >= 0.55:
            signal = "buy"
            signal_label = "买入"
        elif resonance_score <= 0.3:
            signal = "strong_sell"
            signal_label = "强烈卖出"
        elif resonance_score <= 0.45:
            signal = "sell"
            signal_label = "卖出"
        else:
            signal = "neutral"
            signal_label = "观望"

        return {
            "ok": True,
            "resonance_score": round(resonance_score * 100, 1),
            "signal": signal,
            "signal_label": signal_label,
            "buy_signals": len([s for s in signals if s["signal"] == "buy"]),
            "sell_signals": len([s for s in signals if s["signal"] == "sell"]),
            "details": signals,
        }


class VisualDataReducerService:
    """可视化数据降维服务 - 综合财务和技术面."""

    def __init__(
        self,
        market_provider: MarketDataProvider,
        indicator_provider: IndicatorProvider | None = None,
        fundamental_provider: Any | None = None,
    ):
        self._market = market_provider
        self._indicators = indicator_provider
        self._fundamental = fundamental_provider

    def reduce(
        self,
        symbol: str,
        market: MarketCode = MarketCode.CN,
    ) -> GenericResponseDTO:
        """对个股数据进行可视化降维处理."""
        # 获取基础数据
        profile = self._market.get_stock_profile(symbol, market)
        if not profile:
            return {"ok": False, "error": "股票不存在"}

        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now().replace(month=datetime.now().month - 3)).strftime("%Y-%m-%d")
        history = self._market.get_stock_history(symbol, market, start, end)

        # 获取财务数据
        fundamentals = {}
        if self._fundamental:
            try:
                fundamentals = self._fundamental.get_fundamentals(symbol, market)
            except Exception as e:
                logger.warning("visual_data_reducer_service.py.reduce: %s", e)

        # 财务三色灯
        traffic_light = FinancialTrafficLight.evaluate(fundamentals)

        # 技术指标共振
        resonance = TechnicalResonanceMeter(self._indicators).calculate_resonance(history)

        # 组合结果
        price = float(profile.get("price", 0) or 0)
        change_pct = float(profile.get("change_pct", 0) or 0)

        return {
            "ok": True,
            "symbol": symbol,
            "name": profile.get("name", symbol),
            "price": price,
            "change_pct": round(change_pct, 2),
            "generated_at": datetime.now().isoformat(),
            "financial_lights": traffic_light,
            "technical_resonance": resonance,
            "overall_signal": self._calculate_overall_signal(
                financial=traffic_light.get("_overall"),
                technical=resonance.get("signal"),
            ),
        }

    def _calculate_overall_signal(
        self,
        financial: str,
        technical: str,
    ) -> GenericResponseDTO:
        """计算综合信号."""
        # 权重：技术面60%，财务面40%
        score = 0

        if technical in ["strong_buy", "buy"]:
            score += 0.6
        elif technical in ["strong_sell", "sell"]:
            score -= 0.6

        if financial == "green":
            score += 0.4
        elif financial == "red":
            score -= 0.4

        if score >= 0.5:
            return {"signal": "buy", "label": "建议买入", "score": round(score, 2)}
        elif score <= -0.3:
            return {"signal": "sell", "label": "建议卖出", "score": round(score, 2)}
        else:
            return {"signal": "hold", "label": "继续观望", "score": round(score, 2)}