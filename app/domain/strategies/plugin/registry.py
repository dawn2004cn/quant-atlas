from __future__ import annotations

"""Strategy Registry - 策略注册中心。

提供策略插件的注册、发现、查询功能:
- 注册策略
- 查找策略
- 状态管理
"""


import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .protocol import PluginMetadata, PluginState, StrategyPlugin

logger = logging.getLogger(__name__)


@dataclass
class RegistryEntry:
    """注册表条目"""
    plugin: StrategyPlugin
    metadata: PluginMetadata
    state: PluginState = PluginState.DISCOVERED
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    usage_count: int = 0


class StrategyRegistry:
    """策略注册中心 - 线程安全

    管理所有已加载的策略插件，支持:
    - 注册/注销
    - 按名称/ID 查询
    - 状态变更
    """

    def __init__(self):
        self._plugins: dict[str, RegistryEntry] = {}
        self._lock = threading.RLock()
        self._observers: list[callable] = []

    def register(self, plugin: StrategyPlugin) -> bool:
        """注册策略插件

        Args:
            plugin: 策略插件实例

        Returns:
            是否注册成功
        """
        with self._lock:
            plugin_id = plugin.metadata.id

            if plugin_id in self._plugins:
                logger.warning(f"Plugin {plugin_id} already registered")
                return False

            # 调用加载钩子
            if not plugin.on_load():
                logger.error(f"Plugin {plugin_id} load failed")
                return False

            entry = RegistryEntry(
                plugin=plugin,
                metadata=plugin.metadata,
                state=PluginState.LOADED,
            )

            self._plugins[plugin_id] = entry
            self._notify_observers("register", plugin_id, plugin)

            logger.info(f"Plugin registered: {plugin_id}")
            return True

    def unregister(self, plugin_id: str) -> bool:
        """注销策略插件

        Args:
            plugin_id: 插件 ID

        Returns:
            是否注销成功
        """
        with self._lock:
            entry = self._plugins.get(plugin_id)
            if not entry:
                logger.warning(f"Plugin {plugin_id} not found")
                return False

            # 调用卸载钩子
            if not entry.plugin.on_unload():
                logger.error(f"Plugin {plugin_id} unload failed")
                return False

            del self._plugins[plugin_id]
            self._notify_observers("unregister", plugin_id, None)

            logger.info(f"Plugin unregistered: {plugin_id}")
            return True

    def get(self, plugin_id: str) -> StrategyPlugin | None:
        """获取策略插件

        Args:
            plugin_id: 插件 ID

        Returns:
            插件实例或 None
        """
        with self._lock:
            entry = self._plugins.get(plugin_id)
            if entry:
                entry.last_used = datetime.now()
                entry.usage_count += 1
            return entry.plugin if entry else None

    def get_by_name(self, name: str) -> StrategyPlugin | None:
        """通过名称查找

        Args:
            name: 插件名称

        Returns:
            插件实例或 None
        """
        with self._lock:
            for entry in self._plugins.values():
                if entry.metadata.name == name:
                    entry.last_used = datetime.now()
                    entry.usage_count += 1
                    return entry.plugin
            return None

    def list_all(self) -> list[PluginMetadata]:
        """列出所有插件元数据"""
        with self._lock:
            return [entry.metadata for entry in self._plugins.values()]

    def list_by_state(self, state: PluginState) -> list[PluginMetadata]:
        """按状态列出插件"""
        with self._lock:
            return [
                entry.metadata
                for entry in self._plugins.values()
                if entry.state == state
            ]

    def list_by_tag(self, tag: str) -> list[PluginMetadata]:
        """按标签查找插件"""
        with self._lock:
            return [
                entry.metadata
                for entry in self._plugins.values()
                if tag in entry.metadata.tags
            ]

    def update_state(self, plugin_id: str, state: PluginState) -> bool:
        """更新插件状态"""
        with self._lock:
            entry = self._plugins.get(plugin_id)
            if not entry:
                return False
            entry.state = state
            self._notify_observers("state_change", plugin_id, state)
            return True

    def get_state(self, plugin_id: str) -> PluginState | None:
        """获取插件状态"""
        with self._lock:
            entry = self._plugins.get(plugin_id)
            return entry.state if entry else None

    def get_stats(self) -> dict[str, Any]:
        """获取注册表统计"""
        with self._lock:
            total = len(self._plugins)
            by_state = {}
            for entry in self._plugins.values():
                state = entry.state.value
                by_state[state] = by_state.get(state, 0) + 1

            return {
                "total": total,
                "by_state": by_state,
                "total_usage": sum(e.usage_count for e in self._plugins.values()),
            }

    def add_observer(self, callback: callable) -> None:
        """添加状态变更观察者"""
        self._observers.append(callback)

    def remove_observer(self, callback: callable) -> None:
        """移除观察者"""
        self._observers.remove(callback)

    def _notify_observers(self, event: str, plugin_id: str, data: Any) -> None:
        """通知观察者"""
        for observer in self._observers:
            try:
                observer(event, plugin_id, data)
            except Exception as e:
                logger.error(f"Observer notification failed: {e}")


class GlobalRegistry:
    """全局策略注册中心 (单例)"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._registry = StrategyRegistry()
        return cls._instance

    def __getattr__(self, name: str):
        return getattr(self._registry, name)

    @classmethod
    def reset(cls) -> None:
        """重置全局注册表 (测试用)"""
        with cls._lock:
            if cls._instance:
                cls._instance._registry = StrategyRegistry()


def get_registry() -> StrategyRegistry:
    """获取全局注册中心"""
    return GlobalRegistry()
