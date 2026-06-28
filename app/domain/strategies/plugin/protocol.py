from __future__ import annotations
"""Strategy Plugin Protocol - 策略插件接口定义。

定义策略插件的标准接口，包括:
- 生命周期钩子
- 信号生成
- 配置管理
"""


import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class PluginState(str, Enum):
    """插件状态"""
    DISCOVERED = "discovered"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class PluginMetadata:
    """插件元数据"""
    id: str
    name: str
    version: str
    author: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    entry_point: str = ""
    loaded_at: datetime | None = None


@dataclass
class StrategySignal:
    """策略信号"""
    code: str
    direction: str  # long, short, close
    strength: float  # 0-1
    price: float = 0.0
    target_price: float | None = None
    stop_loss: float | None = None
    confidence: float = 50.0
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyResult:
    """策略执行结果"""
    signals: list[StrategySignal] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PluginConfig:
    """插件配置"""
    enabled: bool = True
    params: dict[str, Any] = field(default_factory=dict)
    risk_level: str = "medium"  # low, medium, high
    max_position: float = 1.0  # 0-1
    priority: int = 0


class StrategyPlugin(ABC):
    """策略插件抽象基类

    所有策略必须实现此接口以支持热插拔。
    """

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """返回插件元数据"""
        pass

    @abstractmethod
    def on_load(self) -> bool:
        """插件加载时调用"""
        pass

    @abstractmethod
    def on_unload(self) -> bool:
        """插件卸载时调用"""
        pass

    @abstractmethod
    def on_init(self, config: PluginConfig) -> bool:
        """插件初始化 (Setup)

        Args:
            config: 插件配置

        Returns:
            是否初始化成功
        """
        pass

    @abstractmethod
    def on_start(self) -> bool:
        """插件启动 (TearUp)"""
        pass

    @abstractmethod
    def on_stop(self) -> bool:
        """插件停止 (TearDown)"""
        pass

    @abstractmethod
    def on_update(self, params: dict[str, Any]) -> bool:
        """参数更新 (Hot Reload)

        Args:
            params: 新的参数字典

        Returns:
            是否更新成功
        """
        pass

    @abstractmethod
    def analyze(self, data: dict[str, Any]) -> StrategyResult:
        """分析数据并生成信号

        Args:
            data: 市场数据

        Returns:
            策略执行结果
        """
        pass

    def get_state(self) -> PluginState:
        """获取当前状态"""
        return PluginState.LOADED

    def validate_config(self, config: PluginConfig) -> tuple[bool, str]:
        """验证配置合法性

        Returns:
            (是否合法, 错误信息)
        """
        return True, ""


class BaseStrategyPlugin(StrategyPlugin):
    """策略插件基类实现

    提供常用的生命周期管理方法。
    """

    def __init__(self):
        self._state = PluginState.DISCOVERED
        self._config: PluginConfig | None = None
        self._load_time = 0.0

    @property
    def metadata(self) -> PluginMetadata:
        raise NotImplementedError

    def on_load(self) -> bool:
        self._state = PluginState.LOADED
        self._load_time = time.time()
        return True

    def on_unload(self) -> bool:
        self._state = PluginState.STOPPED
        return True

    def on_init(self, config: PluginConfig) -> bool:
        self._config = config
        self._state = PluginState.INITIALIZED
        return True

    def on_start(self) -> bool:
        self._state = PluginState.RUNNING
        return True

    def on_stop(self) -> bool:
        self._state = PluginState.STOPPED
        return True

    def on_update(self, params: dict[str, Any]) -> bool:
        if self._config:
            self._config.params.update(params)
        return True

    def get_state(self) -> PluginState:
        return self._state

    def analyze(self, data: dict[str, Any]) -> StrategyResult:
        """默认实现返回空结果"""
        return StrategyResult()


class PluginLifecycle:
    """插件生命周期管理器"""

    @staticmethod
    def create_context(plugin: StrategyPlugin) -> dict[str, Any]:
        """创建生命周期上下文"""
        return {
            "plugin_id": plugin.metadata.id,
            "plugin_name": plugin.metadata.name,
            "state": plugin.get_state(),
            "loaded_at": plugin.metadata.loaded_at,
        }

    @staticmethod
    def validate_transition(from_state: PluginState, to_state: PluginState) -> bool:
        """验证状态转换合法性"""
        valid_transitions = {
            PluginState.DISCOVERED: [PluginState.LOADED],
            PluginState.LOADED: [PluginState.INITIALIZED, PluginState.ERROR],
            PluginState.INITIALIZED: [PluginState.RUNNING, PluginState.PAUSED, PluginState.ERROR],
            PluginState.RUNNING: [PluginState.PAUSED, PluginState.STOPPED, PluginState.ERROR],
            PluginState.PAUSED: [PluginState.RUNNING, PluginState.STOPPED],
            PluginState.STOPPED: [PluginState.LOADED, PluginState.INITIALIZED],
            PluginState.ERROR: [PluginState.LOADED, PluginState.INITIALIZED],
        }
        return to_state in valid_transitions.get(from_state, [])
