from __future__ import annotations

"""Validate normalized OHLCV history rows before MySQL persist."""

from typing import Any

from app.application.errors import ValidationError
from app.core.logger import get_logger

logger = get_logger(__name__)

_REQUIRED_FIELDS = ("date", "open", "high", "low", "close")
_NUMERIC_FIELDS = ("open", "high", "low", "close", "volume", "amount")


def _is_valid_trade_date(date_str: str) -> bool:
    from datetime import datetime

    try:
        datetime.strptime(date_str[:10], "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validate_ohlcv_history_rows(rows: list[Any]) -> list[dict[str, Any]]:
    """Normalize and validate OHLCV rows for day-K write paths."""
    if not isinstance(rows, list) or not rows:
        raise ValidationError("rows_required")

    out: list[dict[str, Any]] = []
    skipped = 0
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValidationError("invalid_row", details={"index": index})

        missing = [field for field in _REQUIRED_FIELDS if row.get(field) in (None, "")]
        if missing:
            raise ValidationError(
                "invalid_row_field",
                details={"index": index, "fields": missing},
            )

        date_str = str(row.get("date") or "")[:10]
        if len(date_str) != 10 or not _is_valid_trade_date(date_str):
            skipped += 1
            continue
        normalized: dict[str, Any] = {"date": date_str}
        for field in _NUMERIC_FIELDS:
            if field not in row and field in ("volume", "amount"):
                normalized[field] = 0.0
                continue
            try:
                normalized[field] = float(row.get(field) or 0)
            except (TypeError, ValueError) as exc:
                raise ValidationError(
                    "invalid_row_numeric",
                    details={"index": index, "field": field},
                ) from exc

        out.append(normalized)
    if skipped:
        logger.warning("validate_ohlcv_history_rows: skipped %d invalid-date rows", skipped)
    if not out:
        raise ValidationError("rows_required")
    return out