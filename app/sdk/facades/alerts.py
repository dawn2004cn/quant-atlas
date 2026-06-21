from __future__ import annotations

"""Alert center facade over ``AlertCenterService``."""

from typing import Any

from app.modules.system.services.system.alert_center_service import AlertCenterService
from app.domain.dto.alert_dto import AlertCategory, AlertCenterFeedDTO, AlertLevel


class AlertsFacade:
    """Thin SDK wrapper for the intelligent alert center."""

    def __init__(self, service: AlertCenterService | None = None) -> None:
        self._service = service or AlertCenterService()

    def list(
        self,
        *,
        limit: int = 50,
        min_level: AlertLevel = "info",
        category: AlertCategory | None = None,
        include_system_probes: bool = True,
    ) -> AlertCenterFeedDTO:
        return self._service.list_alerts(
            limit=limit,
            min_level=min_level,
            category=category,
            include_system_probes=include_system_probes,
        )

    def summary(self, *, limit: int = 100) -> dict[str, Any]:
        feed = self._service.list_alerts(limit=limit, min_level="info")
        return {
            "total": feed.total,
            "counts_by_level": feed.counts_by_level,
            "counts_by_category": feed.counts_by_category,
            "critical_count": feed.counts_by_level.get("critical", 0),
            "warning_count": feed.counts_by_level.get("warning", 0),
        }

    def list_dict(self, **kwargs: Any) -> dict[str, Any]:
        return self.list(**kwargs).model_dump(mode="json")

    def dispatch(
        self,
        *,
        min_level: AlertLevel = "warning",
        limit: int = 20,
        channel_names: list[str] | None = None,
        include_system_probes: bool = True,
    ) -> dict[str, Any]:
        from app.modules.system.services.system.alert_notification_service import AlertNotificationService

        result = AlertNotificationService(alert_service=self._service).dispatch(
            min_level=min_level,
            limit=limit,
            channel_names=channel_names,
            include_system_probes=include_system_probes,
        )
        return result.model_dump(mode="json")
