from __future__ import annotations

"""门户滚动/股道新闻：CLI 用抓取与可选落盘（与 Web 新闻源同源）。"""


import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ..infrastructure.providers.cn_portal_news import (
    fetch_10jqka_gdxw_headlines,
    fetch_eastmoney_roll_headlines,
)


def _merge_write_json(fp: Path, items: list[dict[str, Any]]) -> tuple[int, int]:
    """去重合并写入；返回 (新增条数, 总条数)。"""
    existing: list[dict[str, Any]] = []
    if fp.is_file():
        try:
            raw = json.loads(fp.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                existing = raw
        except json.JSONDecodeError:
            existing = []
    keys = {(x.get("title"), x.get("published_at")) for x in existing}
    new = [x for x in items if (x.get("title"), x.get("published_at")) not in keys]
    if new:
        fp.write_text(json.dumps(existing + new, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(new), len(existing) + len(new)


def crawl_eastmoney_roll(*, out_dir: Path, limit: int) -> list[dict[str, Any]]:
    items = fetch_eastmoney_roll_headlines(limit=limit)
    out_dir.mkdir(parents=True, exist_ok=True)
    if items:
        fp = out_dir / f"eastmoney_roll_{datetime.now().strftime('%Y%m%d')}.json"
        n_new, total = _merge_write_json(fp, items)
        if n_new:
            print(f"东方财富滚动：新增 {n_new} 条（累计 {total}）→ {fp}")
    return items


def crawl_10jqka_gdxw(*, out_dir: Path, limit: int) -> list[dict[str, Any]]:
    items = fetch_10jqka_gdxw_headlines(limit=limit)
    out_dir.mkdir(parents=True, exist_ok=True)
    if items:
        fp = out_dir / f"10jqka_gdxw_{datetime.now().strftime('%Y%m%d')}.json"
        n_new, total = _merge_write_json(fp, items)
        if n_new:
            print(f"同花顺股道：新增 {n_new} 条（累计 {total}）→ {fp}")
    return items
