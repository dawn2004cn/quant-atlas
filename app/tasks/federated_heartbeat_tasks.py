from __future__ import annotations

"""Celery task: periodic federated cluster stale-node scan."""

from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


def run_federated_cluster_scan(*, mark_inactive: bool = True) -> dict[str, Any]:
    """Detect stale deployment nodes and optionally mark them inactive."""
    from app.modules.system.services.institution_tier_service import FederatedDeploymentService

    svc = FederatedDeploymentService()
    return svc.scan_cluster_health(mark_inactive=mark_inactive)


from app.celery_app import celery as _celery

if _celery is not None:

    @_celery.task(bind=True, name="federated.cluster_health_scan")
    def federated_cluster_health_scan_task(self, mark_inactive: bool = True) -> dict[str, Any]:
        return run_federated_cluster_scan(mark_inactive=mark_inactive)

else:
    federated_cluster_health_scan_task = None  # type: ignore[misc, assignment]


__all__ = ["federated_cluster_health_scan_task", "run_federated_cluster_scan"]
