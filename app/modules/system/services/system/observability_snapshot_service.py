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
        banner = SystemHealthBannerService().build_banner()
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
        }

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
        return "ok"
