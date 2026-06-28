from __future__ import annotations

"""Strategy Engine - 策略引擎。

提供策略的运行管理:
- 初始化/启动/停止
- 参数热更新
- 信号聚合
- 生命周期事件
"""


import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .protocol import (
    PluginConfig,
    PluginState,
    StrategyPlugin,
    StrategySignal,
)
from .registry import StrategyRegistry, get_registry

logger = logging.getLogger(__name__)


@dataclass
class EngineConfig:
    """引擎配置"""
    max_concurrent: int = 10
    timeout_seconds: float = 30.0
    enable_auto_restart: bool = True
    restart_delay_seconds: float = 5.0
    signal_aggregation: str = "weighted"  # weighted, priority, voting


@dataclass
class EngineStats:
    """引擎统计"""
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    avg_execution_time_ms: float = 0.0
    last_run_time: datetime | None = None


class StrategyEngine:
    """策略引擎

    负责:
    - 策略生命周期管理
    - 数据分发与信号聚合
    - 异常处理与自动恢复
    """

    def __init__(
        self,
        registry: StrategyRegistry | None = None,
        config: EngineConfig | None = None,
    ):
        self._registry = registry or get_registry()
        self._config = config or EngineConfig()
        self._running_plugins: dict[str, StrategyPlugin] = {}
        self._stats = EngineStats()
        self._lock = threading.RLock()
        self._event_handlers: dict[str, list[Callable]] = {
            "before_analyze": [],
            "after_analyze": [],
            "on_signal": [],
            "on_error": [],
        }

    # ========== 生命周期管理 ==========

    def initialize_plugin(
        self,
        plugin_id: str,
        config: PluginConfig | None = None,
    ) -> bool:
        """初始化策略插件

        Args:
            plugin_id: 插件 ID
            config: 插件配置

        Returns:
            是否初始化成功
        """
        with self._lock:
            plugin = self._registry.get(plugin_id)
            if not plugin:
                logger.error(f"Plugin {plugin_id} not found in registry")
                return False

            config = config or PluginConfig()

            # 验证配置
            valid, error = plugin.validate_config(config)
            if not valid:
                logger.error(f"Plugin {plugin_id} config validation failed: {error}")
                return False

            # 调用初始化钩子
            if not plugin.on_init(config):
                logger.error(f"Plugin {plugin_id} initialization failed")
                self._registry.update_state(plugin_id, PluginState.ERROR)
                return False

            self._registry.update_state(plugin_id, PluginState.INITIALIZED)
            logger.info(f"Plugin initialized: {plugin_id}")
            return True

    def start_plugin(self, plugin_id: str) -> bool:
        """启动策略插件

        Args:
            plugin_id: 插件 ID

        Returns:
            是否启动成功
        """
        with self._lock:
            # 先初始化
            if self._registry.get_state(plugin_id) in (
                None,
                PluginState.DISCOVERED,
                PluginState.LOADED,
            ):
                if not self.initialize_plugin(plugin_id):
                    return False

            plugin = self._registry.get(plugin_id)
            if not plugin:
                return False

            # 调用启动钩子
            if not plugin.on_start():
                logger.error(f"Plugin {plugin_id} start failed")
                self._registry.update_state(plugin_id, PluginState.ERROR)
                return False

            self._running_plugins[plugin_id] = plugin
            self._registry.update_state(plugin_id, PluginState.RUNNING)
            logger.info(f"Plugin started: {plugin_id}")
            return True

    def stop_plugin(self, plugin_id: str) -> bool:
        """停止策略插件

        Args:
            plugin_id: 插件 ID

        Returns:
            是否停止成功
        """
        with self._lock:
            plugin = self._running_plugins.pop(plugin_id, None)
            if not plugin:
                logger.warning(f"Plugin {plugin_id} not running")
                return False

            # 调用停止钩子
            if not plugin.on_stop():
                logger.error(f"Plugin {plugin_id} stop failed")
                return False

            self._registry.update_state(plugin_id, PluginState.STOPPED)
            logger.info(f"Plugin stopped: {plugin_id}")
            return True

    def update_plugin_params(
        self,
        plugin_id: str,
        params: dict[str, Any],
    ) -> bool:
        """热更新策略参数

        Args:
            plugin_id: 插件 ID
            params: 新参数

        Returns:
            是否更新成功
        """
        with self._lock:
            plugin = self._registry.get(plugin_id)
            if not plugin:
                return False

            if not plugin.on_update(params):
                logger.error(f"Plugin {plugin_id} update failed")
                return False

            logger.info(f"Plugin params updated: {plugin_id}")
            return True

    # ========== 信号执行 ==========

    def execute(
        self,
        data: dict[str, Any],
        plugin_ids: list[str] | None = None,
    ) -> list[StrategySignal]:
        """执行策略分析

        Args:
            data: 市场数据
            plugin_ids: 指定插件 ID 列表，None 表示执行所有运行中的插件

        Returns:
            聚合后的信号列表
        """
        with self._lock:
            start_time = time.time()

            # 确定要执行的插件
            if plugin_ids is None:
                plugins = list(self._running_plugins.values())
            else:
                plugins = [
                    self._running_plugins.get(pid)
                    for pid in plugin_ids
                    if pid in self._running_plugins
                ]

            all_signals = []

            for plugin in plugins:
                try:
                    # 触发 before_analyze 事件
                    self._emit("before_analyze", plugin, data)

                    # 执行分析
                    result = plugin.analyze(data)

                    # 触发 after_analyze 事件
                    self._emit("after_analyze", plugin, result)

                    if result.signals:
                        all_signals.extend(result.signals)
                        for signal in result.signals:
                            self._emit("on_signal", plugin, signal)

                    if result.errors:
                        for error in result.errors:
                            self._emit("on_error", plugin, error)

                except Exception as e:
                    logger.error(f"Plugin {plugin.metadata.id} execution failed: {e}")
                    self._emit("on_error", plugin, str(e))

            # 聚合信号
            aggregated = self._aggregate_signals(all_signals)

            # 更新统计
            self._update_stats(time.time() - start_time, len(all_signals) > 0)

            return aggregated

    def _aggregate_signals(
        self,
        signals: list[StrategySignal],
    ) -> list[StrategySignal]:
        """聚合信号"""
        if not signals:
            return []

        if self._config.signal_aggregation == "weighted":
            # 按权重聚合
            return signals
        elif self._config.signal_aggregation == "priority":
            # 按优先级排序
            return sorted(signals, key=lambda s: s.confidence, reverse=True)
        else:
            return signals

    def _update_stats(self, elapsed: float, success: bool) -> None:
        """更新统计信息"""
        self._stats.total_runs += 1
        if success:
            self._stats.successful_runs += 1
        else:
            self._stats.failed_runs += 1

        # 计算平均执行时间
        n = self._stats.total_runs
        self._stats.avg_execution_time_ms = (
            self._stats.avg_execution_time_ms * (n - 1) + elapsed * 1000
        ) / n
        self._stats.last_run_time = datetime.now()

    # ========== 事件系统 ==========

    def on(self, event: str, handler: Callable) -> None:
        """注册事件处理器"""
        if event in self._event_handlers:
            self._event_handlers[event].append(handler)

    def off(self, event: str, handler: Callable) -> None:
        """移除事件处理器"""
        if event in self._event_handlers:
            self._event_handlers[event].remove(handler)

    def _emit(self, event: str, plugin: StrategyPlugin, data: Any) -> None:
        """触发事件"""
        for handler in self._event_handlers.get(event, []):
            try:
                handler(plugin, data)
            except Exception as e:
                logger.error(f"Event handler failed: {e}")

    # ========== 状态查询 ==========

    def get_running_plugins(self) -> list[str]:
        """获取运行中的插件 ID"""
        with self._lock:
            return list(self._running_plugins.keys())

    def get_stats(self) -> EngineStats:
        """获取引擎统计"""
        with self._lock:
            return self._stats

    def get_plugin_state(self, plugin_id: str) -> PluginState | None:
        """获取插件状态"""
        return self._registry.get_state(plugin_id)

    def stop_all(self) -> int:
        """停止所有插件"""
        with self._lock:
            plugin_ids = list(self._running_plugins.keys())
            for pid in plugin_ids:
                self.stop_plugin(pid)
            return len(plugin_ids)


class GlobalEngine:
    """全局策略引擎 (单例)"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._engine = StrategyEngine()
        return cls._instance

    def __getattr__(self, name: str):
        return getattr(self._engine, name)


def get_engine() -> StrategyEngine:
    """获取全局引擎"""
    return GlobalEngine()
