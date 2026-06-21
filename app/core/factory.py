from __future__ import annotations
"""Strategy factory for dynamic instantiation."""


from typing import Any, Iterator, Type
from ..domain.entities import StrategyConfig
from .base_strategy import BaseTradingStrategy

from app.core.logger import get_logger

logger = get_logger(__name__)


class StrategyFactory:
    """Creates strategy instances based on configuration."""

    _registry: dict[str, Type[BaseTradingStrategy]] = {}

    @classmethod
    def register(cls, strategy_id: str, strategy_class: Type[BaseTradingStrategy]):
        cls._registry[strategy_id] = strategy_class

    @classmethod
    def create(cls, config: StrategyConfig) -> BaseTradingStrategy | None:
        """Instantiate a strategy with given parameters."""
        strategy_class = cls._registry.get(config.strategy_id)
        if not strategy_class:
            return None
        
        try:
            # 使用配置中的参数进行实例化
            return strategy_class(**config.parameters)
        except Exception as e:
            logger.warning(
                "Failed to create strategy %s: %s",
                config.strategy_id,
                e,
                exc_info=True,
            )
            # 回退到默认实例化
            return strategy_class()

    @classmethod
    def get_registered_ids(cls) -> list[str]:
        return list(cls._registry.keys())

    @classmethod
    def iter_registered_instances(cls) -> Iterator[tuple[str, BaseTradingStrategy]]:
        """遍历已注册策略 (strategy_id, 默认参数实例)，供信号扫描等批量逻辑使用。"""
        for strategy_id, strategy_class in cls._registry.items():
            cfg = StrategyConfig(strategy_id=strategy_id, parameters={})
            inst = cls.create(cfg)
            if inst is not None:
                yield strategy_id, inst
