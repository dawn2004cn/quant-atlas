"""Post-module wiring hooks — run after ``initialize_all_modules`` completes."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def run_post_wire_hooks(services: Any) -> None:
    """Finalize services that depend on all context modules being wired."""
    _wire_recommendation_service(services)
    _wire_optimization_services(services)
    _wire_strategy_sop()


def _wire_recommendation_service(services: Any) -> None:
    try:
        from app.bootstrap_components.service_wiring import wire_recommendation_service

        wire_recommendation_service(services)
    except Exception:
        logger.warning("Recommendation service wiring failed", exc_info=True)


def _wire_optimization_services(services: Any) -> None:
    try:
        from app.bootstrap_components.wiring_optimization import wire_optimization_services

        wire_optimization_services(services)
    except Exception as exc:
        logger.debug("Optimization wiring skipped: %s", exc)


def _wire_strategy_sop() -> None:
    try:
        from app.bootstrap_components.wiring_strategy import wire_strategy_sop

        wire_strategy_sop()
    except Exception as exc:
        logger.warning("Strategy SOP wiring failed: %s", exc)


__all__ = ["run_post_wire_hooks"]
