from __future__ import annotations
"""通达信股本变迁 ``hq_cache/gbbq``（pytdx GbbqReader）。"""


import re
from pathlib import Path
from typing import Any


import logging
logger = logging.getLogger(__name__)
def gbbq_rows_for_code(gbbq_path: Path, code6: str, *, tail: int = 15) -> tuple[list[dict[str, Any]], str]:
    if not gbbq_path.is_file():
        return [], "gbbq_missing"
    try:
        from pytdx.reader.gbbq_reader import GbbqReader  # noqa: PLC0415
    except ImportError:
        return [], "pytdx_not_installed"

    c = "".join(x for x in code6 if x.isdigit())[-6:].zfill(6)
    if len(c) != 6:
        return [], "bad_code"

    try:
        df = GbbqReader().get_df(str(gbbq_path))
    except Exception as exc:  # noqa: BLE001
        return [], f"read_failed:{exc!s}"

    if df is None or df.empty or "code" not in df.columns:
        return [], "empty"

    def _norm(x: object) -> str:
        d = re.sub(r"\D", "", str(x))
        return d[-6:].zfill(6) if len(d) >= 4 else ""

    sub = df[df["code"].map(_norm) == c]
    if sub.empty:
        return [], "no_rows"

    tail = max(1, min(tail, 80))
    sub = sub.tail(tail)
    out: list[dict[str, Any]] = []
    for _, row in sub.iterrows():
        rec: dict[str, Any] = {}
        for col in sub.columns:
            v = row[col]
            if hasattr(v, "item"):
                try:
                    v = v.item()
                except Exception:  # noqa: BLE001 as e:
                    logger.warning("tdx_gbbq.py.gbbq_rows_for_code: %s", e)
            rec[str(col)] = float(v) if isinstance(v, (int, float)) else str(v)
        out.append(rec)
    return out, "ok"
