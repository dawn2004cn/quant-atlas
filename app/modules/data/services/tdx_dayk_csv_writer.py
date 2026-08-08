from __future__ import annotations

"""Qlib CSV 导出写入。"""

import csv
from pathlib import Path
from typing import Any

from app.modules.data.services.tdx_dayk_sync_helpers import normalize_ohlcv_rows

CSV_COLUMNS = ("date", "open", "high", "low", "close", "volume", "amount")


def write_qlib_csv(
    export_dir: Path,
    instrument: str,
    rows: list[dict[str, Any]],
    *,
    merge: bool = False,
) -> tuple[int, str, str]:
    """写入 Qlib CSV，返回 (行数, min_date, max_date)。"""
    out_dir = Path(export_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"{instrument}.csv"
    norm = normalize_ohlcv_rows(rows)
    if not norm:
        return 0, "", ""

    if merge and csv_path.exists():
        existing: dict[str, dict[str, Any]] = {}
        with csv_path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                existing[row["date"]] = row
        for row in norm:
            existing[row["date"]] = row
        norm = sorted(existing.values(), key=lambda item: item["date"])

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(CSV_COLUMNS)
        for row in norm:
            writer.writerow([row[column] for column in CSV_COLUMNS])
    return len(norm), norm[0]["date"], norm[-1]["date"]
