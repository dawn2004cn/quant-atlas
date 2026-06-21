from __future__ import annotations
"""Pytdx 实时行情 → 业务层通用 quote dict（domain 纯函数）。"""

from typing import Any

from app.domain.dto.quote_factory import canonical_quote_payload


def pytdx_row_to_quote_payload(raw: dict[str, Any]) -> dict[str, Any]:
    """将 ``get_security_quotes`` 单行转为与行情卡片一致的字段。"""
    code = str(raw.get("code") or "").strip()
    price = float(raw.get("price") or 0)
    last_close = float(raw.get("last_close") or 0)
    if last_close <= 0:
        last_close = price
    change_amount = price - last_close if last_close else 0.0
    change_pct = (change_amount / last_close * 100.0) if last_close else 0.0
    open_p = float(raw.get("open") or 0)
    high_p = float(raw.get("high") or 0)
    low_p = float(raw.get("low") or 0)
    amplitude = ((high_p - low_p) / last_close * 100.0) if last_close and high_p and low_p else 0.0

    return canonical_quote_payload(
        {
            "code": code,
            "name": str(raw.get("name") or ""),
            "price": price,
            "change_amount": round(change_amount, 4),
            "change_pct": round(change_pct, 4),
            "volume": float(raw.get("vol") or raw.get("volume") or 0),
            "amount": float(raw.get("amount") or 0),
            "turnover": 0.0,
            "volume_ratio": 0.0,
            "amplitude": round(amplitude, 4),
            "pe": 0.0,
            "pb": 0.0,
            "industry": "",
            "open_price": open_p,
            "high_price": high_p,
            "low_price": low_p,
            "prev_close": last_close,
            "source": "tdx",
        }
    )
