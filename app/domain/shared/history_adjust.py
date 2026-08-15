"""History adjust helpers inspired by local quant engines (qfq/hfq/raw).

Does not embed external C++ engines; uses existing TDX local readers when available.
"""

from __future__ import annotations

from typing import Any

from app.domain.enums import MarketCode

_ADJUST_ALIASES = {
    "qfq": "qfq",
    "forward": "qfq",
    "前复权": "qfq",
    "hfq": "hfq",
    "backward": "hfq",
    "后复权": "hfq",
    "raw": "raw",
    "none": "raw",
    "bfq": "raw",
    "unadjusted": "raw",
    "不复权": "raw",
}


def normalize_adjust(value: str | None, *, default: str = "qfq") -> str:
    """Normalize adjust mode to qfq | hfq | raw."""
    key = (value or default).strip().lower()
    return _ADJUST_ALIASES.get(key, default if default in ("qfq", "hfq", "raw") else "qfq")


def try_local_cn_history(
    symbol: str,
    start: str,
    end: str,
    adjust: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch CN bars from local TDX lday when present.

    ``raw`` → unadjusted file; ``qfq``/``hfq`` → qfq reader (hfq may note fallback).
    """
    mode = normalize_adjust(adjust)
    meta: dict[str, Any] = {
        "adjust": mode,
        "adjust_applied": False,
        "adjust_source": None,
    }
    try:
        from app.infrastructure.providers.cn_tdx_provider import TdxHistoryProvider

        use_qfq = mode != "raw"
        provider = TdxHistoryProvider(use_qfq=use_qfq)
        bars = provider.get_stock_history(symbol, MarketCode.CN, start, end) or []
        if not bars:
            return [], meta
        meta["adjust_applied"] = True
        meta["adjust_source"] = "tdx_local"
        meta["adjust_served"] = "qfq" if use_qfq else "raw"
        if mode == "hfq":
            # Local lday path currently exposes qfq/raw; mark honest fallback.
            meta["adjust_note"] = "requested_hfq_served_qfq"
            meta["adjust_served"] = "qfq"
        # stringify dates for JSON
        out: list[dict[str, Any]] = []
        for row in bars:
            item = dict(row)
            d = item.get("date")
            if hasattr(d, "strftime"):
                item["date"] = d.strftime("%Y-%m-%d")
            elif d is not None:
                item["date"] = str(d)[:10]
            out.append(item)
        return out, meta
    except Exception as exc:  # noqa: BLE001 — boundary helper
        meta["adjust_error"] = str(exc)
        return [], meta
