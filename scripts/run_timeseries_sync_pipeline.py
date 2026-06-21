#!/usr/bin/env python3
"""分步时序日 K 同步：验收 → 按库补跑 → 对账。

目标：QuestDB / ClickHouse / Timescale 与 TDX 一致，互不拖垮。

用法:
  python scripts/run_timeseries_sync_pipeline.py status
  python scripts/run_timeseries_sync_pipeline.py status-mysql
  python scripts/run_timeseries_sync_pipeline.py sync-clickhouse
  python scripts/run_timeseries_sync_pipeline.py sync-timescale
  python scripts/run_timeseries_sync_pipeline.py sync-mysql-csv [--resume]
  python scripts/run_timeseries_sync_pipeline.py dump-qlib
  python scripts/run_timeseries_sync_pipeline.py sync-failed
  python scripts/run_timeseries_sync_pipeline.py verify
  python scripts/run_timeseries_sync_pipeline.py run-missing
  python scripts/run_timeseries_sync_pipeline.py run-mysql-missing
  python scripts/run_timeseries_sync_pipeline.py sync-all
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

# 避免 shell 残留单股测试变量
os.environ.pop("TIMESERIES_SYNC_SYMBOLS", None)
os.environ.pop("QUESTDB_SYNC_SYMBOLS", None)
os.environ.setdefault("TIMESCALE_SYNC_WORKERS", "1")
os.environ.setdefault("TIMESCALE_REFRESH_MATVIEWS_ON_SYNC", "0")
os.environ.setdefault("TIMESCALE_BACKFILL_BATCH_SLEEP_SEC", "2")
os.environ.setdefault("TDX_SYNC_ENABLE_TIMESCALE", "0")


def _print(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2), flush=True)


def cmd_status(_: argparse.Namespace) -> int:
    from app.modules.data.services.timeseries_sync_status import collect_timeseries_sync_status

    _print(collect_timeseries_sync_status())
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    from app.modules.data.services.timeseries_sync_status import run_timeseries_verify

    out = run_timeseries_verify(sample_size=args.sample)
    _print(out)
    return 0 if out.get("ok") else 1


def cmd_sync_clickhouse(args: argparse.Namespace) -> int:
    from app.modules.data.services.tdx_ohlcv_reader import ensure_tdx_local_file_port
    from app.modules.data.services.timeseries_fresh_backfill import preflight_timeseries_targets
    from app.modules.data.services.timeseries_ohlcv_sync_service import run_timeseries_ohlcv_backfill
    from app.core.runtime_config import get_runtime_int

    ensure_tdx_local_file_port()
    pre = preflight_timeseries_targets(require_questdb=False)
    if not pre.get("ok"):
        _print({"ok": False, "error": "preflight_failed", "preflight": pre})
        return 1
    out = run_timeseries_ohlcv_backfill(
        batch_size=args.batch_size or get_runtime_int("TIMESERIES_BACKFILL_BATCH", 200),
        max_batches=args.max_batches,
        offset=args.offset,
        lookback_days=args.lookback_days or get_runtime_int("QUESTDB_SYNC_LOOKBACK_DAYS", 1500),
        workers=args.workers or get_runtime_int("TIMESERIES_SYNC_WORKERS", 2),
        all_market=False,
        targets=["clickhouse"],
        skip_existing=False,
    )
    _print({"ok": bool(out.get("ok")), "result": out})
    return 0 if out.get("ok") else 1


def cmd_sync_questdb_ch(args: argparse.Namespace) -> int:
    from app.modules.data.services.tdx_ohlcv_reader import ensure_tdx_local_file_port
    from app.modules.data.services.timeseries_fresh_backfill import preflight_timeseries_targets
    from app.modules.data.services.timeseries_ohlcv_sync_service import run_timeseries_ohlcv_backfill
    from app.core.runtime_config import get_runtime_int

    ensure_tdx_local_file_port()
    pre = preflight_timeseries_targets()
    if not pre.get("ok"):
        _print({"ok": False, "error": "preflight_failed", "preflight": pre})
        return 1
    targets = [t.strip() for t in (args.targets or "questdb,clickhouse").split(",") if t.strip()]
    out = run_timeseries_ohlcv_backfill(
        batch_size=args.batch_size or get_runtime_int("TIMESERIES_BACKFILL_BATCH", 200),
        max_batches=args.max_batches,
        offset=args.offset,
        lookback_days=args.lookback_days or get_runtime_int("QUESTDB_SYNC_LOOKBACK_DAYS", 1500),
        workers=args.workers or get_runtime_int("TIMESERIES_SYNC_WORKERS", 2),
        all_market=False,
        targets=targets,
        skip_existing=not args.force,
    )
    _print({"ok": bool(out.get("ok")), "result": out})
    return 0 if out.get("ok") else 1


def cmd_sync_timescale(args: argparse.Namespace) -> int:
    from app.modules.data.services.tdx_ohlcv_reader import ensure_tdx_local_file_port
    from app.modules.system.services.helpers.timescale_bar_access import ensure_timescale_bar_port
    from app.modules.data.services.tdx_timescale_sync_service import run_tdx_timescale_backfill
    from app.core.runtime_config import get_runtime_int

    ensure_tdx_local_file_port()
    ensure_timescale_bar_port()
    out = run_tdx_timescale_backfill(
        batch_size=args.batch_size or get_runtime_int("TIMESCALE_BACKFILL_BATCH", 200),
        max_batches=args.max_batches,
        offset=args.offset,
        dump_max_workers=args.workers or get_runtime_int("TIMESCALE_SYNC_WORKERS", 1),
        resume=not args.no_resume,
    )
    _print({"ok": bool(out.get("ok")), "result": out})
    return 0 if out.get("ok") and not out.get("paused") else 1


def cmd_sync_failed(args: argparse.Namespace) -> int:
    from app.modules.data.services.tdx_ohlcv_reader import ensure_tdx_local_file_port
    from app.modules.system.services.helpers.timescale_bar_access import ensure_timescale_bar_port
    from app.modules.data.services.tdx_sync_checkpoint import load_failed_codes
    from app.modules.data.services.tdx_timescale_sync_service import run_tdx_timescale_sync
    from app.core.runtime_config import get_runtime_int

    ensure_tdx_local_file_port()
    ensure_timescale_bar_port()
    codes = load_failed_codes()
    if not codes:
        _print({"ok": True, "skipped": True, "reason": "no_failed_codes"})
        return 0
    if args.limit and args.limit > 0:
        codes = codes[: args.limit]
    out = run_tdx_timescale_sync(
        symbols=codes,
        dump_max_workers=args.workers or get_runtime_int("TIMESCALE_SYNC_WORKERS", 1),
    )
    _print({"ok": bool(out.get("ok")), "codes": len(codes), "result": out})
    return 0 if out.get("ok") else 1


def _bind_infra() -> None:
    from app.bootstrap_components.infrastructure_binding import bind_application_infrastructure
    from app.config import get_settings

    bind_application_infrastructure(get_settings())


def cmd_status_mysql(_: argparse.Namespace) -> int:
    _bind_infra()
    from app.modules.data.services.mysql_qlib_sync_status import collect_mysql_qlib_sync_status

    _print(collect_mysql_qlib_sync_status())
    return 0


def cmd_sync_mysql_csv(args: argparse.Namespace) -> int:
    _bind_infra()
    from app.infrastructure.repositories.common.deps import create_tdx_dayk_sync_service
    from app.core.runtime_config import get_runtime_int

    import os as _os

    _os.environ["TDX_MYSQL_TRUNCATE_SUFFIX_TABLES"] = "0"
    _os.environ["TDX_MYSQL_INSERT_ONLY"] = "0"
    svc = create_tdx_dayk_sync_service()
    if args.retry_failed:
        out = svc.retry_failed_from_tdx(
            workers=args.workers or get_runtime_int("TDX_MYSQL_SYNC_WORKERS", 3),
            mysql_table_suffix=args.table_suffix,
            dump_qlib_bin=False,
            enable_csv=True,
            enable_timescale=False,
        )
    else:
        out = svc.full_sync_all_from_tdx(
            limit=args.limit,
            workers=args.workers or get_runtime_int("TDX_FULL_SYNC_WORKERS", 3),
            mysql_table_suffix=args.table_suffix,
            swap_mysql_tables=args.swap_tables,
            truncate_factors=args.truncate_factors,
            dump_qlib_bin=False,
            resume_skip_ok=args.resume,
            clear_checkpoint=args.clear_checkpoint,
        )
    _print(dict(out))
    return 0 if out.get("ok") else 1


def cmd_dump_qlib(args: argparse.Namespace) -> int:
    _bind_infra()
    from app.infrastructure.repositories.common.deps import (
        create_default_qlib_pipeline_service,
    )

    svc = create_default_qlib_pipeline_service()
    out = svc.mysql_to_bin_sync(
        days_lookback=0 if args.full else args.days_lookback,
        limit_stocks=args.limit or None,
        export_csv=not args.skip_csv,
    )
    _print(dict(out) if isinstance(out, dict) else out.model_dump())
    return 0 if (out.get("ok") if isinstance(out, dict) else out.ok) else 1


def cmd_run_mysql_missing(args: argparse.Namespace) -> int:
    _bind_infra()
    from app.modules.data.services.mysql_qlib_sync_status import collect_mysql_qlib_sync_status

    status = collect_mysql_qlib_sync_status()
    pending = list(status.get("pending_actions") or [])
    _print({"phase": "status-mysql", "status": status})
    rc = 0
    if "mysql_backfill" in pending or "csv_backfill" in pending:
        _print({"phase": "sync-mysql-csv"})
        sync_args = argparse.Namespace(
            table_suffix=getattr(args, "table_suffix", "_new"),
            resume=True,
            retry_failed=False,
            swap_tables=False,
            truncate_factors=getattr(args, "truncate_factors", False),
            clear_checkpoint=False,
            limit=None,
            workers=getattr(args, "workers", None) or 2,
        )
        rc = max(rc, cmd_sync_mysql_csv(sync_args))
    from app.modules.data.services.tdx_sync_checkpoint import load_failed_codes

    failed_n = len(load_failed_codes())
    if failed_n:
        _print({"phase": "sync-mysql-retry-failed", "count": failed_n})
        retry_args = argparse.Namespace(
            table_suffix=getattr(args, "table_suffix", "_new"),
            resume=False,
            retry_failed=True,
            swap_tables=False,
            truncate_factors=False,
            clear_checkpoint=False,
            limit=None,
            workers=getattr(args, "workers", None) or 2,
        )
        rc = max(rc, cmd_sync_mysql_csv(retry_args))
    if "qlib_bin_dump" in pending or getattr(args, "always_dump_qlib", False):
        _print({"phase": "dump-qlib"})
        ql_args = argparse.Namespace(full=True, days_lookback=5, limit=0, skip_csv=False)
        rc = max(rc, cmd_dump_qlib(ql_args))
    return rc


def cmd_run_missing(args: argparse.Namespace) -> int:
    from app.modules.data.services.timeseries_sync_status import collect_timeseries_sync_status

    status = collect_timeseries_sync_status()
    pending = list(status.get("pending_actions") or [])
    _print({"phase": "status", "status": status})
    if not pending:
        return cmd_verify(args)

    rc = 0
    if "clickhouse_backfill" in pending:
        _print({"phase": "sync-clickhouse"})
        rc = max(rc, cmd_sync_clickhouse(args))
    if "timescale_backfill" in pending:
        _print({"phase": "sync-timescale"})
        rc = max(rc, cmd_sync_timescale(args))
    if "questdb_backfill" in pending:
        _print({"phase": "sync-questdb-ch"})
        rc = max(rc, cmd_sync_questdb_ch(args))

    _print({"phase": "verify"})
    rc = max(rc, cmd_verify(args))
    return rc


def cmd_sync_all(args: argparse.Namespace) -> int:
    """按缺口顺序补跑：CH → Timescale → MySQL/CSV → qlib → verify（串行）。"""
    from app.modules.data.services.timeseries_sync_status import collect_timeseries_sync_status

    ts_status = collect_timeseries_sync_status()
    _print({"phase": "status-timeseries", "status": ts_status})
    rc = 0
    pending = list(ts_status.get("pending_actions") or [])

    if "questdb_unreachable" in pending:
        _print({"phase": "skip-questdb", "reason": "QuestDB unreachable; fix network first"})
    elif "questdb_backfill" in pending:
        _print({"phase": "sync-questdb-ch"})
        rc = max(rc, cmd_sync_questdb_ch(args))

    if "clickhouse_unreachable" in pending:
        _print({"phase": "skip-clickhouse", "reason": "ClickHouse unreachable"})
    elif "clickhouse_backfill" in pending or getattr(args, "force_ch", False):
        _print({"phase": "sync-clickhouse"})
        rc = max(rc, cmd_sync_clickhouse(args))

    if "timescale_unreachable" in pending:
        _print({"phase": "skip-timescale", "reason": "Timescale unreachable; fix PG first"})
    elif "timescale_backfill" in pending or getattr(args, "force_ts", False):
        _print({"phase": "sync-timescale"})
        rc = max(rc, cmd_sync_timescale(args))

    rc = max(rc, cmd_run_mysql_missing(args))

    _print({"phase": "verify"})
    rc = max(rc, cmd_verify(args))
    return rc


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="分步时序日 K 同步管道")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="三库行数/标的快照")
    sub.add_parser("status-mysql", help="MySQL / CSV / qlib_bin 快照")

    v = sub.add_parser("verify", help="快照 + 最新日对账抽检")
    v.add_argument("--sample", type=int, default=40)

    ch = sub.add_parser("sync-clickhouse", help="仅 TDX → ClickHouse 全量分页")
    ts = sub.add_parser("sync-timescale", help="仅 TDX → Timescale 全量分页（断点续跑）")
    sf = sub.add_parser("sync-failed", help="仅补跑 Timescale 失败代码")
    qc = sub.add_parser("sync-questdb-ch", help="TDX → QuestDB + ClickHouse")

    rm = sub.add_parser("run-missing", help="按 status 自动补跑缺失库并 verify")

    mc = sub.add_parser("sync-mysql-csv", help="TDX → MySQL + 因子 + CSV（默认不写 Timescale）")
    mc.add_argument("--table-suffix", default="_new")
    mc.add_argument("--resume", action="store_true", help="跳过 ok_codes.txt 已成功标的")
    mc.add_argument("--retry-failed", action="store_true")
    mc.add_argument("--swap-tables", action="store_true")
    mc.add_argument("--truncate-factors", action="store_true")
    mc.add_argument("--clear-checkpoint", action="store_true")
    mc.add_argument("--limit", type=int, default=None)
    mc.add_argument("--workers", type=int, default=None)

    ql = sub.add_parser("dump-qlib", help="MySQL → qlib_bin（可选导出 CSV）")
    ql.add_argument("--full", action="store_true", help="全量导 bin（days_lookback=0）")
    ql.add_argument("--days-lookback", type=int, default=5)
    ql.add_argument("--limit", type=int, default=0)
    ql.add_argument("--skip-csv", action="store_true")

    rmm = sub.add_parser("run-mysql-missing", help="按 status-mysql 补 MySQL/CSV/qlib")
    rmm.add_argument("--always-dump-qlib", action="store_true")
    rmm.add_argument("--table-suffix", default="_new")
    rmm.add_argument("--workers", type=int, default=None)
    rmm.add_argument("--truncate-factors", action="store_true")

    sa = sub.add_parser("sync-all", help="串行补齐全链路并 verify")
    sa.add_argument("--batch-size", type=int, default=None)
    sa.add_argument("--max-batches", type=int, default=0)
    sa.add_argument("--offset", type=int, default=None)
    sa.add_argument("--workers", type=int, default=2)
    sa.add_argument("--lookback-days", type=int, default=None)
    sa.add_argument("--table-suffix", default="_new")
    sa.add_argument("--force-ch", action="store_true")
    sa.add_argument("--force-ts", action="store_true")
    sa.add_argument("--always-dump-qlib", action="store_true")
    sa.add_argument("--sample", type=int, default=40)

    for sp in (ch, ts, sf, qc, rm):
        sp.add_argument("--batch-size", type=int, default=None)
        sp.add_argument("--max-batches", type=int, default=0)
        sp.add_argument("--offset", type=int, default=None)
        sp.add_argument("--workers", type=int, default=None)
        sp.add_argument("--lookback-days", type=int, default=None)
    qc.add_argument("--targets", type=str, default="questdb,clickhouse")
    qc.add_argument("--force", action="store_true", help="QuestDB/CH 强制重写")
    ts.add_argument("--no-resume", action="store_true", help="忽略 timescale_backfill_state.json")
    sf.add_argument("--limit", type=int, default=0, help="最多补跑 N 只失败代码，0=全部")

    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    handlers = {
        "status": cmd_status,
        "status-mysql": cmd_status_mysql,
        "verify": cmd_verify,
        "sync-clickhouse": cmd_sync_clickhouse,
        "sync-timescale": cmd_sync_timescale,
        "sync-failed": cmd_sync_failed,
        "sync-questdb-ch": cmd_sync_questdb_ch,
        "sync-mysql-csv": cmd_sync_mysql_csv,
        "dump-qlib": cmd_dump_qlib,
        "run-missing": cmd_run_missing,
        "run-mysql-missing": cmd_run_mysql_missing,
        "sync-all": cmd_sync_all,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
