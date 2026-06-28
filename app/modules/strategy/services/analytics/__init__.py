"""Analytics group facade — namespace package.

Only services that actually exist are re-exported here.
"""
from __future__ import annotations

from app.modules.strategy.services.analytics.attribution_service import AttributionAnalyzer

__all__ = [
    "AttributionAnalyzer",
]
