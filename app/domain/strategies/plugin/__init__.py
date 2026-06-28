"""Strategy Plugin System - 策略插件化引擎。

提供策略的热插拔生命周期管理:
- StrategyPlugin: 策略插件接口
- StrategyRegistry: 策略注册中心
- StrategyEngine: 策略引擎
- StrategyLoader: 动态加载器
"""

from .engine import EngineConfig, EngineStats, StrategyEngine
from .loader import PluginDiscovery, StrategyLoader
from .protocol import (
    BaseStrategyPlugin,
    PluginConfig,
    PluginMetadata,
    PluginState,
    StrategyPlugin,
    StrategyResult,
    StrategySignal,
)
from .registry import StrategyRegistry

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
