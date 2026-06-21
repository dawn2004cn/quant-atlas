#!/usr/bin/env python3
"""Pytdx 冒烟：拉取行情 / 日K / 财务。用法: python scripts/pytdx_smoke.py [symbol]"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.modules.data.services.pytdx_market_data_service import get_pytdx_market_data_service


def main() -> None:
    symbol = (sys.argv[1] if len(sys.argv) > 1 else "600519").strip()
    svc = get_pytdx_market_data_service()
    if not svc.is_available():
        print("pytdx 未安装: pip install pytdx")
        sys.exit(1)

    hq = svc.connection_status().get("hq", {})
    print(f"HQ connected={hq.get('connected')} server={hq.get('server')}")

    quotes = svc.get_quotes([symbol, "000001"])
    for q in quotes:
        print(f"  quote {q.get('code')}: price={q.get('price')} vol={q.get('vol')}")

    bars = svc.get_daily_bars(symbol, count=3)
    for b in bars:
        print(f"  bar {b.get('datetime')}: close={b.get('close')}")

    fin = svc.get_finance_info(symbol)
    if fin:
        print(
            f"  finance: date={fin.get('updated_date')} "
            f"revenue={fin.get('zhuyingshouru')} profit={fin.get('jinglirun')}"
        )
    else:
        print("  finance: (empty)")


if __name__ == "__main__":
    main()
