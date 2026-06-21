#!/usr/bin/env python3
"""TDX 全链路历史数据一致性补齐：QuestDB/CH/Timescale + MySQL/CSV/qlib。

串行、可断点、写日志 instance/full_data_consistency.log
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

os.environ.pop("TIMESERIES_SYNC_SYMBOLS", None)
os.environ.pop("QUESTDB_SYNC_SYMBOLS", None)
os.environ.setdefault("TIMESCALE_SYNC_WORKERS", "1")
os.environ.setdefault("TIMESERIES_SYNC_WORKERS", "2")
os.environ.setdefault("TIMESCALE_REFRESH_MATVIEWS_ON_SYNC", "0")
os.environ.setdefault("TIMESCALE_BACKFILL_BATCH_SLEEP_SEC", "2")
os.environ.setdefault("TDX_SYNC_ENABLE_TIMESCALE", "0")

LOG_PATH = _ROOT / "instance" / "full_data_consistency.log"
_TIMESCALE_STATE = _ROOT / "instance" / "timescale_backfill_state.json"


def _timescale_paused() -> bool:
    if not _TIMESCALE_STATE.is_file():
        return False
    try:
        state = json.loads(_TIMESCALE_STATE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return bool(state.get("paused"))


def _log(msg: str) -> None:
    line = f"{datetime.now(timezone.utc).isoformat()} {msg}"
    print(line, flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError as exc:
        print(f"{line} [log-write-failed: {exc}]", flush=True)


def _preflight(retries: int = 3, sleep_sec: float = 5.0) -> dict:
    from app.modules.data.services.timeseries_fresh_backfill import preflight_timeseries_targets

    last: dict = {}
    for attempt in range(1, retries + 1):
        last = preflight_timeseries_targets(require_questdb=False)
        q_ok = bool((last.get("questdb") or {}).get("connected"))
        ch_ok = bool((last.get("clickhouse") or {}).get("connected"))
        if q_ok or ch_ok:
            last["questdb_reachable"] = q_ok
            return last
        _log(f"preflight attempt {attempt}/{retries} failed (q={q_ok} ch={ch_ok})")
        if attempt < retries:
            time.sleep(sleep_sec)
    last["questdb_reachable"] = False
    return last


def main() -> int:
    parser = argparse.ArgumentParser(description="Full TDX data consistency sync")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--skip-ch", action="store_true")
    parser.add_argument(
        "--skip-ts",
        action="store_true",
        help="跳过 Timescale（或 state.paused / FULL_BACKFILL_SKIP_TIMESCALE=1 时自动跳过）",
    )
    parser.add_argument("--skip-mysql", action="store_true")
    parser.add_argument("--skip-qlib", action="store_true")
    parser.add_argument("--sample", type=int, default=40)
    args = parser.parse_args()

    from app.core.runtime_config import get_runtime_bool

    skip_ts_auto = get_runtime_bool("FULL_BACKFILL_SKIP_TIMESCALE", False) or _timescale_paused()
    if skip_ts_auto and not args.skip_ts:
        args.skip_ts = True
        reason = "FULL_BACKFILL_SKIP_TIMESCALE" if get_runtime_bool("FULL_BACKFILL_SKIP_TIMESCALE", False) else "timescale_backfill_state.paused"
        _log(f"INFO auto skip timescale ({reason}); prioritize MySQL/CSV/qlib")

    from app.bootstrap_components.infrastructure_binding import bind_application_infrastructure
    from app.config import get_settings

    bind_application_infrastructure(get_settings())

    from scripts.run_timeseries_sync_pipeline import (
        cmd_dump_qlib,
        cmd_sync_clickhouse,
        cmd_sync_mysql_csv,
        cmd_sync_timescale,
        cmd_verify,
    )

    _log("=== full data consistency start ===")
    pre = _preflight()
    q_rows = int((pre.get("questdb") or {}).get("rows") or 0)
    ch_raw = (pre.get("clickhouse") or {}).get("rows") or 0
    ch_rows = int(ch_raw) if str(ch_raw).isdigit() else 0
    q_ok = bool((pre.get("questdb") or {}).get("connected"))
    ch_ok = bool((pre.get("clickhouse") or {}).get("connected"))
    _log(json.dumps({"preflight": pre}, ensure_ascii=False))

    if not q_ok:
        _log("WARN questdb unreachable; CH/Timescale/MySQL will sync from TDX only")
    if not ch_ok and not args.skip_ch:
        _log("ERROR: clickhouse preflight failed")
        return 1

    rc = 0
    ns = argparse.Namespace(
        batch_size=200,
        max_batches=0,
        offset=None,
        workers=args.workers,
        lookback_days=None,
        force=False,
        targets="questdb,clickhouse",
        no_resume=False,
        table_suffix="_new",
        resume=False,
        retry_failed=False,
        swap_tables=False,
        truncate_factors=False,
        clear_checkpoint=False,
        limit=None,
        full=True,
        days_lookback=5,
        skip_csv=False,
        sample=args.sample,
    )

    if (
        not args.skip_ch
        and ch_ok
        and q_ok
        and ch_rows < q_rows * 0.998
    ):
        _log(f"PHASE clickhouse gap={q_rows - ch_rows}")
        rc = max(rc, cmd_sync_clickhouse(ns))
    elif not args.skip_ch and ch_ok and not q_ok and ch_rows < 8_000_000:
        _log(f"PHASE clickhouse gap=unknown qdb_down ch_rows={ch_rows}")
        rc = max(rc, cmd_sync_clickhouse(ns))
    elif not args.skip_ch and ch_ok and not q_ok:
        _log(
            f"PHASE clickhouse skipped (qdb down, ch_rows={ch_rows} ~complete; "
            "run sync-clickhouse after QuestDB recovery to verify gap)"
        )
    elif not args.skip_ch:
        _log("PHASE clickhouse skipped (aligned or CH unreachable)")

    if not args.skip_ts:
        _log("PHASE timescale resume")
        ns.workers = 1
        rc = max(rc, cmd_sync_timescale(ns))
    else:
        _log("PHASE timescale skipped (prioritize MySQL/CSV/qlib)")

    if not args.skip_mysql:
        from app.modules.data.services.tdx_sync_checkpoint import load_failed_codes

        fail_n = len(load_failed_codes())
        if fail_n:
            _log(f"PHASE mysql retry_failed count={fail_n}")
            ns.retry_failed = True
            ns.resume = False
            ns.workers = max(1, min(args.workers, 2))
            rc = max(rc, cmd_sync_mysql_csv(ns))
        _log("PHASE mysql resume")
        ns.retry_failed = False
        ns.resume = True
        rc = max(rc, cmd_sync_mysql_csv(ns))
    else:
        _log("PHASE mysql skipped")

    if not args.skip_qlib:
        _log("PHASE qlib dump")
        ns.full = True
        rc = max(rc, cmd_dump_qlib(ns))
    else:
        _log("PHASE qlib skipped")

    _log("PHASE verify")
    rc = max(rc, cmd_verify(ns))
    _log(f"=== full data consistency end rc={rc} ===")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
