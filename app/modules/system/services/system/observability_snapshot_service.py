"""Unified observability snapshot for observability UI and ops dashboards (Phase E)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.bootstrap_components.service_readiness import (
    CRITICAL_RESOLVE_SERVICES,
    OPTIONAL_SERVICE_ATTRS,
    REQUIRED_SERVICE_ATTRS,
)
from app.domain.compliance.retail_manifest import BETA_SLA, MANIFEST_VERSION
from app.modules.system.services.system.system_health_banner_service import (
    SystemHealthBannerService,
)
from app.modules.system.services.system.system_pulse_service import SystemPulseService


class ObservabilitySnapshotService:
    """Aggregate pulse, banner, SLA, service readiness, and review queue metrics."""

    def build_snapshot(self, ctx: Any) -> dict[str, Any]:
        pulse = SystemPulseService().build_pulse(ctx)
        quotes_api = self._quotes_api_stats()
        banner = SystemHealthBannerService().build_banner(quotes_dump=quotes_api)
        critical = self._critical_services(ctx)
        review = self._decision_review_summary()
        overall = self._overall_status(pulse.overall_status, banner, critical)

        return {
            "schema_version": "v1",
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "compliance_version": MANIFEST_VERSION,
            "overall_status": overall,
            "pulse": pulse.model_dump(),
            "health_banner": banner,
            "sla": dict(BETA_SLA),
            "critical_services": critical,
            "decision_review": review,
            "task_messages": self._task_messages(ctx, limit=40),
            "timeseries_beat_runs": self._timeseries_beat_runs(ctx, limit=12),
            "quotes_api": quotes_api,
            "alert_ops": self._alert_ops(quotes_api),
        }

    def _alert_ops(self, quotes_api: dict[str, Any]) -> dict[str, Any]:
        """Beat flags + current dump pressure for ops dashboards."""
        try:
            from app.core.runtime_config import get_runtime, get_runtime_bool, get_runtime_int

            dump_n = int(quotes_api.get("full_dump_count") or 0)
            threshold = max(1, int(get_runtime_int("QUOTES_FULL_DUMP_WARN_THRESHOLD", 1)))
            return {
                "alert_dispatch_beat": get_runtime("ALERT_DISPATCH_CELERY_BEAT", "0") == "1",
                "alert_dispatch_beat_minutes": get_runtime_int("ALERT_DISPATCH_BEAT_MINUTES", 30),
                "quotes_dump_monitor_beat": get_runtime("QUOTES_DUMP_MONITOR_CELERY_BEAT", "0") == "1",
                "quotes_dump_monitor_beat_minutes": get_runtime_int(
                    "QUOTES_DUMP_MONITOR_BEAT_MINUTES", 30
                ),
                "quotes_dump_auto_dispatch": get_runtime_bool("QUOTES_DUMP_AUTO_DISPATCH", False),
                "quotes_full_dump_count": dump_n,
                "quotes_full_dump_threshold": threshold,
                "quotes_full_dump_warn": dump_n >= threshold,
                "preferred_endpoint": "quotes/page",
            }
        except Exception:
            return {
                "alert_dispatch_beat": False,
                "quotes_dump_monitor_beat": False,
                "quotes_dump_auto_dispatch": False,
                "quotes_full_dump_warn": False,
            }

    def _quotes_api_stats(self) -> dict[str, Any]:
        try:
            from app.modules.market_data.services.quotes_dump_metrics import get_quotes_dump_stats

            return get_quotes_dump_stats()
        except Exception:
            return {
                "full_dump_count": 0,
                "symbol_batch_count": 0,
                "last_full_dump_at": None,
            }

    def _task_messages(self, ctx: Any, *, limit: int = 40) -> list[dict[str, Any]]:
        try:
            store = getattr(ctx, "task_message_store", None)
            if store is None:
                return []
            if hasattr(store, "list_recent"):
                rows = store.list_recent(limit=limit) or []
            elif hasattr(store, "list_messages"):
                rows = store.list_messages(limit=limit) or []
            elif hasattr(store, "tail"):
                rows = store.tail(limit=limit) or []
            else:
                return []
            out: list[dict[str, Any]] = []
            for row in rows[:limit]:
                if isinstance(row, dict):
                    out.append(row)
                elif hasattr(row, "model_dump"):
                    out.append(row.model_dump())
                else:
                    out.append({"detail": str(row)})
            return out
        except Exception:
            return []

    def _timeseries_beat_runs(self, ctx: Any, *, limit: int = 12) -> list[dict[str, Any]]:
        _ = ctx
        try:
            from app.infrastructure.timeseries.sync_snapshot import get_timeseries_sync_history

            rows = get_timeseries_sync_history(limit=limit, source="celery_beat") or []
            return [r for r in rows if isinstance(r, dict)][:limit]
        except Exception:
            return []

    def _critical_services(self, ctx: Any) -> dict[str, Any]:
        resolved: list[str] = []
        missing: list[str] = []
        for name in CRITICAL_RESOLVE_SERVICES:
            if getattr(ctx, name, None) is not None:
                resolved.append(name)
            else:
                missing.append(name)

        required_missing = [
            n for n in REQUIRED_SERVICE_ATTRS if getattr(ctx, n, None) is None
        ]
        optional_missing = [
            n for n in OPTIONAL_SERVICE_ATTRS if getattr(ctx, n, None) is None
        ]

        return {
            "critical_resolved": resolved,
            "critical_missing": missing,
            "required_missing": required_missing,
            "optional_missing": optional_missing,
            "ok": not missing and not required_missing,
        }

    def _decision_review_summary(self) -> dict[str, Any]:
        try:
            from app.modules.system.services.ui.decision_review_queue import get_review_queue

            return get_review_queue().product_summary()
        except Exception:
            return {
                "pending_count": 0,
                "overdue_count": 0,
                "high_priority_count": 0,
                "sla_hours": BETA_SLA.get("decision_review_sla_hours", 24),
                "cta": "",
                "oldest_pending_at": None,
            }

    def _overall_status(
        self,
        pulse_status: str,
        banner: dict[str, Any],
        critical: dict[str, Any],
    ) -> str:
        if banner.get("level") == "critical" or not critical.get("ok"):
            return "critical"
        if pulse_status in ("degraded", "critical") or banner.get("level") == "warning":
            return "degraded"
        if critical.get("optional_missing"):
            return "degraded"
        return "ok"
