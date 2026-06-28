from __future__ import annotations

"""Intelligent alert center API."""

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ValidationError
from app.core.registry import register_routes
from app.domain.dto.alert_dto import AlertCategory
from app.modules.system.services.system.alert_center_service import AlertCenterService
from app.modules.system.services.system.alert_notification_service import AlertNotificationService

from .common import ok_response
from .v1_context import ApiV1Context

_VALID_LEVELS = frozenset({"info", "warning", "critical"})
_VALID_CATEGORIES = frozenset({"task", "factor", "data", "system", "execution", "consensus"})


@register_routes(name="alert_center", context="system", description="Intelligent alert center API")
def register_alert_center_routes(blueprint: Blueprint, ctx: ApiV1Context | None = None) -> None:
    cross_team = (
        getattr(ctx, "cross_team_meta_learning_service", None) if ctx is not None else None
    )
    service = AlertCenterService(cross_team_service=cross_team)
    dispatch_service = AlertNotificationService(alert_service=service)

    @blueprint.get("/system/alerts")
    @login_required
    def system_alert_center():
        """Unified alert feed: tasks, factor IC, data freshness, system health."""
        limit = min(max(int(request.args.get("limit", 50)), 1), 200)
        min_level = (request.args.get("min_level") or "info").strip().lower()
        if min_level not in _VALID_LEVELS:
            raise ValidationError("invalid_min_level")
        category_raw = (request.args.get("category") or "").strip().lower()
        category: AlertCategory | None = None
        if category_raw:
            if category_raw not in _VALID_CATEGORIES:
                raise ValidationError("invalid_category")
            category = category_raw  # type: ignore[assignment]

        include_probes = request.args.get("include_probes", "1") != "0"
        feed = service.list_alerts(
            limit=limit,
            min_level=min_level,  # type: ignore[arg-type]
            category=category,
            include_system_probes=include_probes,
        )
        return ok_response(
            data=feed.model_dump(mode="json"),
            count=feed.total,
        )

    @blueprint.post("/system/alerts/dispatch")
    @login_required
    def system_alert_dispatch():
        """Push current alert feed to webhook / DingTalk / email (configured via env)."""
        body = request.get_json(silent=True) or {}
        min_level = (body.get("min_level") or request.args.get("min_level") or "warning").strip().lower()
        if min_level not in _VALID_LEVELS:
            raise ValidationError("invalid_min_level")
        limit = min(max(int(body.get("limit", request.args.get("limit", 20))), 1), 50)
        channels_raw = body.get("channels")
        channels = None
        if isinstance(channels_raw, list):
            channels = [str(x).strip().lower() for x in channels_raw if str(x).strip()]
        include_probes = body.get("include_probes", request.args.get("include_probes", "1")) != "0"
        respect_dedup = body.get("respect_dedup", True) is not False
        result = dispatch_service.dispatch(
            min_level=min_level,  # type: ignore[arg-type]
            limit=limit,
            channel_names=channels,
            include_system_probes=include_probes,
            respect_dedup=respect_dedup,
        )
        return ok_response(data=result.model_dump(mode="json"), count=result.sent)

    @blueprint.get("/system/alerts/summary")
    @login_required
    def system_alert_summary():
        """Compact counts for dashboard badges."""
        feed = service.list_alerts(limit=100, min_level="info")
        return ok_response(
            data={
                "total": feed.total,
                "counts_by_level": feed.counts_by_level,
                "counts_by_category": feed.counts_by_category,
                "critical_count": feed.counts_by_level.get("critical", 0),
                "warning_count": feed.counts_by_level.get("warning", 0),
            },
            count=feed.total,
        )
