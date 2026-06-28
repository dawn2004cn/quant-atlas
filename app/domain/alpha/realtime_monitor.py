from __future__ import annotations
"""Real-Time Data Push Service - 实时数据推送服务.

将 ArrowPool 数据实时推送到前端和 RD-Agent。
"""


from dataclasses import dataclass
from datetime import datetime
from typing import Any
from collections.abc import Callable


import logging
logger = logging.getLogger(__name__)
@dataclass
class DataPacket:
    """数据数据包."""

    data_type: str
    timestamp: str
    payload: dict[str, Any]
    priority: int = 0


class RealTimePusher:
    """实时数据推送器."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable]] = {}
        self._data_buffer: list[DataPacket] = []
        self._max_buffer_size = 1000

    def subscribe(
        self,
        data_type: str,
        callback: Callable,
    ) -> None:
        """订阅数据。

        Args:
            data_type: 数据类型
            callback: 回调函数
        """
        if data_type not in self._subscribers:
            self._subscribers[data_type] = []
        self._subscribers[data_type].append(callback)

    def unsubscribe(
        self,
        data_type: str,
        callback: Callable,
    ) -> None:
        """取消订阅。

        Args:
            data_type: 数据类型
            callback: 回调函数
        """
        if data_type in self._subscribers:
            self._subscribers[data_type] = [
                c for c in self._subscribers[data_type] if c != callback
            ]

    def push(
        self,
        data_type: str,
        payload: dict[str, Any],
        priority: int = 0,
    ) -> None:
        """推送数据。

        Args:
            data_type: 数据类型
            payload: 数据内容
            priority: 优先级
        """
        packet = DataPacket(
            data_type=data_type,
            timestamp=datetime.utcnow().isoformat(),
            payload=payload,
            priority=priority,
        )

        self._data_buffer.append(packet)
        if len(self._data_buffer) > self._max_buffer_size:
            self._data_buffer = self._data_buffer[-self._max_buffer_size:]

        if data_type in self._subscribers:
            for callback in self._subscribers[data_type]:
                try:
                    callback(packet)
                except Exception as e:
                    logger.warning("realtime_monitor.py.push: %s", e)

    def get_latest(
        self,
        data_type: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """获取最新数据。

        Args:
            data_type: 数据类型
            limit: 返回数量

        Returns:
            最新数据列表
        """
        packets = [
            p for p in self._data_buffer
            if p.data_type == data_type
        ]
        packets.sort(key=lambda x: x.timestamp, reverse=True)
        return [
            {
                "data_type": p.data_type,
                "timestamp": p.timestamp,
                "payload": p.payload,
            }
            for p in packets[:limit]
        ]


class FactorRealtimeMonitor:
    """因子实时监控器."""

    def __init__(self) -> None:
        self._pusher = RealTimePusher()
        self._monitored_factors: dict[str, dict[str, Any]] = {}

    @property
    def pusher(self) -> RealTimePusher:
        return self._pusher

    def start_monitor(
        self,
        factor_id: str,
        update_interval_seconds: int = 60,
    ) -> None:
        """开始监控因子。

        Args:
            factor_id: 因子 ID
            update_interval_seconds: 更新间隔
        """
        self._monitored_factors[factor_id] = {
            "factor_id": factor_id,
            "interval": update_interval_seconds,
            "started_at": datetime.utcnow().isoformat(),
            "status": "monitoring",
        }

    def stop_monitor(self, factor_id: str) -> None:
        """停止监控因子。"""
        if factor_id in self._monitored_factors:
            self._monitored_factors[factor_id]["status"] = "stopped"

    def push_factor_update(
        self,
        factor_id: str,
        ic_value: float,
        sharpe: float,
        position_data: dict[str, Any],
    ) -> None:
        """推送因子更新。

        Args:
            factor_id: 因子 ID
            ic_value: IC 值
            sharpe: Sharpe 值
            position_data: 持仓数据
        """
        self._pusher.push(
            "factor_update",
            {
                "factor_id": factor_id,
                "ic": ic_value,
                "sharpe": sharpe,
                "positions": position_data,
            },
            priority=1 if abs(ic_value) < 0.02 else 2,
        )

    def get_monitor_status(self) -> dict[str, Any]:
        """获取监控状态."""
        return {
            "monitored_factors": list(self._monitored_factors.keys()),
            "buffer_size": len(self._pusher._data_buffer),
        }


class AlertManager:
    """告警管理器."""

    ALERT_LEVELS = {
        "info": 0,
        "warning": 1,
        "critical": 2,
    }

    def __init__(self) -> None:
        self._alerts: list[dict[str, Any]] = []
        self._rules: list[dict[str, Any]] = []

    def add_rule(
        self,
        name: str,
        condition: Callable[[dict[str, Any]], bool],
        level: str = "info",
        message: str = "",
    ) -> None:
        """添加告警规则。

        Args:
            name: 规则名称
            condition: 条件函数
            level: 告警级别
            message: 告警消息
        """
        self._rules.append({
            "name": name,
            "condition": condition,
            "level": level,
            "message": message,
            "created_at": datetime.utcnow().isoformat(),
        })

    def check(
        self,
        data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """检查数据是否触发告警。

        Args:
            data: 待检查数据

        Returns:
            触发的告警列表
        """
        triggered = []

        for rule in self._rules:
            try:
                if rule["condition"](data):
                    triggered.append({
                        "rule": rule["name"],
                        "level": rule["level"],
                        "message": rule["message"] or rule["name"],
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": data,
                    })
            except Exception as e:
                logger.warning("realtime_monitor.py.check: %s", e)

        self._alerts.extend(triggered)
        return triggered

    def get_alerts(
        self,
        level: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """获取告警历史。

        Args:
            level: 告警级别过滤
            limit: 返回数量

        Returns:
            告警列表
        """
        alerts = self._alerts
        if level:
            alerts = [a for a in alerts if a["level"] == level]

        return sorted(
            alerts,
            key=lambda x: x["timestamp"],
            reverse=True,
        )[:limit]


def create_default_alerts() -> list[dict[str, Any]]:
    """创建默认告警规则."""
    return [
        {
            "name": "IC decay warning",
            "condition": lambda d: d.get("ic", 0) < 0.03,
            "level": "warning",
            "message": "IC 低于 0.03，因子可能失效",
        },
        {
            "name": "Sharpe drop",
            "condition": lambda d: d.get("sharpe", 0) < 0.5,
            "level": "warning",
            "message": "Sharpe 低于 0.5",
        },
        {
            "name": "High drawdown",
            "condition": lambda d: d.get("drawdown", 0) > 0.15,
            "level": "critical",
            "message": "回撤超过 15%",
        },
    ]


_global_monitor: FactorRealtimeMonitor | None = None
_global_alerts: AlertManager | None = None


def get_factor_monitor() -> FactorRealtimeMonitor:
    """获取全局因子监控器."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = FactorRealtimeMonitor()
    return _global_monitor


def get_alert_manager() -> AlertManager:
    """获取全局告警管理器."""
    global _global_alerts
    if _global_alerts is None:
        _global_alerts = AlertManager()
    return _global_alerts
