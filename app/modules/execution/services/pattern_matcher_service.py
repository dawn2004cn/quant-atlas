from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Pattern Matcher - 历史相似度匹配服务."""


from datetime import datetime, timedelta
from typing import Any

import numpy as np

from app.domain.enums import MarketCode
from app.domain.ports import MarketDataProvider


class PatternMatcherService:
    """历史相似度匹配服务."""

    def __init__(
        self,
        market_provider: MarketDataProvider | None = None,
    ):
        self._market = market_provider

    def find_similar_patterns(
        self,
        symbol: str,
        market: MarketCode = MarketCode.CN,
        lookback_days: int = 60,
        match_count: int = 5,
    ) -> GenericResponseDTO:
        """在历史K线中寻找相似走势."""
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=lookback_days * 2)).strftime("%Y-%m-%d")

        history = self._market.get_stock_history(symbol, market, start, end) if self._market else []

        if not history or len(history) < 40:
            return {
                "ok": False,
                "error": "数据不足",
            }

        # 计算当前走势向量
        current_prices = [h.get("close", 0) for h in history[-30:] if h.get("close", 0) > 0]
        if len(current_prices) < 20:
            return {
                "ok": False,
                "error": "近期数据不足",
            }

        current_returns = self._calculate_returns(current_prices)

        # 在历史窗口中滑动搜索
        best_matches = []
        for i in range(len(history) - 30):
            hist_prices = [h.get("close", 0) for h in history[i:i+30] if h.get("close", 0) > 0]
            if len(hist_prices) < 20:
                continue

            hist_returns = self._calculate_returns(hist_prices)
            similarity = self._calculate_similarity(current_returns, hist_returns)

            if similarity > 0.85:
                date_start = history[i].get("date", "")
                best_matches.append({
                    "date": date_start,
                    "similarity": round(similarity * 100, 1),
                    "future_5d_return": self._get_future_return(history, i, 5),
                    "future_20d_return": self._get_future_return(history, i, 20),
                })

        best_matches.sort(key=lambda x: x["similarity"], reverse=True)
        best_matches = best_matches[:match_count]

        if not best_matches:
            return {
                "ok": True,
                "symbol": symbol,
                "matches": [],
                "message": "未找到高度相似的历史走势",
            }

        # 计算统计
        avg_5d = np.mean([m["future_5d_return"] for m in best_matches])
        avg_20d = np.mean([m["future_20d_return"] for m in best_matches])

        return {
            "ok": True,
            "symbol": symbol,
            "current_pattern": "相似于30日周期",
            "matches": best_matches,
            "statistics": {
                "avg_5d_return": round(avg_5d, 2),
                "avg_20d_return": round(avg_20d, 2),
                "win_rate_5d": len([m for m in best_matches if m["future_5d_return"] > 0]) / len(best_matches),
                "win_rate_20d": len([m for m in best_matches if m["future_20d_return"] > 0]) / len(best_matches),
            },
            "ai_insight": self._generate_insight(avg_5d, avg_20d),
        }

    def _calculate_returns(self, prices: list[float]) -> list[float]:
        """计算收益率序列."""
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                returns.append((prices[i] - prices[i-1]) / prices[i-1])
        return returns

    def _calculate_similarity(
        self,
        returns1: list[float],
        returns2: list[float],
    ) -> float:
        """计算两条收益率序列的相似度(余弦相似度)."""
        min_len = min(len(returns1), len(returns2))
        if min_len < 10:
            return 0

        r1 = np.array(returns1[:min_len])
        r2 = np.array(returns2[:min_len])

        dot = np.dot(r1, r2)
        norm1 = np.linalg.norm(r1)
        norm2 = np.linalg.norm(r2)

        if norm1 == 0 or norm2 == 0:
            return 0

        return dot / (norm1 * norm2)

    def _get_future_return(
        self,
        history: list[dict],
        start_idx: int,
        days: int,
    ) -> float:
        """计算未来N天收益率."""
        if start_idx + days >= len(history):
            return 0

        start_price = history[start_idx].get("close", 0)
        end_price = history[start_idx + days].get("close", 0) if start_idx + days < len(history) else history[-1].get("close", 0)

        if start_price <= 0:
            return 0

        return (end_price - start_price) / start_price * 100

    def _generate_insight(self, avg_5d: float, avg_20d: float) -> str:
        """生成AI洞察."""
        if avg_5d > 3:
            return f"历史相似走势显示，后续5天平均上涨 {avg_5d:.1f}%，具备短期反弹潜力。"
        elif avg_5d < -2:
            return f"历史相似走势显示，后续5天平均下跌 {abs(avg_5d):.1f}%，需注意短期风险。"
        else:
            return "历史数据显示未来走势不确定性较大，建议观望。"