from __future__ import annotations

"""TDX 在线财务快照（pytdx get_finance_info）。"""


from dataclasses import dataclass
from typing import Any

from ..mappers.symbol_normalizer import SymbolNormalizer
from .tdx_manager import TdxConnectionManager


@dataclass(frozen=True)
class TdxFinanceSnapshot:
    symbol: str  # sh600519 / sz000001 / bj830001
    report_date: str  # yyyymmdd or yyyymm
    total_shares: float
    float_shares: float
    eps: float
    bps: float
    net_profit: float
    revenue: float
    raw: dict[str, Any]


def _tdx_market_code_from_symbol(db_symbol: str) -> int:
    # 仅支持 A 股：sz=0, sh=1；bj 暂不支持 pytdx 财务接口
    cn = SymbolNormalizer.to_db_code(db_symbol, market="CN")
    raw = cn.split(":", 1)[1] if ":" in cn else cn
    mkt = raw[:2].lower() if len(raw) >= 2 else "sz"
    if mkt == "sh":
        return 1
    if mkt == "sz":
        return 0
    return -1


def fetch_tdx_finance_snapshot(symbol: str, *, manager: TdxConnectionManager | None = None) -> TdxFinanceSnapshot | None:
    """抓取单标的财务快照；失败返回 None（由上层记录/跳过）。"""
    mgr = manager or TdxConnectionManager()
    cn = SymbolNormalizer.to_db_code(symbol, market="CN")
    raw_sym = cn.split(":", 1)[1] if ":" in cn else cn
    market_code = _tdx_market_code_from_symbol(cn)
    if market_code < 0:
        return None
    code6 = raw_sym[-6:]
    data = mgr.execute("get_finance_info", market_code, code6) or {}
    if not isinstance(data, dict) or not data:
        return None

    report_date = str(
        data.get("updated_date") or data.get("updatedate") or ""
    ).strip()
    if not report_date:
        report_date = "unknown"
    revenue = float(
        data.get("zhuyingshouru") or data.get("zhuyingyewushouru") or 0
    )
    eps = float(data.get("meigushouyi") or 0)
    return TdxFinanceSnapshot(
        symbol=cn,
        report_date=report_date,
        total_shares=float(data.get("zongguben") or 0),
        float_shares=float(data.get("liutongguben") or 0),
        eps=eps,
        bps=float(data.get("meigujingzichan") or 0),
        net_profit=float(data.get("jinglirun") or 0),
        revenue=revenue,
        raw=dict(data),
    )

