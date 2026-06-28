from __future__ import annotations

"""Pure helpers to build ``BarData`` from history payloads."""

from typing import Any

from app.domain.dto import BarData


def history_rows_to_bar_data_list(rows: list[Any]) -> list[BarData]:
    out: list[BarData] = []
    for row in rows:
        if isinstance(row, dict):
            bar = _from_dict(row)
        else:
            bar = _from_object(row)
        if bar is not None:
            out.append(bar)
    return out


def _from_dict(data: dict[str, Any]) -> BarData | None:
    try:
        return BarData(
            code=str(data.get("code", data.get("stock_code", "")) or ""),
            name=str(data.get("name", "") or ""),
            trade_date=str(data.get("trade_date", data.get("date", "")) or ""),
            open=float(data.get("open", 0) or 0),
            high=float(data.get("high", 0) or 0),
            low=float(data.get("low", 0) or 0),
            close=float(data.get("close", data.get("price", 0) or 0)),
            volume=float(data.get("volume", 0) or 0),
            amount=float(data.get("amount", 0) or 0),
            turnover=float(data.get("turnover", 0) or 0),
            change_pct=float(data.get("change_pct", 0) or 0),
        )
    except (TypeError, ValueError):
        return None


def _from_object(row: Any) -> BarData | None:
    try:
        return BarData(
            code=str(getattr(row, "stock_code", "") or ""),
            name=str(getattr(row, "stock_name", "") or ""),
            trade_date=str(getattr(row, "date", "") or ""),
            open=float(getattr(row, "open", 0) or 0),
            high=float(getattr(row, "high", 0) or 0),
            low=float(getattr(row, "low", 0) or 0),
            close=float(getattr(row, "close", 0) or 0),
            volume=float(getattr(row, "volume", 0) or 0),
            amount=float(getattr(row, "amount", 0) or 0),
        )
    except (TypeError, ValueError):
        return None
