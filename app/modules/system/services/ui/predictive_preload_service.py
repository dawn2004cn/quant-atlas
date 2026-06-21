from __future__ import annotations

"""Build lightweight preload plans for likely next user actions."""

from typing import Any


class PredictivePreloadService:
    """Suggest nearby stock APIs to prefetch from a sector or watch context."""

    def __init__(self, *, hot_sector_storage_service: Any = None) -> None:
        self._hot_sector_storage_service = hot_sector_storage_service

    def build_sector_plan(
        self,
        *,
        sector_code: str,
        market: str = "CN",
        limit: int = 5,
        source: str = "auto",
        sector_name: str | None = None,
        board_kind: str = "concept",
        provider: str | None = None,
    ) -> dict[str, Any]:
        candidates = self._sector_members(
            sector_code=sector_code,
            limit=limit,
            source=source,
            sector_name=sector_name,
            board_kind=board_kind,
            provider=provider,
        )
        return {
            "context": {
                "type": "sector",
                "sector_code": sector_code,
                "sector_name": sector_name or "",
                "market": market,
            },
            "candidates": candidates,
            "prefetch": [self._prefetch_entry(item, market) for item in candidates],
            "policy": {
                "max_parallel": 2,
                "trigger": "idle",
                "ttl_seconds": 180,
            },
        }

    def _sector_members(
        self,
        *,
        sector_code: str,
        limit: int,
        source: str,
        sector_name: str | None,
        board_kind: str,
        provider: str | None,
    ) -> list[dict[str, Any]]:
        if self._hot_sector_storage_service is None:
            return []
        rows, mode = self._hot_sector_storage_service.resolve_members(
            sector_code,
            limit=limit,
            source=source,
            board_kind=board_kind,
            sector_name=sector_name,
            provider=provider,
        )
        candidates = []
        for idx, row in enumerate(rows or []):
            item = dict(row)
            symbol = self._symbol_from(item)
            if not symbol:
                continue
            candidates.append(
                {
                    "rank": idx + 1,
                    "symbol": symbol,
                    "name": item.get("name") or item.get("stock_name") or item.get("symbol_name") or symbol,
                    "reason": item.get("reason") or item.get("sector_name") or "sector member",
                    "source_mode": mode,
                }
            )
        return candidates[:limit]

    @staticmethod
    def _prefetch_entry(item: dict[str, Any], market: str) -> dict[str, Any]:
        symbol = item["symbol"]
        return {
            "symbol": symbol,
            "priority": item.get("rank", 99),
            "urls": [
                f"/api/v1/stocks/{market}/{symbol}",
                f"/api/v1/stocks/{market}/{symbol}/attribution-timeline?limit=30",
                f"/api/v1/strategy/copilot?symbol={symbol}&market={market}",
            ],
        }

    @staticmethod
    def _symbol_from(row: dict[str, Any]) -> str:
        raw = row.get("symbol") or row.get("code") or row.get("stock_code") or row.get("ts_code") or ""
        text = str(raw).strip()
        if ":" in text:
            text = text.split(":")[-1]
        if len(text) >= 8 and text[:2].lower() in {"sh", "sz", "bj"}:
            text = text[2:]
        return text.upper()


__all__ = ["PredictivePreloadService"]
