from __future__ import annotations

"""Aggregate operational alerts from task messages, health probes, and data freshness."""

from typing import Any
from collections.abc import Callable

from app.modules.system.services.helpers.monitoring_access import check_table_freshness
from app.modules.system.services.helpers.task_message_access import get_task_message_store
from app.modules.system.services.system.system_health_probe_service import SystemHealthProbeService
from app.domain.dto.alert_dto import AlertCenterFeedDTO, AlertEventDTO, AlertCategory, AlertLevel

_LEVEL_RANK = {"info": 0, "warning": 1, "critical": 2}

_TASK_FAILURE_EVENTS = frozenset({"task_failed"})
_FACTOR_EVENTS = frozenset({"factor_ic_alert"})
_ALERT_TASK_EVENTS = _TASK_FAILURE_EVENTS | _FACTOR_EVENTS | frozenset({"task_revoked"})


class AlertCenterService:
    """Collect and normalize alerts for the intelligent alert center."""

    def __init__(
        self,
        *,
        message_store_factory: Callable[[], Any] | None = None,
        freshness_checker: Callable[[str, int], bool] | None = None,
        cross_team_service: Any | None = None,
    ) -> None:
        self._message_store_factory = message_store_factory or get_task_message_store
        self._freshness_checker = freshness_checker or (
            lambda table, minutes=15: check_table_freshness(table, max_delay_minutes=minutes)
        )
        self._cross_team = cross_team_service

    def list_alerts(
        self,
        *,
        limit: int = 50,
        min_level: AlertLevel = "info",
        category: AlertCategory | None = None,
        include_system_probes: bool = True,
    ) -> AlertCenterFeedDTO:
        items: list[AlertEventDTO] = []
        items.extend(self._alerts_from_task_messages(limit=limit * 2))
        items.extend(self._alerts_from_data_freshness())
        items.extend(self._alerts_from_cross_team())
        if include_system_probes:
            items.extend(self._alerts_from_system_probes())

        min_rank = _LEVEL_RANK[min_level]
        filtered = [
            item
            for item in items
            if _LEVEL_RANK[item.level] >= min_rank and (category is None or item.category == category)
        ]
        filtered.sort(key=lambda x: x.occurred_at, reverse=True)
        filtered = filtered[: max(1, min(limit, 200))]

        counts_by_level: dict[str, int] = {}
        counts_by_category: dict[str, int] = {}
        for item in filtered:
            counts_by_level[item.level] = counts_by_level.get(item.level, 0) + 1
            counts_by_category[item.category] = counts_by_category.get(item.category, 0) + 1

        return AlertCenterFeedDTO(
            items=filtered,
            total=len(filtered),
            counts_by_level=counts_by_level,
            counts_by_category=counts_by_category,
        )

    def _alerts_from_task_messages(self, *, limit: int) -> list[AlertEventDTO]:
        try:
            store = self._message_store_factory()
            rows = store.list_recent(limit=limit)
        except Exception:
            return []

        alerts: list[AlertEventDTO] = []
        for row in rows:
            event = str(row.get("event") or "")
            if event not in _ALERT_TASK_EVENTS and event != "task_succeeded":
                continue
            if event == "task_succeeded":
                row.get("meta") or {}
                if not row.get("detail", "").startswith("skipped"):
                    continue
                level: AlertLevel = "info"
                category: AlertCategory = "task"
                title = row.get("label") or row.get("task_name") or "任务"
                message = row.get("detail") or "任务已跳过"
            elif event == "task_failed":
                level = "critical"
                category = "task"
                title = row.get("label") or row.get("task_name") or "Celery 任务"
                message = row.get("detail") or "任务执行失败"
            elif event == "factor_ic_alert":
                level = "warning"
                category = "factor"
                title = "因子 IC 弱信号"
                message = row.get("detail") or "检测到弱 IC 因子"
            elif event == "task_revoked":
                level = "warning"
                category = "task"
                title = "Celery 任务已撤销"
                message = row.get("detail") or "任务被运维撤销"
            else:
                continue

            alerts.append(
                AlertEventDTO(
                    id=str(row.get("id") or f"{event}:{row.get('task_id', '')}"),
                    level=level,
                    category=category,
                    title=str(title),
                    message=str(message)[:2000],
                    source="task_message_store",
                    occurred_at=str(row.get("ts") or ""),
                    meta={
                        "event": event,
                        "task_id": row.get("task_id"),
                        "task_name": row.get("task_name"),
                        **(row.get("meta") or {}),
                    },
                )
            )
        return alerts

    def _alerts_from_data_freshness(self) -> list[AlertEventDTO]:
        try:
            fresh = self._freshness_checker("stock_history_sh", 15)
        except Exception as exc:
            return [
                AlertEventDTO(
                    id="data:freshness:check_error",
                    level="warning",
                    category="data",
                    title="数据新鲜度检查失败",
                    message=str(exc)[:500],
                    source="monitoring_access",
                    occurred_at="",
                )
            ]
        if fresh:
            return []
        return [
            AlertEventDTO(
                id="data:freshness:stock_history_sh",
                level="warning",
                category="data",
                title="A股历史数据可能过期",
                message="stock_history_sh 最新记录超出允许延迟，策略信号可能基于陈旧数据。",
                source="monitoring_access",
                occurred_at="",
            )
        ]

    def _alerts_from_cross_team(self) -> list[AlertEventDTO]:
        if self._cross_team is None:
            return []
        try:
            payload = self._cross_team.list_site_alerts(limit=40)
        except Exception:
            return []
        alerts: list[AlertEventDTO] = []
        for row in payload.get("alerts") or []:
            level_raw = str(row.get("level") or "info")
            level: AlertLevel = level_raw if level_raw in ("info", "warning", "critical") else "info"
            alerts.append(
                AlertEventDTO(
                    id=str(row.get("id") or ""),
                    level=level,
                    category="consensus",
                    title=str(row.get("title") or "全站共识异动"),
                    message=str(row.get("message") or "")[:2000],
                    source="cross_team_meta_learning",
                    occurred_at=str(row.get("created_at") or ""),
                    meta={
                        "symbol": row.get("symbol"),
                        "market": row.get("market"),
                        "verdict": row.get("verdict"),
                        "team_count": row.get("team_count"),
                        "avg_confidence": row.get("avg_confidence"),
                    },
                )
            )
        return alerts

    def _alerts_from_system_probes(self) -> list[AlertEventDTO]:
        alerts: list[AlertEventDTO] = []
        probes = {
            "mysql": SystemHealthProbeService.probe_mysql(),
            "async_queue": SystemHealthProbeService.probe_async_queue(),
        }
        for name, result in probes.items():
            status = str(result.get("status") or "")
            if status in ("ok", "skipped"):
                continue
            level: AlertLevel = "critical" if status == "error" else "warning"
            alerts.append(
                AlertEventDTO(
                    id=f"system:{name}:{status}",
                    level=level,
                    category="system",
                    title=f"系统组件异常：{name}",
                    message=str(result.get("error") or result.get("reason") or status)[:500],
                    source="system_health_probe",
                    occurred_at="",
                    meta=result,
                )
            )
        return alerts
