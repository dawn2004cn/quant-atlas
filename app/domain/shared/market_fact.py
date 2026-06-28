from __future__ import annotations

"""Factual price labels (MA deviation) and UI trace anchors."""

from typing import Any


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


def ma_deviation_pct(price: float, ma: float) -> float | None:
    if ma <= 0 or price <= 0:
        return None
    return round((price - ma) / ma * 100.0, 2)


def format_price_fact(
    price: float,
    ma20: float | None,
    *,
    ma5: float | None = None,
    precision: int = 2,
) -> dict[str, Any]:
    """Build factual close label, e.g. ``10.20 (vs MA20 -2.3%)``."""
    out: dict[str, Any] = {
        "price": round(price, precision),
        "close_fact": f"{price:.{precision}f}",
        "ma20_deviation_pct": None,
        "ma5_deviation_pct": None,
    }
    if ma20 and ma20 > 0:
        dev = ma_deviation_pct(price, ma20)
        out["ma20"] = round(ma20, precision)
        out["ma20_deviation_pct"] = dev
        if dev is not None:
            sign = "+" if dev > 0 else ""
            out["close_fact"] = f"{price:.{precision}f} (vs MA20 {sign}{dev:.1f}%)"
    if ma5 and ma5 > 0:
        out["ma5_deviation_pct"] = ma_deviation_pct(price, ma5)
    return out


def build_trace_ref(
    *,
    anchor: str,
    section_id: str,
    field: str = "",
    date: str = "",
    label: str = "",
    symbol: str = "",
    market: str = "CN",
    page: str = "stock_detail",
) -> dict[str, str]:
    ref = {
        "anchor": anchor,
        "section_id": section_id,
        "field": field,
        "date": (date or "")[:10],
        "label": label,
        "symbol": symbol,
        "market": (market or "CN").upper(),
        "page": page,
    }
    if symbol:
        ref["href"] = f"/stock/{symbol}?m={ref['market']}#{section_id}"
    return ref


def enrich_history_with_facts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach ``close_fact`` / ``ma20_deviation_pct`` / ``trace_ref`` per bar."""
    if not items:
        return []
    rows = [dict(x) for x in items]
    closes: list[float] = []
    for row in rows:
        closes.append(_safe_float(row.get("close") or row.get("Close")))
    out: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        close = closes[i]
        ma20 = sum(closes[max(0, i - 19) : i + 1]) / min(i + 1, 20) if close > 0 else None
        if i < 19:
            ma20 = None
        fact = format_price_fact(close, ma20)
        row.update(fact)
        date = str(row.get("date") or row.get("Date") or row.get("trade_date") or "")[:10]
        row["trace_ref"] = build_trace_ref(
            anchor="kline",
            section_id="stockChart",
            field="close",
            date=date,
            label=str(fact.get("close_fact") or ""),
        )
        out.append(row)
    return out


def enrich_quote_with_facts(
    quote: dict[str, Any],
    indicators: dict[str, Any] | None,
    *,
    symbol: str = "",
    market: str = "CN",
) -> dict[str, Any]:
    price = _safe_float(quote.get("price"))
    ind = indicators or {}
    ma20 = _safe_float(ind.get("ma20"), 0.0) or None
    ma5 = _safe_float(ind.get("ma5"), 0.0) or None
    fact = format_price_fact(price, ma20, ma5=ma5)
    fact["trace_ref"] = build_trace_ref(
        anchor="quote",
        section_id="stock-detail-hero",
        field="price",
        label=str(fact.get("close_fact") or ""),
        symbol=symbol,
        market=market,
    )
    return fact


__all__ = [
    "build_trace_ref",
    "enrich_history_with_facts",
    "enrich_quote_with_facts",
    "format_price_fact",
    "ma_deviation_pct",
]
