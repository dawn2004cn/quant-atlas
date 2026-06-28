from __future__ import annotations

"""Comprehensive quantitative trading system components."""


from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


class SystemStatus(str, Enum):
    """System status."""
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    DEGRADED = "degraded"
    ERROR = "error"


@dataclass
class SystemHealth:
    """System health status."""
    status: SystemStatus = SystemStatus.INITIALIZING
    uptime_seconds: float = 0.0
    components: dict[str, dict] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)


class SystemComponent:
    """Base system component."""

    def __init__(self, name: str):
        self.name = name
        self._enabled = True
        logger.info(f"Component initialized: {name}")

    def is_enabled(self) -> bool:
        return self._enabled

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False

    def get_status(self) -> dict[str, Any]:
        return {"name": self.name, "enabled": self._enabled}


class DataSourceComponent(SystemComponent):
    """Market data source component."""

    def __init__(self):
        super().__init__("data_source")
        self._sources: dict[str, Any] = {}
        self._active_source: str = ""

    def register_source(self, name: str, provider: Any):
        self._sources[name] = provider
        logger.info(f"Registered data source: {name}")

    def set_active(self, name: str):
        if name in self._sources:
            self._active_source = name

    def get_status(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "enabled": self._enabled,
            "sources": list(self._sources.keys()),
            "active": self._active_source,
        }


class ComputationComponent(SystemComponent):
    """Computation component."""

    def __init__(self):
        super().__init__("computation")
        self._indicators_count = 0
        self._calculations_count = 0

    def record_calculation(self):
        self._calculations_count += 1

    def get_status(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "enabled": self._enabled,
            "calculations": self._calculations_count,
        }


class StrategyComponent(SystemComponent):
    """Strategy management component."""

    def __init__(self):
        super().__init__("strategy")
        self._strategies: dict[str, Any] = {}
        self._active_strategies: list[str] = []

    def register_strategy(self, name: str, strategy: Any):
        self._strategies[name] = strategy
        logger.info(f"Registered strategy: {name}")

    def activate(self, name: str):
        if name in self._strategies and name not in self._active_strategies:
            self._active_strategies.append(name)

    def deactivate(self, name: str):
        if name in self._active_strategies:
            self._active_strategies.remove(name)

    def get_status(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "enabled": self._enabled,
            "registered": list(self._strategies.keys()),
            "active": self._active_strategies,
        }


class ExecutionComponent(SystemComponent):
    """Order execution component."""

    def __init__(self):
        super().__init__("execution")
        self._orders_count = 0
        self._pending_orders: list[str] = []

    def record_order(self, order_id: str):
        self._orders_count += 1
        self._pending_orders.append(order_id)

    def complete_order(self, order_id: str):
        if order_id in self._pending_orders:
            self._pending_orders.remove(order_id)

    def get_status(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "enabled": self._enabled,
            "total_orders": self._orders_count,
            "pending": len(self._pending_orders),
        }


class RiskComponent(SystemComponent):
    """Risk management component."""

    def __init__(self):
        super().__init__("risk")
        self._alerts: list[dict] = []
        self._breaches: list[dict] = []

    def add_alert(self, alert: dict):
        self._alerts.append({**alert, "timestamp": datetime.now().isoformat()})
        if len(self._alerts) > 1000:
            self._alerts = self._alerts[-500:]

    def get_status(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "enabled": self._enabled,
            "alerts_count": len(self._alerts),
            "breaches_count": len(self._breaches),
        }


class QuantitativeSystem:
    """Comprehensive quantitative trading system."""

    def __init__(self):
        self._components: dict[str, SystemComponent] = {}
        self._start_time = datetime.now()
        self._register_components()
        logger.info("QuantitativeSystem initialized")

    def _register_components(self):
        self._components["data_source"] = DataSourceComponent()
        self._components["computation"] = ComputationComponent()
        self._components["strategy"] = StrategyComponent()
        self._components["execution"] = ExecutionComponent()
        self._components["risk"] = RiskComponent()

    def get_component(self, name: str) -> SystemComponent | None:
        return self._components.get(name)

    def get_health(self) -> SystemHealth:
        components_status = {}
        total_components = len(self._components)
        ready_components = 0

        for name, component in self._components.items():
            status = component.get_status()
            components_status[name] = status
            if component.is_enabled():
                ready_components += 1

        uptime = (datetime.now() - self._start_time).total_seconds()

        if ready_components == total_components:
            status = SystemStatus.READY
        elif ready_components > 0:
            status = SystemStatus.DEGRADED
        else:
            status = SystemStatus.ERROR

        return SystemHealth(
            status=status,
            uptime_seconds=uptime,
            components=components_status,
            metrics={"ready_ratio": ready_components / total_components if total_components > 0 else 0},
        )

    def start(self):
        """Start the system."""
        for component in self._components.values():
            component.enable()
        logger.info("QuantitativeSystem started")

    def stop(self):
        """Stop the system."""
        for component in self._components.values():
            component.disable()
        logger.info("QuantitativeSystem stopped")


_system: QuantitativeSystem | None = None


def get_quantitative_system() -> QuantitativeSystem:
    """Get global quantitative system."""
    global _system
    if _system is None:
        _system = QuantitativeSystem()
    return _system


__all__ = [
    "SystemStatus",
    "SystemHealth",
    "SystemComponent",
    "DataSourceComponent",
    "ComputationComponent",
    "StrategyComponent",
    "ExecutionComponent",
    "RiskComponent",
    "QuantitativeSystem",
    "get_quantitative_system",
]
