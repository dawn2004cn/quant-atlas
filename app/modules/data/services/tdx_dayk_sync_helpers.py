from __future__ import annotations

"""Tdx 日 K 同步纯函数辅助（无服务状态依赖）。"""

from pathlib import Path
from typing import Any

from app.core.runtime_config import get_runtime_int
from app.domain.shared.symbol_normalizer import SymbolNormalizer
from app.domain.shared.tdx_paths import TdxLocalPaths


def scan_cn_codes_from_tdx_dayk(tdx_root: Path) -> list[str]:
    """扫描 TDX dayk 目录获取所有股票代码."""
    paths = TdxLocalPaths(Path(tdx_root).resolve())
    out: set[str] = set()
    for sub, prefix in (("sh", "sh"), ("sz", "sz"), ("bj", "bj")):
        day_dir = paths.root / "vipdoc" / sub / "lday"
        if not day_dir.is_dir():
            continue
        for path in day_dir.glob(f"{prefix}[0-9]*.day"):
            stem = path.stem.lower()
            code = stem.replace(prefix, "")[-6:]
            if code.isdigit():
                out.add(f"{prefix}{code}")
    return sorted(out)


def normalize_ohlcv_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """规范化行情数据行，去重并按日期排序."""
    by_date: dict[str, dict[str, Any]] = {}
    for row in rows:
        date_str = str(row.get("date") or "")[:10]
        if not date_str:
            continue
        row_dict: dict[str, Any] = {"date": date_str}
        for key, value in row.items():
            if key == "date":
                continue
            if value is None:
                row_dict[key] = 0.0
            elif key in ("volume", "amount"):
                row_dict[key] = int(float(value))
            else:
                row_dict[key] = float(value)
        by_date[date_str] = row_dict
    return sorted(by_date.values(), key=lambda item: item["date"])


def cap_mysql_sync_workers(requested: int) -> int:
    pool_cap = get_runtime_int("DB_POOL_SIZE", 5) + get_runtime_int("DB_MAX_OVERFLOW", 10)
    hard_cap = max(1, get_runtime_int("TDX_MYSQL_MAX_WORKERS", min(3, pool_cap - 1)))
    return max(1, min(int(requested), hard_cap, max(1, pool_cap - 1)))


def cap_timescale_sync_workers(requested: int) -> int:
    hard_cap = max(1, get_runtime_int("TIMESCALE_MAX_WORKERS", 2))
    return max(1, min(int(requested), hard_cap))


def is_transient_conn_error(message: str) -> bool:
    msg = (message or "").lower()
    needles = (
        "connection is lost",
        "server closed the connection",
        "network is unreachable",
        "consuming input failed",
        "connection failed",
        "could not connect",
        "connection refused",
    )
    return any(needle in msg for needle in needles)


def qlib_instrument_for(cn_symbol: str) -> str:
    sym = SymbolNormalizer.normalize_cn_symbol(cn_symbol)
    if sym.startswith("sh"):
        return f"SH{sym[-6:]}"
    if sym.startswith("bj"):
        return f"BJ{sym[-6:]}"
    return f"SZ{sym[-6:]}"
