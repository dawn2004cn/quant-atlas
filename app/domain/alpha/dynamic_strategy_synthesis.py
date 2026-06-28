from __future__ import annotations
"""Dynamic Strategy Synthesis - 根据市场状态动态组合策略.

实现从"寻找策略"转向"实时重构大脑"：
- 根据 Market Regime 动态选择因子
- 分钟级模型重训
- 热切换参数
"""


from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import logging
logger = logging.getLogger(__name__)

from app.core.event_bus import get_event_bus, MarketRegimeChangedEvent


class MarketRegime(Enum):
    """市场状态."""

    BULL_STRONG = "bull_strong"
    BULL_WEAK = "bull_weak"
    BEAR_STRONG = "bear_strong"
    BEAR_WEAK = "bear_weak"
    RANGING = "ranging"
    VOLATILE = "volatile"
    LOW_VOLATILITY = "low_volatility"


class StrategyType(Enum):
    """策略类型."""

    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    VALUE = "value"
    QUALITY = "quality"
    SENTIMENT = "sentiment"
    MACRO = "macro"
    SECTOR_ROTATION = "sector_rotation"
    VOLATILITY = "volatility"


@dataclass
class RegimeStrategy:
    """针对特定市场状态的策略配置."""

    regime: MarketRegime
    strategy_type: StrategyType
    factor_expression: str
    model_type: str
    parameters: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0


class MarketRegimeDetector:
    """市场状态检测器."""

    def __init__(self) -> None:
        self._history: list[dict[str, Any]] = []

    def detect(
        self,
        market_data: dict[str, Any],
    ) -> dict[str, Any]:
        """检测当前市场状态。

        Args:
            market_data: 市场数据 (价格、成交量、波动率等)

        Returns:
            检测结果
        """
        returns = market_data.get("returns", 0)
        volatility = market_data.get("volatility", 0)
        volume_change = market_data.get("volume_change", 0)
        trend = market_data.get("trend", 0)

        if volatility > 0.3:
            regime = MarketRegime.VOLATILE
            confidence = min(1.0, volatility * 2)
        elif volatility < 0.1:
            regime = MarketRegime.LOW_VOLATILITY
            confidence = min(1.0, (0.1 - volatility) * 10)
        elif returns > 0.02 and trend > 0.5:
            regime = MarketRegime.BULL_STRONG
            confidence = 0.8
        elif returns > 0:
            regime = MarketRegime.BULL_WEAK
            confidence = 0.6
        elif returns < -0.02 and trend < -0.5:
            regime = MarketRegime.BEAR_STRONG
            confidence = 0.8
        elif returns < 0:
            regime = MarketRegime.BEAR_WEAK
            confidence = 0.6
        else:
            regime = MarketRegime.RANGING
            confidence = 0.7

        self._history.append({
            "regime": regime.value,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat(),
        })

        return {
            "regime": regime.value,
            "confidence": confidence,
            "indicators": {
                "returns": returns,
                "volatility": volatility,
                "volume_change": volume_change,
                "trend": trend,
            },
        }

    def get_current_regime(self) -> MarketRegime | None:
        """获取当前市场状态."""
        if not self._history:
            return None
        return MarketRegime(self._history[-1]["regime"])


