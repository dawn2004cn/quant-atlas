from __future__ import annotations

"""Industry drill-down context for stock detail pages."""

from typing import Any

from app.domain.enums import MarketCode


class SectorContextService:
    """Resolve industry-chain navigation payloads for a symbol."""

    def __init__(self, *, industry_chain_service: Any = None) -> None:
        self._industry_chain_service = industry_chain_service

    def build_context(self, symbol: str, market: MarketCode | str = MarketCode.CN) -> dict[str, Any]:
        mkt = market if isinstance(market, MarketCode) else MarketCode(str(market or "CN").upper())
        sym = str(symbol or "").strip().upper()
        if self._industry_chain_service is None or not sym:
            return self._empty(sym, mkt.value, "industry_chain_service_unavailable")

        raw = self._call_chain_service(sym, mkt)
        if not raw or raw.get("ok") is False:
            return self._empty(sym, mkt.value, raw.get("error", "sector_context_unavailable") if raw else "")

        chain = raw.get("chain") or raw.get("chain_id") or ""
        chain_name = raw.get("chain_name") or raw.get("name") or chain
        related = raw.get("related_symbols") or []
        return {
            "symbol": sym,
            "market": mkt.value,
            "chain": chain,
            "chain_name": chain_name,
            "nodes": {
                "upstream": raw.get("upstream") or [],
                "downstream": raw.get("downstream") or [],
                "related_symbols": related,
            },
            "navigation": {
                "industry_chain": f"/industry-chain?symbol={sym}&market={mkt.value}",
                "industry_panorama": f"/industry-chain?chain={chain}&market={mkt.value}",
                "peer_compare": [
                    f"/stock/{peer}?m={mkt.value}"
                    for peer in related[:5]
                    if str(peer).strip().upper() != sym
                ],
            },
            "chain_effects": raw.get("chain_effects") or {},
            "visualization": raw.get("visualization") or "",
        }

    def _call_chain_service(self, symbol: str, market: MarketCode) -> dict[str, Any]:
        svc = self._industry_chain_service
        if hasattr(svc, "build_chain"):
            return self._to_dict(svc.build_chain(symbol=symbol, market=market))
        if hasattr(svc, "get_chain_map"):
            return self._to_dict(svc.get_chain_map(symbol=symbol, market=market))
        return {}

    @staticmethod
    def _to_dict(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if hasattr(value, "model_dump"):
            return value.model_dump()
        if hasattr(value, "dict"):
            return value.dict()
        return dict(getattr(value, "__dict__", {}) or {})

    @staticmethod
    def _empty(symbol: str, market: str, reason: str = "") -> dict[str, Any]:
        return {
            "symbol": symbol,
            "market": market,
            "chain": "",
            "chain_name": "",
            "nodes": {"upstream": [], "downstream": [], "related_symbols": []},
            "navigation": {},
            "chain_effects": {},
            "visualization": "",
            "warning": reason,
        }


__all__ = ["SectorContextService"]
