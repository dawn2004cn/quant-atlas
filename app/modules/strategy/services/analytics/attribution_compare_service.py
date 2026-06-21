from __future__ import annotations

"""Compare factor-style attribution between two symbols."""

from typing import Any

from app.modules.strategy.services.analytics.unified_attribution_service import UnifiedAttributionService
from app.domain.dto.analytics_dto import AttributionCompareDTO, FactorCompareRowDTO
from app.domain.enums import MarketCode
import logging
logger = logging.getLogger(__name__)



def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


class AttributionCompareService:
    """Build side-by-side attribution comparison for benchmarking UI."""

    def __init__(
        self,
        *,
        attribution_service: UnifiedAttributionService | None = None,
        market_service: object | None = None,
    ) -> None:
        self._attribution = attribution_service or UnifiedAttributionService()
        self._market_service = market_service

    def compare(
        self,
        *,
        base_symbol: str,
        peer_symbol: str,
        market: MarketCode = MarketCode.CN,
        period: str = "30d",
        benchmark_return: float = 3.5,
    ) -> AttributionCompareDTO:
        base = base_symbol.strip().upper()
        peer = peer_symbol.strip().upper()
        base_pos = self._position_for(base, market)
        peer_pos = self._position_for(peer, market)

        base_report = self._attribution.build_report(
            strategy_name=f"{base} 对标",
            period=period,
            positions=[base_pos],
            benchmark_return=benchmark_return,
            symbol=base,
            include_slippage=False,
        )
        peer_report = self._attribution.build_report(
            strategy_name=f"{peer} 对标",
            period=period,
            positions=[peer_pos],
            benchmark_return=benchmark_return,
            symbol=peer,
            include_slippage=False,
        )

        base_map = {f.factor_name: f.contribution_pct for f in base_report.factors}
        peer_map = {f.factor_name: f.contribution_pct for f in peer_report.factors}
        names = sorted(set(base_map) | set(peer_map))
        rows: list[FactorCompareRowDTO] = []
        for name in names:
            b = float(base_map.get(name, 0.0))
            p = float(peer_map.get(name, 0.0))
            rows.append(
                FactorCompareRowDTO(
                    factor_name=name,
                    base_pct=round(b, 4),
                    peer_pct=round(p, 4),
                    delta_pct=round(b - p, 4),
                )
            )

        summary = (
            f"{base} vs {peer}：总收益 {base_report.total_return:.2f}% / "
            f"{peer_report.total_return:.2f}%，Alpha {base_report.market_effect.alpha:.2f}% / "
            f"{peer_report.market_effect.alpha:.2f}%。"
        )
        return AttributionCompareDTO(
            base_symbol=base,
            peer_symbol=peer,
            base_name=str(base_pos.get("name") or base),
            peer_name=str(peer_pos.get("name") or peer),
            market=market.value,
            period=period,
            base_total_return=round(base_report.total_return, 4),
            peer_total_return=round(peer_report.total_return, 4),
            base_alpha=round(base_report.market_effect.alpha, 4),
            peer_alpha=round(peer_report.market_effect.alpha, 4),
            base_beta=round(base_report.market_effect.beta, 4),
            peer_beta=round(peer_report.market_effect.beta, 4),
            factor_rows=rows,
            summary=summary,
        )

    def _position_for(self, symbol: str, market: MarketCode) -> dict[str, Any]:
        symbol_u = symbol.upper()
        name = symbol
        change_pct = 0.0
        sector = "未知"
        ms = self._market_service
        if ms is not None:
            try:
                rows = ms.list_quotes(market, [symbol])
                if rows:
                    q: dict[str, Any] = {}
                    chosen: dict[str, Any] | None = None
                    for raw in rows:
                        if isinstance(raw, dict):
                            candidate = raw
                        elif hasattr(raw, "model_dump"):
                            candidate = raw.model_dump()
                        elif hasattr(raw, "dict"):
                            candidate = raw.dict()
                        else:
                            continue

                        code = str(candidate.get("code") or candidate.get("symbol") or "").strip().upper()
                        if code and code == symbol_u:
                            chosen = candidate
                            break

                        if chosen is None:
                            chosen = candidate

                    if chosen is not None:
                        q = chosen
                    name = str(q.get("name") or symbol)
                    change_pct = _safe_float(q.get("change_pct"))
                    sector = str(q.get("industry") or q.get("sector") or "未知")
            except Exception:
                logger.warning("Suppressed exception", exc_info=True)
                pass
        value = 100_000.0
        pnl = value * change_pct / 100.0
        return {
            "symbol": symbol,
            "name": name,
            "value": value,
            "return_pct": change_pct,
            "pnl": pnl,
            "sector": sector,
        }