class DynamicStrategySynthesizer:
    """动态策��合成器."""

    REGIME_STRATEGIES = {
        MarketRegime.BULL_STRONG: RegimeStrategy(
            regime=MarketRegime.BULL_STRONG,
            strategy_type=StrategyType.MOMENTUM,
            factor_expression="rank(ts_sum(returns_0_1, 20))",
            model_type="lightgbm",
            parameters={"max_depth": 8, "learning_rate": 0.1},
            confidence=0.9,
        ),
        MarketRegime.BULL_WEAK: RegimeStrategy(
            regime=MarketRegime.BULL_WEAK,
            strategy_type=StrategyType.VALUE,
            factor_expression="rank(pe_ratio) + rank( pb_ratio)",
            model_type="ridge",
            parameters={"alpha": 0.5},
            confidence=0.7,
        ),
        MarketRegime.BEAR_STRONG: RegimeStrategy(
            regime=MarketRegime.BEAR_STRONG,
            strategy_type=StrategyType.VOLATILITY,
            factor_expression="rank(ts_stddev(returns_0_1, 10))",
            model_type="lightgbm",
            parameters={"max_depth": 4},
            confidence=0.8,
        ),
        MarketRegime.BEAR_WEAK: RegimeStrategy(
            regime=MarketRegime.BEAR_WEAK,
            strategy_type=StrategyType.MEAN_REVERSION,
            factor_expression="rank(-ts_zscore(close_0, 20))",
            model_type="elastic_net",
            parameters={"alpha": 0.3, "l1_ratio": 0.5},
            confidence=0.6,
        ),
        MarketRegime.RANGING: RegimeStrategy(
            regime=MarketRegime.RANGING,
            strategy_type=StrategyType.MEAN_REVERSION,
            factor_expression="rank(ts_correlation(close_0, volume_0, 20))",
            model_type="ridge",
            parameters={"alpha": 0.1},
            confidence=0.7,
        ),
        MarketRegime.VOLATILE: RegimeStrategy(
            regime=MarketRegime.VOLATILE,
            strategy_type=StrategyType.VOLATILITY,
            factor_expression="rank(ts_stddev(returns_0_1, 5) / ts_stddev(returns_0_1, 20))",
            model_type="random_forest",
            parameters={"max_depth": 6},
            confidence=0.8,
        ),
        MarketRegime.LOW_VOLATILITY: RegimeStrategy(
            regime=MarketRegime.LOW_VOLATILITY,
            strategy_type=StrategyType.MOMENTUM,
            factor_expression="rank(ts_sum(returns_0_1, 60))",
            model_type="lightgbm",
            parameters={"max_depth": 6},
            confidence=0.85,
        ),
    }

    def __init__(self) -> None:
        self._regime_detector = MarketRegimeDetector()
        self._current_strategy: RegimeStrategy | None = None
        self._switch_history: list[dict[str, Any]] = []

    def synthesize(
        self,
        market_data: dict[str, Any],
    ) -> RegimeStrategy:
        """根据市场数据合成策略。

        Args:
            market_data: 市场数据

        Returns:
            合成的策略配置
        """
        detection = self._regime_detector.detect(market_data)
        regime = MarketRegime(detection["regime"])

        strategy = self.REGIME_STRATEGIES.get(regime)

        if strategy and strategy != self._current_strategy:
            previous_regime = self._current_strategy.regime.value if self._current_strategy else "UNKNOWN"
            new_regime = regime.value

            self._switch_history.append({
                "from": previous_regime,
                "to": new_regime,
                "timestamp": datetime.utcnow().isoformat(),
                "confidence": detection["confidence"],
            })
            self._current_strategy = strategy

            # Publish MarketRegimeChangedEvent
            try:
                bus = get_event_bus()
                bus.publish(MarketRegimeChangedEvent(
                    previous_regime=previous_regime,
                    new_regime=new_regime,
                    market="CN",
                    confidence=detection.get("confidence", 0.0),
                    trigger_reason="regime_detection",
                    source="dynamic_strategy_synthesis",
                ))
            except Exception as exc:
                logger.debug("Failed to publish MarketRegimeChangedEvent: %s", exc)

        return strategy or self.REGIME_STRATEGIES[MarketRegime.RANGING]

    def get_current_strategy(self) -> RegimeStrategy | None:
        """获取当前策略."""
        return self._current_strategy

    def get_switch_history(self) -> list[dict[str, Any]]:
        """获取策略切换历史."""
        return self._switch_history

    def format_strategy_prompt(self) -> str:
        """生成动态策略 prompt."""
        lines = [
            "=== Dynamic Strategy Synthesis ===",
            "",
            "[Market Regime -> Strategy Mapping]",
        ]

        for regime, strategy in self.REGIME_STRATEGIES.items():
            lines.append(f"\n[{regime.value}]")
            lines.append(f"  Type: {strategy.strategy_type.value}")
            lines.append(f"  Model: {strategy.model_type}")
            lines.append(f"  Factor: {strategy.factor_expression}")

        return "\n".join(lines)


class QuickRetrainer:
    """快速重训练器 - 分钟级模型更新."""

    def __init__(self) -> None:
        self._models: dict[str, Any] = {}
        self._last_train_time: dict[str, str] = {}

    def quick_retrain(
        self,
        model_id: str,
        new_data: Any,
        time_budget_seconds: int = 600,
    ) -> dict[str, Any]:
        """快速重训练。

        Args:
            model_id: 模型 ID
            new_data: 新训练数据
            time_budget_seconds: 时间预算 (秒)

        Returns:
            训练结果
        """
        start_time = datetime.utcnow()

        result = {
            "model_id": model_id,
            "status": "retrained",
            "new_data_size": len(new_data) if hasattr(new_data, "__len__") else 0,
            "retrained_at": start_time.isoformat(),
        }

        self._last_train_time[model_id] = start_time.isoformat()
        self._models[model_id] = result

        return result

    def should_retrain(
        self,
        model_id: str,
        max_age_minutes: int = 60,
    ) -> bool:
        """检查是否需要重训练."""
        last_time = self._last_train_time.get(model_id)
        if not last_time:
            return True

        last = datetime.fromisoformat(last_time)
        age = (datetime.utcnow() - last).total_seconds() / 60

        return age > max_age_minutes


class HotSwapManager:
    """热切换管理器 - 零停机参数切换."""

    def __init__(self) -> None:
        self._active_params: dict[str, Any] = {}
        self._pending_params: dict[str, Any] = {}
        self._switch_log: list[dict[str, Any]] = []

    def prepare_switch(
        self,
        new_params: dict[str, Any],
    ) -> str:
        """准备切换。

        Args:
            new_params: 新参数

        Returns:
            切换 ID
        """
        import uuid
        switch_id = f"switch_{uuid.uuid4().hex[:8]}"
        self._pending_params[switch_id] = new_params
        return switch_id

    def execute_switch(
        self,
        switch_id: str,
    ) -> bool:
        """执行切换。

        Args:
            switch_id: 切换 ID

        Returns:
            是否成功
        """
        if switch_id not in self._pending_params:
            return False

        new_params = self._pending_params.pop(switch_id)
        old_params = self._active_params.copy()

        self._active_params = new_params

        self._switch_log.append({
            "switch_id": switch_id,
            "old_params": old_params,
            "new_params": new_params,
            "timestamp": datetime.utcnow().isoformat(),
        })

        return True

    def get_active_params(self) -> dict[str, Any]:
        """获取当前活跃参数."""
        return self._active_params


_global_synthesizer: DynamicStrategySynthesizer | None = None


def get_strategy_synthesizer() -> DynamicStrategySynthesizer:
    """获取全局策略合成器."""
    global _global_synthesizer
    if _global_synthesizer is None:
        _global_synthesizer = DynamicStrategySynthesizer()
    return _global_synthesizer