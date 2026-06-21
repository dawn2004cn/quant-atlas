#!/usr/bin/env python3
"""一次性全市场历史入库：TDX → QuestDB+ClickHouse → Timescale → MySQL(可选)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

import os

# 避免 shell 残留单股测试变量导致只同步 1 只
os.environ.pop("TIMESERIES_SYNC_SYMBOLS", None)
os.environ.pop("QUESTDB_SYNC_SYMBOLS", None)
# QuestDB PG 并发连接有限，全量回填默认降低 worker
os.environ.setdefault("TIMESERIES_SYNC_WORKERS", "2")
os.environ.setdefault("TIMESCALE_SYNC_WORKERS", "2")
os.environ.setdefault("TIMESCALE_REFRESH_MATVIEWS_ON_SYNC", "0")


def main() -> int:
    from app.modules.data.services.tdx_ohlcv_reader import ensure_tdx_local_file_port
    from app.modules.system.services.helpers.timescale_bar_access import ensure_timescale_bar_port
    from app.modules.data.services.tdx_timescale_sync_service import run_tdx_timescale_backfill
    from app.modules.data.services.timeseries_ohlcv_sync_service import (
        run_timeseries_ohlcv_backfill,
    )
    from app.core.runtime_config import get_runtime_bool, get_runtime_int

    ensure_tdx_local_file_port()
    ensure_timescale_bar_port()

    if get_runtime_bool("FULL_BACKFILL_TRUNCATE", get_runtime_bool("FULL_BACKFILL_FRESH", False)):
        from app.modules.data.services.timeseries_fresh_backfill import (
            truncate_all_timeseries_targets,
        )

        print("=== [0] 清空 QuestDB / ClickHouse / Timescale 日 K 表 ===", flush=True)
        trunc = truncate_all_timeseries_targets()
        print(json.dumps(trunc, ensure_ascii=False, indent=2), flush=True)
        if not trunc.get("ok"):
            print("truncate failed; fix connectivity/auth before backfill", flush=True)
            return 1

    from app.modules.data.services.timeseries_fresh_backfill import preflight_timeseries_targets

    print("=== [0] 探活 QuestDB + ClickHouse SQL ===", flush=True)
    pre = preflight_timeseries_targets()
    print(json.dumps(pre, ensure_ascii=False, indent=2), flush=True)
    if not pre.get("ok"):
        print("preflight failed; check QUESTDB_* / CLICKHOUSE_PASSWORD", flush=True)
        return 1

    skip_ch = get_runtime_bool("FULL_BACKFILL_SKIP_CLICKHOUSE", False)
    if skip_ch:
        print("NOTE: ClickHouse skipped (FULL_BACKFILL_SKIP_CLICKHOUSE=1); fix password and re-run CH later", flush=True)

    from app.modules.data.services.tdx_code_cache import get_tdx_cn_universe

    n_codes = len(get_tdx_cn_universe())
    batch = get_runtime_int("TIMESERIES_BACKFILL_BATCH", 200)
    est_batches = (n_codes + batch - 1) // batch if batch else 0
    print(
        f"TDX universe: {n_codes} codes, batch={batch}, est_batches≈{est_batches}, "
        f"lookback={get_runtime_int('QUESTDB_SYNC_LOOKBACK_DAYS', 1500)}d",
        flush=True,
    )

    report: dict[str, object] = {"steps": [], "universe_size": n_codes, "preflight": pre}
    timescale_only = get_runtime_bool("FULL_BACKFILL_TIMESCALE_ONLY", False)

    if timescale_only:
        print("=== [1/2] QuestDB+ClickHouse 跳过 (FULL_BACKFILL_TIMESCALE_ONLY=1) ===", flush=True)
    else:
        print("=== [1/2] TDX → QuestDB + ClickHouse 全量分页 ===", flush=True)
    ts_out = (
        {"ok": True, "skipped": True, "reason": "timescale_only"}
        if timescale_only
        else run_timeseries_ohlcv_backfill(
            batch_size=get_runtime_int("TIMESERIES_BACKFILL_BATCH", 200),
            max_batches=0,
            lookback_days=get_runtime_int("QUESTDB_SYNC_LOOKBACK_DAYS", 1500),
            workers=get_runtime_int("TIMESERIES_SYNC_WORKERS", 2),
            all_market=False,
            targets=["questdb"] if skip_ch else None,
        )
    )
    if not timescale_only:
        report["steps"].append({"name": "questdb_clickhouse", "result": ts_out})
    if not timescale_only:
        q_rows = (ts_out.get("questdb") or {}).get("rows_written", 0)
        ch_rows = (ts_out.get("clickhouse") or {}).get("rows_written", 0)
        print(
            f"  step1 done: batches={ts_out.get('total_batches')} "
            f"q_rows={q_rows} ch_rows={ch_rows} next_offset={ts_out.get('next_offset')}",
            flush=True,
        )

    if not get_runtime_bool("ENABLE_TIMESCALE_TDX_SYNC", True):
        print("=== [2/2] Timescale 跳过 (ENABLE_TIMESCALE_TDX_SYNC=0) ===", flush=True)
    else:
        print("=== [2/2] TDX → Timescale 全量分页 ===", flush=True)
        scale_out = run_tdx_timescale_backfill(
            batch_size=get_runtime_int("TIMESCALE_BACKFILL_BATCH", 200),
            max_batches=0,
            dump_max_workers=get_runtime_int("TIMESCALE_SYNC_WORKERS", 4),
        )
        report["steps"].append({"name": "timescale", "result": scale_out})
        print(
            f"  step2 done: batches={scale_out.get('total_batches')} ok={scale_out.get('ok')}",
            flush=True,
        )

    if get_runtime_bool("FULL_BACKFILL_INCLUDE_MYSQL", False):
        print("=== [3/3] TDX → MySQL 全量 (可选，较慢) ===", flush=True)
        from app.infrastructure.repositories.deps import create_tdx_dayk_sync_service

        mysql_out = create_tdx_dayk_sync_service().full_sync_from_tdx_dayk(
            dump_qlib_bin=get_runtime_bool("FULL_BACKFILL_MYSQL_DUMP_QLIB", False),
        )
        report["steps"].append({"name": "mysql", "result": mysql_out})
        print(json.dumps(mysql_out, ensure_ascii=False, indent=2)[:2000], flush=True)

    ok = all(
        bool((s.get("result") or {}).get("ok"))
        for s in report["steps"]
        if isinstance(s.get("result"), dict)
    )
    report["ok"] = ok
    out_path = _ROOT / "instance" / "full_history_backfill_report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"report written: {out_path}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
