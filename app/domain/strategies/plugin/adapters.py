from __future__ import annotations
"""Strategy Adapter - 现有策略适配器。

将现有 BaseStrategy 转换为插件模式:
- MACDStrategy -> MacdPlugin
- RSIStrategy -> RsiPlugin
"""


from typing import Any

from .protocol import (
    BaseStrategyPlugin,
    PluginConfig,
    PluginMetadata,
    StrategyResult,
)
from ..base import BaseStrategy


class StrategyAdapter(BaseStrategyPlugin):
    """策略适配器

    将现有 BaseStrategy 包装为 StrategyPlugin。
    """

    def __init__(
        self,
        strategy: BaseStrategy,
        metadata: PluginMetadata | None = None,
    ):
        super().__init__()
        self._strategy = strategy
        self._metadata = metadata or PluginMetadata(
            id=f"adapter_{strategy.name}",
            name=strategy.name,
            version="1.0.0",
            description=f"Adapter for {strategy.name}",
        )

    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata

    def on_load(self) -> bool:
        super().on_load()
        self._metadata.loaded_at = self._strategy.__class__.__module__
        return True

    def analyze(self, data: dict[str, Any]) -> StrategyResult:
        return self._strategy.analyze(data)

    def on_init(self, config: PluginConfig) -> bool:
        if not super().on_init(config):
            return False

        # 将配置参数传递给底层策略
        if config.params:
            self._strategy.params.update(config.params)

        return self._strategy.validate_params()

    def on_update(self, params: dict[str, Any]) -> bool:
        if not super().on_update(params):
            return False
        self._strategy.params.update(params)
        return True


class MacdPlugin(StrategyAdapter):
    """MACD 策略插件"""

    def __init__(self, params: dict | None = None):
        from ..base import MACDStrategy
        strategy = MACDStrategy(params)
        metadata = PluginMetadata(
            id="macd_crossover",
            name="MACD Crossover",
            version="1.0.0",
            author="Quant Atlas",
            description="MACD 金叉/死叉策略",
            tags=["trend", "oscillator", "classic"],
            entry_point="app.domain.strategies.base.MACDStrategy",
        )
        super().__init__(strategy, metadata)


class RsiPlugin(StrategyAdapter):
    """RSI 策略插件"""

    def __init__(self, params: dict | None = None):
        from ..base import RSIStrategy
        strategy = RSIStrategy(params)
        metadata = PluginMetadata(
            id="rsi_reversal",
            name="RSI Reversal",
            version="1.0.0",
            author="Quant Atlas",
            description="RSI 超买超卖策略",
            tags=["oscillator", "reversal"],
            entry_point="app.domain.strategies.base.RSIStrategy",
        )
        super().__init__(strategy, metadata)


class BreakoutPlugin(StrategyAdapter):
    """突破策略插件"""

    def __init__(self, params: dict | None = None):
        from ..base import BreakoutStrategy
        strategy = BreakoutStrategy(params)
        metadata = PluginMetadata(
            id="breakout",
            name="Breakout",
            version="1.0.0",
            author="Quant Atlas",
            description="价格突破策略",
            tags=["breakout", "momentum"],
            entry_point="app.domain.strategies.base.BreakoutStrategy",
        )
        super().__init__(strategy, metadata)


def create_adapter(strategy: BaseStrategy) -> StrategyAdapter:
    """创建策略适配器

    自动识别策略类型并创建对应的插件适配器。
    """
    name = strategy.name.lower()

    if "macd" in name:
        return MacdPlugin(strategy.params)
    elif "rsi" in name:
        return RsiPlugin(strategy.params)
    elif "breakout" in name:
        return BreakoutPlugin(strategy.params)
    else:
        # 通用适配器
        metadata = PluginMetadata(
            id=f"adapter_{id(strategy)}",
            name=strategy.name,
            version="1.0.0",
            description=f"Adapter for {strategy.name}",
        )
        return StrategyAdapter(strategy, metadata)
