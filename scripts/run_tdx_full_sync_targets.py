#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TDX 全量同步到 Timescale + CSV + qlib_bin（跳过 MySQL 历史表写入）。

适用场景：MySQL ``stock_history_*`` 已有最新数据，只需把 TDX lday+xdxr 全量
刷新到 Timescale + qlib_export CSV + qlib_bin，避免重写 MySQL 历史表。

- 复权因子在内存中重算后直接喂给 Timescale（不写 ``stock_adjustment_factor`` 表）
- ``validate_ohlcv_history_rows`` 自动跳过无效日期行（异常数据过滤）
- qlib_bin 从 CSV 导出（不依赖 MySQL）
- 默认清空 ``instance/tdx_sync/`` 检查点全新跑

用法（项目根目录，请先停 Beat / 增量任务）：
  # smoke test（前 3 个代码）
  python scripts/run_tdx_full_sync_targets.py --limit 3
  # 全量
  python scripts/run_tdx_full_sync_targets.py --workers 3
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="TDX full sync to Timescale + CSV + qlib_bin (skip MySQL history)",
    )
    parser.add_argument("--limit", type=int, default=None, help="Smoke: first N symbols")
    parser.add_argument(
        "--workers",
        type=int,
        default=3,
        help="Parallel workers (default 3, capped by TIMESCALE_MAX_WORKERS)",
    )
    parser.add_argument(
        "--keep-checkpoint",
        action="store_true",
        help="Keep instance/tdx_sync before run (default: cleared)",
    )
    parser.add_argument(
        "--skip-qlib-bin",
        action="store_true",
        help="Skip qlib_bin dump from CSV",
    )
    parser.add_argument(
        "--resume-skip-ok",
        action="store_true",
        help="Resume mode: skip symbols already in instance/tdx_sync/ok_codes.txt",
    )
    args = parser.parse_args()

    from app.bootstrap_components.infrastructure_binding import bind_application_infrastructure
    from app.config import get_settings
    from app.domain.shared.tdx_paths import resolve_tdx_root
    from app.infrastructure.repositories.common.deps import create_tdx_dayk_sync_service
    from app.modules.data.services.tdx_sync_checkpoint import (
        checkpoint_dir,
        filter_codes_resume,
    )

    settings = get_settings()
    tdx_root = resolve_tdx_root(settings.tdx_root_path)
    if tdx_root is None:
        print("ERROR: TDX_ROOT_PATH not configured", file=sys.stderr)
        return 1
    if not settings.use_timescaledb:
        print("ERROR: USE_TIMESCALEDB=0 — Timescale target unavailable", file=sys.stderr)
        return 1

    if not args.keep_checkpoint:
        d = checkpoint_dir()
        if d.is_dir():
            shutil.rmtree(d)
            print(f"Cleared checkpoint: {d}")

    print("=== TDX full sync (Timescale + CSV + qlib_bin, skip MySQL history) ===")
    print(f"TDX root: {tdx_root}")
    print(f"use_mysql={settings.use_mysql} use_timescaledb={settings.use_timescaledb}")
    print(f"workers={args.workers} dump_qlib_bin={not args.skip_qlib_bin} resume_skip_ok={args.resume_skip_ok}")

    bind_application_infrastructure(settings)
    svc = create_tdx_dayk_sync_service()

    # Resume mode: pre-filter codes to skip already-successful ones
    if args.resume_skip_ok:
        all_codes = svc.scan_cn_codes_from_tdx_dayk(tdx_root)
        before = len(all_codes)
        all_codes = filter_codes_resume(all_codes)
        skipped = before - len(all_codes)
        print(f"Resume filter: {before} -> {len(all_codes)} symbols (skipped {skipped} already-ok)")
        if args.limit:
            all_codes = all_codes[:args.limit]
        # Use _run_sync directly to pass pre-filtered codes
        def filter_all(rows, latest):
            return rows

        result = svc._run_sync(
            mode="full",
            codes=all_codes,
            filter_rows=filter_all,
            csv_merge=False,
            dump_qlib_bin=not args.skip_qlib_bin,
            dump_max_workers=args.workers,
            adjust_type="forward",
            skip_latest_dates=True,
            enable_timescale=True,
            enable_csv=True,
            enable_mysql=False,
        )
    else:
        result = svc.full_sync_from_tdx_dayk(
            limit=args.limit,
            dump_qlib_bin=not args.skip_qlib_bin,
            dump_max_workers=args.workers,
            csv_merge=False,
            adjust_type="forward",
            enable_timescale=True,
            enable_csv=True,
            enable_mysql=False,
        )

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
