from __future__ import annotations
"""统一命令行入口（门户新闻抓取、龙虎榜/研报入库）。"""


import argparse
import json
import sys
from pathlib import Path

from ..application.services.data.basic_market_data_service import BasicMarketDataService
from ..config import BASE_DIR, INSTANCE_DIR
from .portal_news import crawl_10jqka_gdxw, crawl_eastmoney_roll


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="量化平台 CLI：门户新闻、龙虎榜/研报入库（与 Web/API 同源）。",
    )
    sub = p.add_subparsers(dest="command", required=True)

    pe = sub.add_parser(
        "portal-eastmoney",
        help="东财滚动快讯拉取；可选写入 JSON（默认 instance/portal_news_dump）。",
    )
    pe.add_argument("--out-dir", type=Path, default=INSTANCE_DIR / "portal_news_dump", help="JSON 输出目录")
    pe.add_argument("--limit", type=int, default=50, help="最多条数")

    pj = sub.add_parser(
        "portal-10jqka",
        help="同花顺股道新闻拉取；可选写入 JSON（默认 instance/portal_news_dump）。",
    )
    pj.add_argument("--out-dir", type=Path, default=INSTANCE_DIR / "portal_news_dump", help="JSON 输出目录")
    pj.add_argument("--limit", type=int, default=50, help="最多条数")

    lh = sub.add_parser("longhu", help="龙虎榜明细入库（AkShare → instance/basic_market_data.db）")
    lh.add_argument("--lookback-days", type=int, default=14, dest="lookback", help="回溯自然日")

    yb = sub.add_parser("yanbao", help="东财研报列表页入库（→ instance/basic_market_data.db）")

    ts = sub.add_parser(
        "timeseries-backfill",
        help="TDX lday → QuestDB + ClickHouse 历史回填（需 TDX_ROOT_PATH 与 questdb 包）",
    )
    ts.add_argument("--limit", type=int, default=None, help="本批标的数量（默认读环境变量）")
    ts.add_argument("--offset", type=int, default=0, help="标的列表偏移（断点续传）")
    ts.add_argument("--lookback-days", type=int, default=None, dest="lookback_days")
    ts.add_argument("--batch-size", type=int, default=None, dest="batch_size", help="全量模式每批标的数")
    ts.add_argument("--max-batches", type=int, default=None, dest="max_batches", help="全量模式最多批次数，0=直到耗尽")
    ts.add_argument("--workers", type=int, default=None, help="并发拉取线程数")
    ts.add_argument("--force", action="store_true", help="已存在数据也重写（默认跳过已有）")
    ts.add_argument(
        "--targets",
        type=str,
        default="",
        help="questdb,clickhouse 逗号分隔，默认两者",
    )
    ts.add_argument("--full", action="store_true", help="分页跑完全市场（batch-size × max-batches）")

    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "portal-eastmoney":
        crawl_eastmoney_roll(out_dir=args.out_dir, limit=args.limit)
        return 0
    if args.command == "portal-10jqka":
        crawl_10jqka_gdxw(out_dir=args.out_dir, limit=args.limit)
        return 0
    if args.command == "longhu":
        svc = BasicMarketDataService(base_dir=BASE_DIR)
        out = svc.ingest_longhu_em(lookback_calendar_days=args.lookback)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 1 if out.get("ok") is False else 0
    if args.command == "yanbao":
        svc = BasicMarketDataService(base_dir=BASE_DIR)
        out = svc.ingest_yanbao_eastmoney_html()
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 1 if out.get("ok") is False else 0
    if args.command == "timeseries-backfill":
        from dotenv import load_dotenv

        load_dotenv()
        from ..application.services.data.tdx_ohlcv_reader import ensure_tdx_local_file_port

        ensure_tdx_local_file_port()
        from ..application.services.data.timeseries_ohlcv_sync_service import (
            run_timeseries_ohlcv_backfill,
            run_timeseries_ohlcv_sync,
        )

        targets = [t.strip() for t in (args.targets or "").split(",") if t.strip()] or None
        common = {
            "lookback_days": args.lookback_days,
            "targets": targets,
            "skip_existing": not args.force,
            "workers": args.workers,
            "max_symbols_cap": 50_000,
        }
        if args.full:
            out = run_timeseries_ohlcv_backfill(
                batch_size=args.batch_size,
                max_batches=args.max_batches,
                offset=args.offset,
                **common,
            )
        else:
            out = run_timeseries_ohlcv_sync(
                limit=args.limit,
                offset=args.offset,
                **common,
            )
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
