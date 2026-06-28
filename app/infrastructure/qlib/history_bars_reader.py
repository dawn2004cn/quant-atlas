from __future__ import annotations

"""从 ``instance/qlib_bin`` 读取 A 股日 K（仅读本地 bin，不访问公网）。"""


from pathlib import Path
from typing import Any

import pandas as pd

from ...config import BASE_DIR
from ...core.logger import get_logger
from ...domain.enums import MarketCode
from .symbol_map import to_qlib_instrument

logger = get_logger(__name__)


def qlib_bin_calendar_ready(*, base_dir: Path | None = None) -> bool:
    root = Path(base_dir or BASE_DIR)
    cal = root / "instance" / "qlib_bin" / "calendars" / "day.txt"
    try:
        return cal.is_file() and cal.stat().st_size > 0
    except OSError:
        return False


def load_cn_daily_ohlcv_from_qlib_bin(
    symbol: str,
    start: str,
    end: str,
    *,
    base_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """
    使用 pyqlib ``D.features`` 从本地 ``qlib_bin`` 拉日 OHLCV；失败返回空列表。

    与 ``QlibPipelineService.unified_buy_hold_backtest`` 使用同一 ``provider_uri`` 约定。
    """
    root = Path(base_dir or BASE_DIR)
    if not qlib_bin_calendar_ready(base_dir=root):
        return []
    try:
        import qlib
        from qlib.constant import REG_CN
        from qlib.data import D
    except Exception:
        return []

    inst = to_qlib_instrument(symbol, MarketCode.CN)
    uri = str((root / "instance" / "qlib_bin").resolve())
    s0, e0 = start[:10], end[:10]
    fields = ["$open", "$high", "$low", "$close", "$volume"]
    try:
        qlib.init(provider_uri=uri, region=REG_CN)
        df = D.features([inst], fields, start_time=s0, end_time=e0, freq="day")
    except Exception as exc:
        logger.debug("qlib D.features history read failed sym=%s: %s", symbol, exc)
        return []
    if df is None or len(df) == 0:
        return []
    try:
        if inst not in df.index.get_level_values(0):
            return []
        sub = df.loc[inst]
    except Exception:
        return []

    def _row_to_bar(ts: Any, row: Any) -> dict[str, Any] | None:
        try:
            ds = pd.Timestamp(ts).strftime("%Y-%m-%d")
        except Exception:
            ds = str(ts)[:10]
        try:
            o = float(row["$open"])
            h = float(row["$high"])
            l_ = float(row["$low"])
            c = float(row["$close"])
            v = float(row["$volume"])
        except (KeyError, TypeError, ValueError):
            return None
        if not (o > 0 and c > 0):
            return None
        return {
            "date": ds,
            "open": o,
            "high": h,
            "low": l_,
            "close": c,
            "volume": v,
            "amount": 0.0,
            "Date": ds,
            "Open": o,
            "High": h,
            "Low": l_,
            "Close": c,
            "Volume": v,
            "Amount": 0.0,
        }

    out: list[dict[str, Any]] = []
    if isinstance(sub, pd.Series):
        bar = _row_to_bar(sub.name, sub)
        if bar:
            out.append(bar)
    else:
        for ts, row in sub.iterrows():
            bar = _row_to_bar(ts, row)
            if bar:
                out.append(bar)
    out.sort(key=lambda x: x["date"])
    return out
