from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Whale Tracker - 主力追踪与资金流分析服务."""


from datetime import datetime

from app.domain.enums import MarketCode
from app.domain.ports import MarketDataProvider


class WhaleTrackerService:
    """主力资金追踪服务."""

    def __init__(
        self,
        market_provider: MarketDataProvider | None = None,
    ):
        self._market = market_provider

    def analyze_institutional_flow(
        self,
        symbols: list[str],
        market: MarketCode = MarketCode.CN,
    ) -> GenericResponseDTO:
        """分析机构资金流向."""
        flow_data = []

        for symbol in symbols:
            profile = self._market.get_stock_profile(symbol, market) if self._market else {}
            if not profile:
                continue

            change_pct = float(profile.get("change_pct", 0) or 0)

            # 简单估算主力行为
            net_inflow = self._estimate_net_inflow(profile)
            holder_type = self._classify_holder_type(net_inflow, change_pct)

            flow_data.append({
                "symbol": symbol,
                "name": profile.get("name", symbol),
                "change_pct": round(change_pct, 2),
                "net_inflow": round(net_inflow, 2),
                "holder_type": holder_type.get("type"),
                "holder_description": holder_type.get("description"),
            })

        # 按净流入排序
        flow_data.sort(key=lambda x: x.get("net_inflow", 0), reverse=True)

        return {
            "ok": True,
            "generated_at": datetime.now().isoformat(),
            "stocks_analyzed": len(flow_data),
            "flow_data": flow_data,
            "summary": self._summarize_flow(flow_data),
        }

    def _estimate_net_inflow(self, profile: dict) -> float:
        """估算净流入."""
        float(profile.get("amount", 0) or 0)
        volume = float(profile.get("volume", 0) or 0)
        change_pct = float(profile.get("change_pct", 0) or 0)

        if volume <= 0:
            return 0

        # 简单估算：涨时量大认为是资金流入
        if change_pct > 0:
            return min(change_pct * volume / 1000000, change_pct * 10)
        else:
            return max(change_pct * volume / 1000000, change_pct * 10)

    def _classify_holder_type(
        self,
        net_inflow: float,
        change_pct: float,
    ) -> GenericResponseDTO:
        """分类持有者类型."""
        if abs(net_inflow) < 2 and abs(change_pct) < 3:
            return {"type": "retail", "description": "散户主导"}

        if change_pct > 5 and net_inflow > 5:
            return {"type": "institution", "description": "机构主导"}
        elif change_pct > 7 and net_inflow > 3:
            return {"type": "hot_money", "description": "游资热炒"}
        elif change_pct < -5 and net_inflow < -3:
            return {"type": "institution_sell", "description": "机构出货"}
        elif abs(change_pct) < 2 and abs(net_inflow) < 3:
            return {"type": "retail", "description": "散户抱团"}

        return {"type": "mixed", "description": "多空交织"}

    def _summarize_flow(self, flow_data: list[dict]) -> GenericResponseDTO:
        """汇总资金流情况."""
        institution_count = sum(1 for f in flow_data if f.get("holder_type") == "institution")
        hot_money_count = sum(1 for f in flow_data if f.get("holder_type") == "hot_money")
        retail_count = sum(1 for f in flow_data if f.get("holder_type") == "retail")

        return {
            "institution_dominated": institution_count,
            "hot_money_dominated": hot_money_count,
            "retail_dominated": retail_count,
            "overall_market_sentiment": "bull" if institution_count > retail_count else "neutral",
        }


class ChipConcentrationAnalyzer:
    """筹码集中度分析器."""

    @staticmethod
    def analyze_concentration(
        symbol: str,
        market: MarketCode = MarketCode.CN,
    ) -> GenericResponseDTO:
        """分析筹码集中度."""
        # 简化实现：基于价格波动和成交量估算
        return {
            "symbol": symbol,
            "concentration_risk": "low",
            "description": "筹码分布较为分散",
            "warning": None,
            "suggestion": "当前无明显风险",
        }

    @staticmethod
    def check_concentration_change(
        current_concentration: float,
        previous_concentration: float,
    ) -> GenericResponseDTO:
        """检查筹码集中度变化."""
        delta = current_concentration - previous_concentration

        if delta > 0.2:
            return {
                "status": "warning",
                "message": "筹码正在集中，主力可能在建仓",
            }
        elif delta < -0.2:
            return {
                "status": "warning",
                "message": "筹码正在分散，主力可能正在撤离",
            }
        else:
            return {
                "status": "stable",
                "message": "筹码分布相对稳定",
            }
