from __future__ import annotations
"""Infrastructure adapter for ``TdxFinancePort``."""

from app.domain.ports.tdx_finance_port import TdxFinancePort, TdxFinanceSnapshot
from app.infrastructure.external.tdx_finance import fetch_tdx_finance_snapshot as _fetch


class TdxFinancePortAdapter(TdxFinancePort):
    def fetch_snapshot(self, symbol: str) -> TdxFinanceSnapshot | None:
        snap = _fetch(symbol)
        if snap is None:
            return None
        return TdxFinanceSnapshot(
            symbol=snap.symbol,
            report_date=snap.report_date,
            total_shares=snap.total_shares,
            float_shares=snap.float_shares,
            eps=snap.eps,
            bps=snap.bps,
            net_profit=snap.net_profit,
            revenue=snap.revenue,
            raw=snap.raw,
        )
