from __future__ import annotations
"""News bundle capability with archive-backed caching."""


from datetime import datetime, timezone, timedelta
from typing import Any

from app.domain.capabilities.base import BaseCapability
from app.domain.enums import MarketCode
from app.infrastructure.capabilities.registry import capability


def _is_stale_fetched(latest_fetched_at: str | None, max_age_hours: float) -> bool:
    if not latest_fetched_at:
        return True
    try:
        dt = datetime.strptime(
            latest_fetched_at[:19], "%Y-%m-%d %H:%M:%S"
        ).replace(tzinfo=timezone.utc)
    except ValueError:
        return True
    return datetime.now(timezone.utc) - dt > timedelta(hours=max_age_hours)


def _split_news_rows(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    sym: list[dict] = []
    ind: list[dict] = []
    for r in rows:
        scope = r.get("news_scope") or r.get("scope")
        d = {k: v for k, v in r.items() if k != "news_scope"}
        if scope == "industry":
            ind.append(d)
        else:
            sym.append(d)
    return sym, ind


@capability("news_bundle")
class NewsBundleCapability(BaseCapability):
    """Bundled news with archive-backed caching & auto-refresh."""

    capability_name = "news_bundle"

    def __init__(self, **services: Any) -> None:
        self._stock_service = services.get("stock_service")
        self._archive = services.get("archive")

    def execute(
        self,
        symbol: str,
        market: MarketCode,
        *,
        force_refresh: bool = False,
        cache_max_age_hours: float = 24.0,
    ) -> dict[str, Any]:
        m = market.value
        sym = symbol
        remote_refreshed = False

        if self._archive is not None:
            latest = self._archive.latest_fetched_at(m, sym)
            stale = _is_stale_fetched(latest, cache_max_age_hours)
            if force_refresh or stale:
                snap = self._stock_service.get_news_snapshot(sym, market)
                self._archive.ingest_snapshot(
                    m, sym,
                    snap.model_dump() if hasattr(snap, "model_dump") else dict(snap),
                )
                remote_refreshed = True
            rows = self._archive.list_for_symbol(m, sym, limit=160)
            if not rows:
                snap = self._stock_service.get_news_snapshot(sym, market)
                self._archive.ingest_snapshot(
                    m, sym,
                    snap.model_dump() if hasattr(snap, "model_dump") else dict(snap),
                )
                remote_refreshed = True
            sym_news, ind_news = _split_news_rows(rows)
            meta = self._archive.get_meta(m, sym)
            company = str(meta.get("company_name") or "").strip()
            industry = str(meta.get("industry_hint") or "").strip()

            return {
                "news": sym_news,
                "industry_news": ind_news,
                "company_name_hint": company,
                "industry_hint": industry,
                "archive_total_rows": len(rows),
                "remote_refreshed": remote_refreshed,
            }
        else:
            snap = self._stock_service.get_news_snapshot(sym, market)
            sym_news = list(snap.get("news") or [])
            ind_news = list(snap.get("industry_news") or [])
            company = str(snap.get("company_name_hint") or "").strip()
            industry = str(snap.get("industry_hint") or "").strip()
            return {
                "news": sym_news,
                "industry_news": ind_news,
                "company_name_hint": company,
                "industry_hint": industry,
                "archive_total_rows": 0,
                "remote_refreshed": True,
            }
