"""Bootstrap service readiness tiers and validation."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ServiceTier(str, Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    FEATURE_FLAG = "feature_flag"


# Core API / index pages — startup should wire these in normal deployments.
REQUIRED_SERVICE_ATTRS: tuple[str, ...] = (
    "market_service",
    "stock_service",
    "watchlist_service",
    "stock_group_service",
)

# Wired when possible; routes use @service_fallback / deps_service_fallback if missing.
OPTIONAL_SERVICE_ATTRS: tuple[str, ...] = (
    "data_infrastructure_service",
    "user_lifecycle_service",
    "risk_service",
    "integration_stack_service",
    "research_report_rag_service",
    "global_market_service",
    "recommendation_service",
    "strategy_shadow_service",
    "ten_kings_sniper_service",
    "watchlist_agent_service",
    "user_knowledge_service",
    "ai_committee_service",
    "self_healing_execution_service",
    "manifest_service_10",
    "perception_resonance_service",
    "evolution_arbiter_service",
)

# Gated by AppSettings / env (qlib, rdagent, etc.) — never fail bootstrap.
FEATURE_FLAG_SERVICE_ATTRS: tuple[str, ...] = (
    "qlib_pipeline_service",
    "rdagent_run_service",
    "strategy_optimization_service",
)

# Workbench / retail critical path — resolved via factory at boot (Phase A).
CRITICAL_RESOLVE_SERVICES: tuple[str, ...] = (
    "daily_workbench_service",
    "market_service",
    "recommendation_service",
    "task_message_store",
)


@dataclass(frozen=True)
class ServiceReadinessReport:
    missing_required: tuple[str, ...]
    missing_optional: tuple[str, ...]
    strict: bool

    @property
    def ok(self) -> bool:
        return not self.missing_required

    def raise_if_strict(self) -> None:
        if self.strict and self.missing_required:
            raise RuntimeError(
                "Bootstrap missing REQUIRED services: "
                + ", ".join(self.missing_required)
            )


def is_strict_bootstrap() -> bool:
    val = os.environ.get("STRICT_BOOTSTRAP", "").strip().lower()
    if val:
        return val in ("1", "true", "yes", "on")
    # Default: strict in production/staging, lenient in development
    deploy = os.environ.get("FLASK_ENV", os.environ.get("APP_ENV", "development"))
    if deploy in ("production", "staging"):
        return True
    return False


def validate_service_readiness(services: Any, *, strict: bool | None = None) -> ServiceReadinessReport:
    """Check REQUIRED services; log OPTIONAL gaps."""
    if strict is None:
        strict = is_strict_bootstrap()

    missing_required = tuple(
        name for name in REQUIRED_SERVICE_ATTRS if getattr(services, name, None) is None
    )
    missing_optional = tuple(
        name for name in OPTIONAL_SERVICE_ATTRS if getattr(services, name, None) is None
    )

    if missing_required:
        logger.error("REQUIRED services missing: %s", ", ".join(missing_required))
    elif missing_optional:
        logger.debug("OPTIONAL services not wired: %s", ", ".join(missing_optional))

    report = ServiceReadinessReport(
        missing_required=missing_required,
        missing_optional=missing_optional,
        strict=strict,
    )
    report.raise_if_strict()
    return report


def inspect_service_readiness(services: Any) -> ServiceReadinessReport:
    """Inspect readiness without raising (for health/observability endpoints)."""
    missing_required = tuple(
        name for name in REQUIRED_SERVICE_ATTRS if getattr(services, name, None) is None
    )
    missing_optional = tuple(
        name for name in OPTIONAL_SERVICE_ATTRS if getattr(services, name, None) is None
    )
    return ServiceReadinessReport(
        missing_required=missing_required,
        missing_optional=missing_optional,
        strict=False,
    )


def build_public_health_payload(services: Any) -> dict[str, Any]:
    """Public liveness JSON — ``status`` stays ``ok`` when HTTP handler is up."""
    report = inspect_service_readiness(services)
    critical_missing = [
        name for name in CRITICAL_RESOLVE_SERVICES if getattr(services, name, None) is None
    ]
    if report.missing_required or critical_missing:
        deployment_status = "critical"
    elif report.missing_optional:
        deployment_status = "degraded"
    else:
        deployment_status = "ok"

    return {
        "status": "ok",
        "deployment_status": deployment_status,
        "services": {
            "required_missing": list(report.missing_required),
            "optional_missing": list(report.missing_optional),
            "critical_missing": critical_missing,
        },
    }


@dataclass(frozen=True)
class CriticalResolveReport:
    missing: tuple[str, ...]
    resolved: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.missing


def resolve_all_critical_services(registry: Any, *, strict: bool | None = None) -> CriticalResolveReport:
    """Eagerly resolve workbench-critical factories; log ERROR on None."""
    if strict is None:
        strict = is_strict_bootstrap()

    resolved: list[str] = []
    missing: list[str] = []
    for name in CRITICAL_RESOLVE_SERVICES:
        try:
            svc = registry.get_or_none(name)
            if svc is None and hasattr(registry, "get"):
                try:
                    svc = registry.get(name)
                except Exception:
                    svc = None
        except Exception as exc:
            logger.error("Critical service resolve failed for %s: %s", name, exc, exc_info=True)
            svc = None
        if svc is None:
            missing.append(name)
            logger.error("CRITICAL service unresolved: %s", name)
        else:
            resolved.append(name)
            logger.info("Critical service ready: %s (%s)", name, type(svc).__name__)

    report = CriticalResolveReport(missing=tuple(missing), resolved=tuple(resolved))
    if strict and missing:
        raise RuntimeError("Bootstrap missing CRITICAL services: " + ", ".join(missing))
    return report
