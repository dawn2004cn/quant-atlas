#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TDX 一键全量：lday + xdxr → MySQL + stock_adjustment_factor + Timescale + CSV + qlib_bin。

默认写入影子表 ``stock_history_*_new``，灌完后 ``--swap-tables`` 切生产表，再从 MySQL 导 qlib_bin。

用法（项目根目录，请先停 Beat / 增量任务）：
  python scripts/run_tdx_full_sync_all.py --swap-tables --truncate-factors
  python scripts/run_tdx_full_sync_all.py --production --workers 4
  python scripts/run_tdx_full_sync_all.py --limit 20 --truncate-factors

失败续跑（检查点目录默认 ``instance/tdx_sync/``）：
  # 仅重跑 failed_codes.txt（UPSERT，不清空 *_new）
  python scripts/run_tdx_full_sync_all.py --retry-failed --workers 3
  # 全量续传：跳过 ok_codes.txt 中已成功代码
  python scripts/run_tdx_full_sync_all.py --resume --no-truncate-new --workers 3
  # 全新全量前清空检查点
  python scripts/run_tdx_full_sync_all.py --clear-checkpoint --truncate-factors ...
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
    parser = argparse.ArgumentParser(
        description="Full TDX sync: MySQL + factors + Timescale + CSV + qlib_bin",
    )
    parser.add_argument("--limit", type=int, default=None, help="Smoke: first N symbols")
    parser.add_argument("--workers", type=int, default=None, help="Parallel workers (default TDX_FULL_SYNC_WORKERS=4)")
    parser.add_argument(
        "--table-suffix",
        default="_new",
        help="MySQL history table suffix (default _new)",
    )
    parser.add_argument(
        "--production",
        action="store_true",
        help="Write stock_history_sh/sz/bj directly (same as --table-suffix '')",
    )
    parser.add_argument(
        "--swap-tables",
        action="store_true",
        help="After load, RENAME *_new -> production, old -> *_old",
    )
    parser.add_argument(
        "--truncate-factors",
        action="store_true",
        help="TRUNCATE stock_adjustment_factor before sync",
    )
    parser.add_argument(
        "--no-truncate-new",
        action="store_true",
        help="Do not TRUNCATE stock_history_*{suffix} before load (upsert resume)",
    )
    parser.add_argument(
        "--skip-qlib-bin",
        action="store_true",
        help="Skip qlib_bin dump",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Only sync codes in failed_codes.txt (UPSERT resume)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Full sync but skip codes already in ok_codes.txt",
    )
    parser.add_argument(
        "--failed-file",
        type=Path,
        default=None,
        help="Custom failed_codes.txt path (with --retry-failed)",
    )
    parser.add_argument(
        "--clear-checkpoint",
        action="store_true",
        help="Delete instance/tdx_sync before a fresh full run",
    )
    args = parser.parse_args()

    from app.bootstrap_components.infrastructure_binding import bind_application_infrastructure
    from app.config import get_settings
    from app.domain.shared.tdx_paths import resolve_tdx_root
    from app.infrastructure.repositories.common.deps import create_tdx_dayk_sync_service

    settings = get_settings()
    tdx_root = resolve_tdx_root(settings.tdx_root_path)
    if tdx_root is None:
        print("ERROR: TDX_ROOT_PATH not configured", file=sys.stderr)
        return 1
    if not settings.use_mysql:
        print("ERROR: use_mysql required", file=sys.stderr)
        return 1
    if not settings.use_timescaledb:
        print("WARN: USE_TIMESCALEDB=0 — Timescale step will be skipped", file=sys.stderr)

    suffix = "" if args.production else args.table_suffix
    if args.production and args.swap_tables:
        print("ERROR: --production and --swap-tables are mutually exclusive", file=sys.stderr)
        return 1
    if args.swap_tables and not suffix:
        print("ERROR: --swap-tables needs a non-empty table suffix (e.g. _new)", file=sys.stderr)
        return 1
    if args.retry_failed and args.resume:
        print("ERROR: --retry-failed and --resume are mutually exclusive", file=sys.stderr)
        return 1
    if args.retry_failed and args.swap_tables:
        print("ERROR: run --retry-failed until failed=0 before --swap-tables", file=sys.stderr)
        return 1

    import os

    if args.retry_failed or args.resume or args.no_truncate_new:
        os.environ["TDX_MYSQL_TRUNCATE_SUFFIX_TABLES"] = "0"
    if args.retry_failed or args.resume:
        os.environ["TDX_MYSQL_INSERT_ONLY"] = "0"

    print("=== TDX full sync (all targets) ===")
    print(f"TDX root: {tdx_root}")
    print(f"use_mysql={settings.use_mysql} use_timescaledb={settings.use_timescaledb}")
    print(f"MySQL tables: stock_history_sh{suffix}, stock_history_sz{suffix}, stock_history_bj{suffix}")
    print("factors: stock_adjustment_factor")
    print(f"CSV: {settings.qlib_export_dir if hasattr(settings, 'qlib_export_dir') else 'instance/qlib_export'}")
    print(f"swap={args.swap_tables} truncate_factors={args.truncate_factors}")

    bind_application_infrastructure(settings)
    svc = create_tdx_dayk_sync_service()
    n = len(svc.scan_cn_codes_from_tdx_dayk(tdx_root))
    print(f"Symbols in lday: {n}" + (f" (limit {args.limit})" if args.limit else ""))
    if args.retry_failed:
        from app.modules.data.services.tdx_sync_checkpoint import (
            checkpoint_dir,
            failed_codes_path,
            load_failed_codes,
        )

        fc = load_failed_codes(file=args.failed_file)
        print(f"Retry failed: {len(fc)} codes from {args.failed_file or failed_codes_path()}")
        if not fc:
            print("Nothing to retry (empty failed list).")
            return 0
    if args.resume:
        from app.modules.data.services.tdx_sync_checkpoint import (
            checkpoint_dir,
            load_ok_codes,
        )

        print(f"Resume: skip {len(load_ok_codes())} ok codes in {checkpoint_dir()}")

    if args.retry_failed:
        result = svc.retry_failed_from_tdx(
            failed_file=args.failed_file,
            workers=args.workers,
            mysql_table_suffix=suffix,
            dump_qlib_bin=not args.skip_qlib_bin,
        )
    else:
        result = svc.full_sync_all_from_tdx(
            limit=args.limit,
            workers=args.workers,
            mysql_table_suffix=suffix,
            swap_mysql_tables=args.swap_tables,
            truncate_factors=args.truncate_factors,
            dump_qlib_bin=not args.skip_qlib_bin,
            resume_skip_ok=args.resume,
            clear_checkpoint=args.clear_checkpoint,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
