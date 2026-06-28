from __future__ import annotations

"""System Health Check Service.

Provides comprehensive health checks for all system components.
"""


from dataclasses import dataclass
from datetime import datetime

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class HealthStatus:
    """Health status of a component."""
    name: str
    status: str  # "healthy", "degraded", "unhealthy"
    message: str = ""
    details: dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class SystemHealth:
    """Overall system health."""
    overall_status: str
    timestamp: str
    components: list[HealthStatus]
    version: str = "1.0.0"

    @property
    def is_healthy(self) -> bool:
        return self.overall_status == "healthy"

    @property
    def is_degraded(self) -> bool:
        return self.overall_status == "degraded"


class HealthCheckService:
    """Service for checking system health."""

    def __init__(self):
        self._checks: dict[str, callable] = {}
        self._register_default_checks()
        logger.info("HealthCheckService initialized")

    def _register_default_checks(self) -> None:
        """Register default health checks."""
        self.register("domain", self._check_domain)
        self.register("aggregates", self._check_aggregates)
        self.register("events", self._check_events)
        self.register("cqrs", self._check_cqrs)
        self.register("cache", self._check_cache)
        self.register("monitoring", self._check_monitoring)

    def register(self, name: str, check_fn: callable) -> None:
        """Register a health check."""
        self._checks[name] = check_fn
        logger.debug(f"Registered health check: {name}")

    def check_all(self) -> SystemHealth:
        """Run all health checks."""
        components = []
        statuses = []

        for name, check_fn in self._checks.items():
            try:
                status = check_fn()
                components.append(status)
                statuses.append(status.status)
            except Exception as e:
                logger.error(f"Health check {name} failed: {e}")
                components.append(HealthStatus(
                    name=name,
                    status="unhealthy",
                    message=str(e)
                ))
                statuses.append("unhealthy")

        # Determine overall status
        if "unhealthy" in statuses:
            overall = "unhealthy"
        elif "degraded" in statuses:
            overall = "degraded"
        else:
            overall = "healthy"

        return SystemHealth(
            overall_status=overall,
            timestamp=datetime.now().isoformat(),
            components=components
        )

    def check_one(self, name: str) -> HealthStatus | None:
        """Check a specific component."""
        if name not in self._checks:
            return None

        try:
            return self._checks[name]()
        except Exception as e:
            logger.error(f"Health check {name} failed: {e}")
            return HealthStatus(
                name=name,
                status="unhealthy",
                message=str(e)
            )

    def _check_domain(self) -> HealthStatus:
        """Check domain services."""
        try:
            from app.application.domain_facade import get_domain_facade
            facade = get_domain_facade()

            # Test screening service
            facade.screen_stocks([], {})

            return HealthStatus(
                name="domain",
                status="healthy",
                message="Domain services operational",
                details={"screening": "ok"}
            )
        except Exception as e:
            return HealthStatus(
                name="domain",
                status="unhealthy",
                message=str(e)
            )

    def _check_aggregates(self) -> HealthStatus:
        """Check aggregate registry."""
        try:
            from app.application.aggregate_registry import get_aggregate_registry
            registry = get_aggregate_registry()
            stats = registry.get_stats()

            return HealthStatus(
                name="aggregates",
                status="healthy",
                message="Aggregates operational",
                details=stats
            )
        except Exception as e:
            return HealthStatus(
                name="aggregates",
                status="unhealthy",
                message=str(e)
            )

    def _check_events(self) -> HealthStatus:
        """Check event bus."""
        try:
            from app.domain.events.handlers import get_event_bus
            bus = get_event_bus()

            return HealthStatus(
                name="events",
                status="healthy",
                message="Event bus operational",
                details={"event_count": bus.event_count}
            )
        except Exception as e:
            return HealthStatus(
                name="events",
                status="unhealthy",
                message=str(e)
            )

    def _check_cqrs(self) -> HealthStatus:
        """Check CQRS mediator."""
        try:
            from app.application.mediator import get_mediator
            mediator = get_mediator()

            return HealthStatus(
                name="cqrs",
                status="healthy",
                message="CQRS operational",
                details={
                    "commands": len(mediator._command_handlers),
                    "queries": len(mediator._query_handlers)
                }
            )
        except Exception as e:
            return HealthStatus(
                name="cqrs",
                status="unhealthy",
                message=str(e)
            )

    def _check_cache(self) -> HealthStatus:
        """Check caching system."""
        try:
            from app.application.performance import get_domain_cache
            get_domain_cache()

            return HealthStatus(
                name="cache",
                status="healthy",
                message="Cache operational"
            )
        except Exception as e:
            return HealthStatus(
                name="cache",
                status="degraded",
                message=str(e)
            )

    def _check_monitoring(self) -> HealthStatus:
        """Check monitoring system."""
        try:
            from app.application.monitoring import get_metrics_collector
            get_metrics_collector()

            return HealthStatus(
                name="monitoring",
                status="healthy",
                message="Monitoring operational"
            )
        except Exception as e:
            return HealthStatus(
                name="monitoring",
                status="degraded",
                message=str(e)
            )


# Global instance
_health_check_service: HealthCheckService | None = None


def get_health_check_service() -> HealthCheckService:
    """Get global health check service."""
    global _health_check_service
    if _health_check_service is None:
        _health_check_service = HealthCheckService()
    return _health_check_service


__all__ = [
    "HealthStatus",
    "SystemHealth",
    "HealthCheckService",
    "get_health_check_service",
]
