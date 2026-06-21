#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TDX lday + xdxr 重灌 MySQL 三张日 K 表（默认影子表 ``*_new``，灌完后可原子切换）。

用法（项目根目录，重灌前请停 Celery Beat / 增量任务）：
  python scripts/run_tdx_reload_mysql_history.py
  python scripts/run_tdx_reload_mysql_history.py --workers 3 --limit 50
  python scripts/run_tdx_reload_mysql_history.py --swap-tables
  python scripts/run_tdx_reload_mysql_history.py --table-suffix ""   # 直接写生产表（须为空表）

切换前请确认 ``stock_history_sh_new`` 等行数合理；``--swap-tables`` 将生产表改名为 ``*_old``。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")


def main() -> int:
    parser = argparse.ArgumentParser(description="Reload MySQL stock_history_* from TDX lday+xdxr")
    parser.add_argument("--table-suffix", default="_new", help="目标表后缀，默认 _new")
    parser.add_argument("--workers", type=int, default=None, help="MySQL 写入并发，默认 TDX_MYSQL_SYNC_WORKERS=3")
    parser.add_argument("--limit", type=int, default=None, help="仅处理前 N 只（冒烟）")
    parser.add_argument("--swap-tables", action="store_true", help="重灌成功后 RENAME 切换到生产表")
    parser.add_argument("--with-timescale", action="store_true", help="同时双写 Timescale")
    parser.add_argument("--with-csv", action="store_true", help="同时写 qlib_export CSV")
    parser.add_argument("--dump-qlib-bin", action="store_true", help="结束后 dump qlib_bin")
    args = parser.parse_args()

    from app.bootstrap_components.infrastructure_binding import bind_application_infrastructure
    from app.config import get_settings
    from app.domain.shared.tdx_paths import resolve_tdx_root
    from app.infrastructure.repositories.common.deps import create_tdx_dayk_sync_service
    from app.infrastructure.repositories.mysql.mysql_tdx_dayk_repository import (
        MySQLTdxDaykRepository,
    )

    settings = get_settings()
    tdx_root = resolve_tdx_root(settings.tdx_root_path)
    if tdx_root is None:
        print("ERROR: TDX_ROOT_PATH not configured", file=sys.stderr)
        return 1
    if not settings.use_mysql:
        print("ERROR: use_mysql required", file=sys.stderr)
        return 1

    suffix = args.table_suffix
    target = f"stock_history_sh{suffix}, stock_history_sz{suffix}, stock_history_bj{suffix}"
    print(f"TDX root: {tdx_root}")
    print(f"Target tables: {target}")
    print(f"workers={args.workers or 'TDX_MYSQL_SYNC_WORKERS'}")

    bind_application_infrastructure(settings)
    svc = create_tdx_dayk_sync_service()
    codes = svc.scan_cn_codes_from_tdx_dayk(tdx_root)
    print(f"Symbols in lday: {len(codes)}")

    result = svc.reload_mysql_history_from_tdx(
        table_suffix=suffix,
        limit=args.limit,
        mysql_workers=args.workers,
        write_timescale=args.with_timescale,
        write_csv=args.with_csv,
        dump_qlib_bin=args.dump_qlib_bin,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    if not result.get("ok"):
        return 1

    if args.swap_tables:
        if not suffix:
            print("ERROR: --swap-tables requires non-empty --table-suffix", file=sys.stderr)
            return 1
        print("Swapping tables (production <- *_new, old -> *_old)...")
        MySQLTdxDaykRepository.swap_reload_tables(suffix)
        print("Swap done. Verify then DROP stock_history_*_old when ready.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
