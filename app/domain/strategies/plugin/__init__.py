"""Strategy Plugin System - 策略插件化引擎。

提供策略的热插拔生命周期管理:
- StrategyPlugin: 策略插件接口
- StrategyRegistry: 策略注册中心
- StrategyEngine: 策略引擎
- StrategyLoader: 动态加载器
"""

from .protocol import (
    StrategyPlugin,
    PluginMetadata,
    PluginState,
    PluginConfig,
    StrategySignal,
    StrategyResult,
    BaseStrategyPlugin,
)
from .registry import StrategyRegistry
from .engine import StrategyEngine, EngineConfig, EngineStats
from .loader import StrategyLoader, PluginDiscovery

__all__ = [
    "StrategyPlugin",
    "PluginMetadata",
    "PluginState",
    "PluginConfig",
    "StrategySignal",
    "StrategyResult",
    "BaseStrategyPlugin",
    "StrategyRegistry",
    "StrategyEngine",
    "EngineConfig",
    "EngineStats",
    "StrategyLoader",
    "PluginDiscovery",
]
