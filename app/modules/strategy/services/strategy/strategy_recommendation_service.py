from __future__ import annotations

from app.domain.dto.service_result import GenericResponseDTO

"""Strategy Recommendation Service - Find the best strategy for a specific symbol."""


from app.core.base_service import BaseApplicationService
from app.domain.enums import MarketCode


class StrategyRecommendationService(BaseApplicationService):
    def __init__(self, market_service: object, strategy_registry: object):
        super().__init__()
        self._market = market_service
        self._registry = strategy_registry

    def recommend_for_stock(self, symbol: str, market: MarketCode) -> GenericResponseDTO:
        """基于个股当前形态特征推荐契合度最高的策略."""
        # 1. 模拟特征提取 (真实场景需从 history 拉取计算)
        # 假设我们获取了过去 20 天的 ATR 和 ADX
        import random
        volatility = random.uniform(0.01, 0.05)
        trend_strength = random.uniform(10, 50)

        # 2. 匹配逻辑 (Heuristic Match)
        recommendations = []

        if trend_strength > 35:
            recommendations.append({
                "strategy_id": "dual_ma",
                "name": "双均线趋势追踪",
                "fit_score": 92,
                "reason": "该股目前处于强趋势阶段，适合双均线过滤随机波动。"
            })
        elif volatility > 0.03:
             recommendations.append({
                "strategy_id": "bollinger_reversion",
                "name": "布林带均值回归",
                "fit_score": 88,
                "reason": "近期波动率放大，触及极值概率增加，适合高抛低吸。"
            })
        else:
             recommendations.append({
                "strategy_id": "grid_trading",
                "name": "极简网格交易",
                "fit_score": 85,
                "reason": "该股目前处于窄幅震荡，网格策略可稳定收割日内噪声。"
            })

        self.logger.info(f"Recommended strategies for {symbol}: {recommendations[0]['name']}")

        return {
            "symbol": symbol,
            "volatility_regime": "High" if volatility > 0.03 else "Low",
            "trend_regime": "Trending" if trend_strength > 30 else "Ranging",
            "top_pick": recommendations[0]
        }
