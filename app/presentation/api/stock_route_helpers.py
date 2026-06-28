from __future__ import annotations

"""Shared helpers for stock-related HTTP adapters."""

from typing import Any

from app.domain.dto.quote_factory import canonical_quote_payload
from app.domain.enums import MarketCode
from app.modules.system.services.ui.data_freshness_service import enrich_market_payload
from app.modules.system.services.ui.sector_context_service import SectorContextService


def build_sector_context(
    *,
    symbol: str,
    market: MarketCode,
    industry_chain_service: Any | None,
) -> dict[str, Any]:
    svc = industry_chain_service
    if isinstance(svc, type):
        try:
            svc = svc()
        except TypeError:
            svc = None
    return SectorContextService(industry_chain_service=svc).build_context(
        symbol,
        market,
    )


def enrich_quote_resource(resource: dict[str, Any], *, source: str = "stock_quote") -> dict[str, Any]:
    normalized = canonical_quote_payload(resource)
    return enrich_market_payload(normalized, source=source)


__all__ = ["build_sector_context", "enrich_quote_resource"]
