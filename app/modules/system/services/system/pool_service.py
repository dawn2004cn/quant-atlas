from __future__ import annotations

"""Intraday dynamic stock pool service."""


from datetime import datetime

from app.domain.dto.pool_dto import PoolItemDTO, PoolResponseDTO
from app.domain.enums import MarketCode


class PoolApplicationService:
    """Builds realtime stock pools from market + strategy outputs."""

    def __init__(self, market_service, strategy_service):
        self._market_service = market_service
        self._strategy_service = strategy_service

    def get_live_pool(self, market: MarketCode, top_n: int = 20) -> PoolResponseDTO:
        strategy_payload = self._strategy_service.select_stocks("smart", market, top_n)
        symbols = [item.get("code", "") for item in strategy_payload.get("candidates", [])]
        quotes = self._market_service.list_quotes(market, symbols)
        quote_map = {q.code: q for q in quotes}

        rows = []
        for idx, candidate in enumerate(strategy_payload.get("candidates", []), start=1):
            code = candidate.get("code", "")
            q = quote_map.get(code)
            rows.append(
                PoolItemDTO(
                    rank=idx,
                    code=code,
                    name=candidate.get("name", ""),
                    score=float(candidate.get("score", 0)),
                    change_pct=float(q.change_pct) if q else 0.0,
                    price=float(q.price) if q else 0.0,
                    status="new" if idx <= 5 else "watch",
                    reason=candidate.get("reason", ""),
                )
            )
        return PoolResponseDTO(
            market=market.value,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            count=len(rows),
            pool=rows,
        )
