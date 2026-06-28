from __future__ import annotations

from typing import Any

from ..sniper_entities import MarketRegime


class MarketRegimeManager:
    """判定当前市场处于牛市、熊市还是震荡市。"""

    def __init__(self, market_service: Any):
        self._market = market_service

    def get_market_regime(self) -> MarketRegime:
        """根据上证指数/沪深300 的均线系统简单判定。"""
        try:
            # 这里应通过 market_service 获取指数行情
            # 示例逻辑：简单返回震荡，实际可接入均线判定
            return MarketRegime.SIDEWAYS
        except Exception:
            return MarketRegime.SIDEWAYS
