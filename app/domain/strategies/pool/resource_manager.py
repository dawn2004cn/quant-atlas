from __future__ import annotations
"""Resource Manager - 资源管理器。

管理策略实例的资源使用:
- 内存限制
- CPU 限制
- 执行时间限制
"""


import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ResourceLimit:
    """资源限制"""
    max_memory_mb: float = 256.0
    max_cpu_percent: float = 50.0
    max_execution_seconds: float = 30.0
    max_instances: int = 10


@dataclass
class ResourceUsage:
    """资源使用统计"""
    memory_mb: float = 0.0
    cpu_percent: float = 0.0
    execution_count: int = 0
    total_execution_seconds: float = 0.0
    last_execution_time: float = 0.0


class ResourceManager:
    """资源管理器

    监控和管理策略实例的资源使用。
    """

    def __init__(self, default_limit: ResourceLimit | None = None):
        self._default_limit = default_limit or ResourceLimit()
        self._limits: dict[str, ResourceLimit] = {}
        self._usage: dict[str, ResourceUsage] = {}
        self._lock = threading.RLock()

    def set_limit(self, instance_id: str, limit: ResourceLimit) -> None:
        """设置实例资源限制"""
        with self._lock:
            self._limits[instance_id] = limit

    def get_limit(self, instance_id: str) -> ResourceLimit:
        """获取实例资源限制"""
        with self._lock:
            return self._limits.get(instance_id, self._default_limit)

    def record_usage(self, instance_id: str, usage: ResourceUsage) -> None:
        """记录资源使用"""
        with self._lock:
            self._usage[instance_id] = usage

    def check_limits(self, instance_id: str) -> tuple[bool, str]:
        """检查资源使用是否超出限制

        Returns:
            (是否合法, 错误信息)
        """
        with self._lock:
            limit = self._limits.get(instance_id, self._default_limit)
            usage = self._usage.get(instance_id)

            if not usage:
                return True, ""

            if usage.memory_mb > limit.max_memory_mb:
                return False, f"Memory limit exceeded: {usage.memory_mb:.1f}MB > {limit.max_memory_mb:.1f}MB"

            if usage.cpu_percent > limit.max_cpu_percent:
                return False, f"CPU limit exceeded: {usage.cpu_percent:.1f}% > {limit.max_cpu_percent:.1f}%"

            return True, ""

    def get_usage(self, instance_id: str) -> ResourceUsage | None:
        """获取实例资源使用"""
        with self._lock:
            return self._usage.get(instance_id)

    def get_all_usage(self) -> dict[str, ResourceUsage]:
        """获取所有实例资源使用"""
        with self._lock:
            return self._usage.copy()

    def reset_usage(self, instance_id: str) -> None:
        """重置实例资源使用统计"""
        with self._lock:
            self._usage[instance_id] = ResourceUsage()

    def get_total_usage(self) -> ResourceUsage:
        """获取总资源使用"""
        with self._lock:
            total = ResourceUsage()
            for usage in self._usage.values():
                total.memory_mb += usage.memory_mb
                total.cpu_percent = max(total.cpu_percent, usage.cpu_percent)
                total.execution_count += usage.execution_count
                total.total_execution_seconds += usage.total_execution_seconds
            return total