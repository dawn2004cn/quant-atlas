from __future__ import annotations
"""Strategy Pool Manager - 策略池管理器。

管理多租户策略实例:
- 租户隔离
- 实例生命周期
- 资源分配
"""


import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.logger import get_logger
from app.domain.strategies.plugin import StrategyPlugin, PluginConfig, PluginState

logger = get_logger(__name__)


@dataclass
class TenantContext:
    """租户上下文"""
    tenant_id: str
    name: str
    max_strategies: int = 10
    max_memory_mb: int = 512
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PoolConfig:
    """策略池配置"""
    max_total_strategies: int = 100
    max_per_tenant: int = 10
    enable_isolation: bool = True
    auto_cleanup_seconds: float = 3600.0  # 1小时


@dataclass
class StrategyInstance:
    """策略实例"""
    instance_id: str
    tenant_id: str
    plugin: StrategyPlugin
    config: PluginConfig
    state: PluginState = PluginState.DISCOVERED
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    memory_usage_mb: float = 0.0
    execution_count: int = 0


class StrategyPool:
    """策略池 - 多租户策略实例管理

    提供:
    - 租户隔离的策略实例管理
    - 生命周期协调
    - 资源监控
    - 自动清理
    """

    def __init__(self, config: PoolConfig | None = None):
        self._config = config or PoolConfig()
        self._tenants: dict[str, TenantContext] = {}
        self._instances: dict[str, StrategyInstance] = {}
        self._tenant_instances: dict[str, list[str]] = {}  # tenant_id -> [instance_ids]
        self._lock = threading.RLock()

    # ========== 租户管理 ==========

    def register_tenant(self, tenant: TenantContext) -> bool:
        """注册租户"""
        with self._lock:
            if tenant.tenant_id in self._tenants:
                logger.warning(f"Tenant {tenant.tenant_id} already registered")
                return False

            self._tenants[tenant.tenant_id] = tenant
            self._tenant_instances[tenant.tenant_id] = []
            logger.info(f"Tenant registered: {tenant.tenant_id}")
            return True

    def unregister_tenant(self, tenant_id: str) -> bool:
        """注销租户及其所有策略实例"""
        with self._lock:
            if tenant_id not in self._tenants:
                return False

            # 停止所有实例
            instance_ids = self._tenant_instances.get(tenant_id, [])
            for instance_id in instance_ids:
                self._stop_instance(instance_id)

            del self._tenants[tenant_id]
            del self._tenant_instances[tenant_id]

            logger.info(f"Tenant unregistered: {tenant_id}")
            return True

    # ========== 策略实例管理 ==========

    def create_instance(
        self,
        tenant_id: str,
        plugin: StrategyPlugin,
        config: PluginConfig | None = None,
    ) -> StrategyInstance | None:
        """创建策略实例

        Args:
            tenant_id: 租户 ID
            plugin: 策略插件
            config: 策略配置

        Returns:
            策略实例或 None
        """
        with self._lock:
            # 验证租户
            if tenant_id not in self._tenants:
                logger.error(f"Unknown tenant: {tenant_id}")
                return None

            tenant = self._tenants[tenant_id]

            # 检查租户限制
            current_count = len(self._tenant_instances.get(tenant_id, []))
            if current_count >= tenant.max_strategies:
                logger.error(f"Tenant {tenant_id} reached max strategies limit")
                return None

            # 检查全局限制
            if len(self._instances) >= self._config.max_total_strategies:
                logger.error("Global strategy limit reached")
                return None

        # 创建实例
        instance_id = f"{tenant_id}_{plugin.metadata.id}_{int(time.time())}"
        config = config or PluginConfig()

        instance = StrategyInstance(
            instance_id=instance_id,
            tenant_id=tenant_id,
            plugin=plugin,
            config=config,
        )

        with self._lock:
            self._instances[instance_id] = instance
            self._tenant_instances.setdefault(tenant_id, []).append(instance_id)

        # 初始化插件
        plugin.on_init(config)
        instance.state = plugin.get_state()

        logger.info(f"Strategy instance created: {instance_id}")
        return instance

    def destroy_instance(self, instance_id: str) -> bool:
        """销毁策略实例"""
        with self._lock:
            instance = self._instances.get(instance_id)
            if not instance:
                return False

            return self._stop_instance(instance_id)

    def _stop_instance(self, instance_id: str) -> bool:
        """停止实例"""
        instance = self._instances.get(instance_id)
        if not instance:
            return False

        try:
            instance.plugin.on_stop()
            instance.state = PluginState.STOPPED

            # 从租户列表中移除
            tenant_instances = self._tenant_instances.get(instance.tenant_id, [])
            if instance_id in tenant_instances:
                tenant_instances.remove(instance_id)

            del self._instances[instance_id]
            logger.info(f"Instance destroyed: {instance_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop instance {instance_id}: {e}")
            return False

    # ========== 查询与统计 ==========

    def get_instance(self, instance_id: str) -> StrategyInstance | None:
        """获取策略实例"""
        return self._instances.get(instance_id)

    def get_tenant_instances(self, tenant_id: str) -> list[StrategyInstance]:
        """获取租户的所有策略实例"""
        instance_ids = self._tenant_instances.get(tenant_id, [])
        return [
            self._instances[instance_id]
            for instance_id in instance_ids
            if instance_id in self._instances
        ]

    def get_stats(self) -> dict[str, Any]:
        """获取策略池统计"""
        with self._lock:
            by_state = {}
            for instance in self._instances.values():
                state = instance.state.value
                by_state[state] = by_state.get(state, 0) + 1

            return {
                "total_instances": len(self._instances),
                "total_tenants": len(self._tenants),
                "by_state": by_state,
                "per_tenant": {
                    tenant_id: len(instances)
                    for tenant_id, instances in self._tenant_instances.items()
                },
            }

    def cleanup_idle_instances(self, max_idle_seconds: float | None = None) -> int:
        """清理空闲实例

        Returns:
            清理数量
        """
        max_idle = max_idle_seconds or self._config.auto_cleanup_seconds
        now = time.time()
        to_remove = []

        with self._lock:
            for instance_id, instance in self._instances.items():
                if now - instance.last_active > max_idle:
                    to_remove.append(instance_id)

        for instance_id in to_remove:
            self.destroy_instance(instance_id)

        return len(to_remove)
