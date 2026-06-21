from __future__ import annotations

"""Build shareable focus context (symbol + market) for cross-page navigation."""

from app.domain.dto.focus_context_dto import FocusContextDTO, FocusShareLinkDTO
from app.domain.enums import MarketCode
from app.domain.shared.symbol_normalizer import SymbolNormalizer

_SHARE_TEMPLATES: tuple[tuple[str, str, str], ...] = (
    ("stock_detail", "个股详情", "/stock/{symbol}?m={market}"),
    ("ai_analysis", "AI 诊股", "/ai-analysis?symbol={symbol}&market={market}"),
    ("daily_workbench", "操盘台", "/?symbol={symbol}&market={market}"),
    ("backtest", "策略回测", "/backtest?symbol={symbol}&market={market}"),
    ("attribution", "归因看板", "/attribution-dashboard?symbol={symbol}&market={market}"),
)


class FocusContextService:
    """Resolve normalized focus + quick navigation links."""

    @staticmethod
    def normalize_symbol(symbol: str, market: MarketCode) -> str:
        raw = (symbol or "").strip().upper()
        if not raw:
            return ""
        if market == MarketCode.CN:
            code6 = SymbolNormalizer.normalize_code(raw)
            return code6 or raw
        return raw

    def build_context(self, symbol: str, market: MarketCode | str = MarketCode.CN) -> FocusContextDTO:
        mkt = market if isinstance(market, MarketCode) else MarketCode(str(market or "CN").upper())
        sym = self.normalize_symbol(symbol, mkt)
        links: list[FocusShareLinkDTO] = []
        if sym:
            for page, label, tmpl in _SHARE_TEMPLATES:
                links.append(
                    FocusShareLinkDTO(
                        page=page,
                        label=label,
                        href=tmpl.format(symbol=sym, market=mkt.value),
                    )
                )
        query = f"symbol={sym}&market={mkt.value}" if sym else ""
        return FocusContextDTO(
            symbol=sym,
            market=mkt.value,
            query_string=query,
            share_links=links,
        )


__all__ = ["FocusContextService"]
