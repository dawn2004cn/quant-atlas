"""System-level trading rules engine.

Enforces A-share / HK / US market rules at the application layer:

- T+1 settlement (A-share)
- Price limit up/down (10% / 20% / 5% by board)
- Minimum tick size per market
- Trading session filter (9:30-11:30 / 13:00-15:00 for A-share)

Every pre-trade route MUST call ``check()`` before accepting an order.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any

from app.domain.exceptions import (
    AuthorizationError,
    DomainError,
    ValidationError,
)


class TradingRuleViolation(DomainError):
    """Raised when a trade violates a market rule."""


class TPlus1Violation(TradingRuleViolation):
    """A-share T+1: shares bought today cannot be sold until the next
    trading day."""


class PriceLimitViolation(TradingRuleViolation):
    """Order price exceeds the market-allowed limit band."""


class MinTickViolation(TradingRuleViolation):
    """Order price is not aligned to the minimum tick size."""


class SessionViolation(TradingRuleViolation):
    """Order placed outside the trading session window."""


# ── Market Rule Constants ───────────────────────────────────────────

A_SHARE_SESSIONS = [
    (time(9, 30), time(11, 30)),  # morning
    (time(13, 0), time(15, 0)),  # afternoon
]

# code prefix → (limit_ratio, limit_label)
A_SHARE_LIMITS: dict[str, tuple[float, str]] = {
    "30": (0.20, "ChiNext 20%"),
    "68": (0.20, "STAR 20%"),
    "4": (0.05, "NEEQ 5%"),
    "8": (0.05, "NEEQ 5%"),
}

# market → (min_tick, note)
MIN_TICK: dict[str, tuple[float, str]] = {
    "CN": (0.01, "RMB 0.01"),
    "HK": (0.01, "HKD 0.01 (sub-1 prices use 0.001)"),
    "US": (0.01, "USD 0.01"),
}

STOCK_LIMIT_RATIO = 0.10  # main board default 10%


@dataclass
class RulesCheckResult:
    allowed: bool
    reason: str | None = None
    violations: list[str] | None = None


# ── Public API ──────────────────────────────────────────────────────


def check_t_plus_1(
    symbol: str,
    market: str,
    action: str,
    buy_date: date | None,
    today: date | None = None,
) -> None:
    """A-share T+1: reject sell orders for shares bought today."""
    if market != "CN" or action != "sell":
        return
    if buy_date is None:
        return  # cannot verify; let pass
    td = today or date.today()
    if buy_date == td:
        raise TPlus1Violation(
            f"A-share T+1: {symbol} bought today ({td}) cannot be sold"
            " until the next trading day."
        )


def check_price_limit(
    symbol: str,
    market: str,
    price: float,
    prev_close: float | None,
) -> None:
    """Reject orders where the price exceeds the limit band.

    Supports A-share board-specific limits (10% mainboard, 20% ChiNext/STAR,
    5% NEEQ).  Pass *prev_close* as ``None`` to skip (e.g. IPO day).
    """
    if market != "CN" or prev_close is None or prev_close <= 0:
        return

    limit = STOCK_LIMIT_RATIO
    label = "mainboard 10%"
    for prefix, (ratio, lbl) in A_SHARE_LIMITS.items():
        if symbol.startswith(prefix):
            limit = ratio
            label = lbl
            break

    lower = prev_close * (1 - limit)
    upper = prev_close * (1 + limit)
    if price < lower - 0.005 or price > upper + 0.005:
        raise PriceLimitViolation(
            f"{symbol} {label} limit: price {price:.2f} is outside"
            f" [{lower:.2f}, {upper:.2f}] (prev_close={prev_close:.2f})."
        )


def check_min_tick(
    symbol: str,
    market: str,
    price: float,
) -> None:
    """Check that *price* aligns to the minimum tick for *market*."""
    tick, _ = MIN_TICK.get(market, (0.01, ""))
    remainder = round(price / tick, 10) % 1
    if abs(remainder) > 1e-9 and abs(remainder - 1.0) > 1e-9:
        raise MinTickViolation(
            f"{market} min tick is {tick}: price {price} must be a"
            f" multiple of {tick}."
        )


def check_session(
    market: str,
    now: datetime | None = None,
) -> None:
    """Reject orders outside the trading session (A-share only)."""
    if market != "CN":
        return
    dt = now or datetime.now()
    t = dt.time()
    # weekend check
    if dt.weekday() >= 5:
        raise SessionViolation(
            f"A-share market closed on weekends (current: {dt.strftime('%A')})."
        )
    allowed = any(start <= t <= end for start, end in A_SHARE_SESSIONS)
    if not allowed:
        raise SessionViolation(
            f"A-share trading sessions are 9:30-11:30 / 13:00-15:00"
            f" (current: {t.strftime('%H:%M')})."
        )


def check_all(
    symbol: str,
    market: str,
    action: str,
    price: float,
    prev_close: float | None,
    buy_date: date | None = None,
    today: date | None = None,
    now: datetime | None = None,
) -> RulesCheckResult:
    """Run all applicable trade rules and collect violations.

    Returns a ``RulesCheckResult`` that callers can inspect or raise.
    """
    violations: list[str] = []
    try:
        check_session(market, now)
    except SessionViolation as e:
        violations.append(str(e))

    try:
        check_t_plus_1(symbol, market, action, buy_date, today)
    except TPlus1Violation as e:
        violations.append(str(e))

    try:
        check_price_limit(symbol, market, price, prev_close)
    except PriceLimitViolation as e:
        violations.append(str(e))

    try:
        check_min_tick(symbol, market, price)
    except MinTickViolation as e:
        violations.append(str(e))

    if violations:
        return RulesCheckResult(allowed=False, violations=violations)
    return RulesCheckResult(allowed=True)
