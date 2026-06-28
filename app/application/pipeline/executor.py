from __future__ import annotations

"""Quant pipeline execution and orchestration."""

from typing import Any

from app.core.events import market_data_synced
from app.core.logger import get_logger

logger = get_logger(__name__)


def handle_market_data_sync(sender: Any, stats: dict[str, Any]) -> None:
    """Event listener: Triggers subsequent analysis after data sync."""
    logger.info("Received market-data-synced event. Sync Stats: %s", stats)
    try:
        from flask import current_app, has_app_context

        ai_service = None
        if has_app_context():
            bundle = current_app.extensions.get("service_bundle")
            ai_service = getattr(bundle, "ai_analysis_service", None) if bundle else None
            if ai_service is None:
                logger.debug("ai_analysis_service not wired; skip post-sync pipeline")
                return
        logger.info(
            "AI analysis pipeline hook (stubbed; service=%s)",
            type(ai_service).__name__ if ai_service else "none",
        )
    except Exception as exc:
        logger.error("Pipeline execution failed: %s", exc)


market_data_synced.connect(handle_market_data_sync)
