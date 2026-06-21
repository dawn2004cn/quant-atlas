#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""兼容入口：请优先使用 ``run_tdx_full_sync_all.py``（含 MySQL/Timescale/CSV/因子/qlib）。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    target = _ROOT / "scripts" / "run_tdx_full_sync_all.py"
    argv = [sys.executable, str(target), *sys.argv[1:]]
    if "--skip-qlib-bin" not in sys.argv and "--swap-tables" not in sys.argv:
        argv.append("--skip-qlib-bin")
    print("Note: use scripts/run_tdx_full_sync_all.py --swap-tables for full pipeline", file=sys.stderr)
    return subprocess.call(argv)


if __name__ == "__main__":
    raise SystemExit(main())
