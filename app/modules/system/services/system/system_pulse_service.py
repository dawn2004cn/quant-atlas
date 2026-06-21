from __future__ import annotations

from typing import Any

from app.domain.dto.system_pulse_dto import SystemPulseComponentDTO, SystemPulseDTO
from app.domain.verification import list_pending


class SystemPulseService:
    """Build a UI-friendly health snapshot without performing expensive probes."""

    def build_pulse(self, ctx: Any) -> SystemPulseDTO:
        components = [
            self._component(
                "mysql",
                "MySQL",
                "ok" if self._has_mysql(ctx) else "unknown",
                "repository-backed services detected" if self._has_mysql(ctx) else "no live database probe configured",
                "check MYSQL_* settings and repository wiring",
            ),
            self._component(
                "redis",
                "Redis / task messages",
                "ok" if getattr(getattr(ctx, "task_message_store", None), "enabled_backend", "") == "redis" else "degraded",
                f"backend={getattr(getattr(ctx, 'task_message_store', None), 'enabled_backend', 'none')}",
                "set TASK_MESSAGE_REDIS_URL or CELERY_BROKER_URL for durable progress",
            ),
            self._component(
                "celery",
                "Celery",
                "ok" if getattr(ctx, "enable_celery", False) else "degraded",
                "enabled" if getattr(ctx, "enable_celery", False) else "disabled in current runtime",
                "enable Celery for long-running workflow execution",
            ),
            self._component(
                "tdx",
                "TDX",
                "ok" if getattr(ctx, "tdx_base_read_service", None) else "unknown",
                "read service wired" if getattr(ctx, "tdx_base_read_service", None) else "read service not wired",
                "verify TDX data path and base data service wiring",
            ),
            self._component(
                "llm",
                "LLM / AI",
                "ok" if self._has_ai(ctx) else "degraded",
                "AI service available" if self._has_ai(ctx) else "AI service unavailable or adapter not configured",
                "configure LLM provider before running AI research workflows",
            ),
            self._component(
                "capabilities",
                "Capability Registry",
                "ok" if self._capabilities(ctx) else "degraded",
                f"{len(self._capabilities(ctx))} capabilities registered",
                "check infrastructure capability decorators",
                {"items": self._capabilities(ctx)},
            ),
            self._truth_sentry_component(),
        ]
        overall = self._overall_status(components)
        return SystemPulseDTO(overall_status=overall, components=components)

    def _component(
        self,
        component_id: str,
        label: str,
        status: str,
        detail: str,
        remedy: str,
        meta: dict[str, Any] | None = None,
    ) -> SystemPulseComponentDTO:
        return SystemPulseComponentDTO(
            id=component_id,
            label=label,
            status=status,
            detail=detail,
            remedy=remedy,
            meta=meta or {},
        )

    def _has_mysql(self, ctx: Any) -> bool:
        return any(
            getattr(ctx, name, None) is not None
            for name in (
                "basic_market_data_service",
                "signal_observation_service",
                "investment_manager_service",
            )
        )

    def _has_ai(self, ctx: Any) -> bool:
        return any(
            getattr(ctx, name, None) is not None
            for name in (
                "ai_analysis_service",
                "ai_research_service",
                "fingpt_application_service",
                "investment_committee_service",
            )
        )

    def _capabilities(self, ctx: Any) -> list[str]:
        facade = getattr(ctx, "tool_facade_service", None)
        if facade is None or not hasattr(facade, "list_capabilities"):
            return []
        try:
            return sorted(facade.list_capabilities())
        except Exception:
            return []

    def _truth_sentry_component(self) -> SystemPulseComponentDTO:
        pending = list_pending()
        count = len(pending)
        if count == 0:
            return self._component(
                "truth_sentry",
                "Truth Sentry",
                "ok",
                "多源数据一致，无待验证分析",
                "TruthSentry 监听 MarketDataUpdatedEvent",
            )
        return self._component(
            "truth_sentry",
            "Truth Sentry",
            "degraded",
            f"{count} 个标的分析待验证（TDX/Qlib 偏差）",
            "检查 /api/v1/data/compare-sources 或等待数据同步",
            {"pending": pending},
        )

    def _overall_status(self, components: list[SystemPulseComponentDTO]) -> str:
        statuses = {item.status for item in components}
        if "unavailable" in statuses:
            return "unavailable"
        if "degraded" in statuses:
            return "degraded"
        return "ok"

