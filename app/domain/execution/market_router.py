from __future__ import annotations
"""Symbol → market → execution driver routing."""

import re

from app.domain.enums import MARKET_CURRENCIES, MarketCode
from app.domain.execution.execution_schema import ExecutionRouteDescriptor

_CRYPTO_RE = re.compile(r"^(BTC|ETH|SOL|BNB|DOGE|XRP|ADA|USDT|USDC)(USDT|USD|BUSD)?$", re.I)
_HK_SUFFIX_RE = re.compile(r"\.HK$", re.I)
_CN_PREFIX_RE = re.compile(r"^(SH|SZ|BJ)\d{6}$", re.I)
_CN_SIX_DIGIT_RE = re.compile(r"^\d{6}$")


def infer_market(symbol: str, market_hint: str | None = None) -> MarketCode:
    hint = (market_hint or "").strip().upper()
    if hint in {m.value for m in MarketCode}:
        return MarketCode(hint)

    raw = (symbol or "").strip().upper()
    if ":" in raw:
        prefix, sym = raw.split(":", 1)
        if prefix in {m.value for m in MarketCode}:
            return MarketCode(prefix)
        raw = sym.strip().upper()

    if _HK_SUFFIX_RE.search(raw):
        return MarketCode.HK
    if raw.endswith(".SH") or raw.endswith(".SZ"):
        return MarketCode.CN
    if _CN_PREFIX_RE.match(raw) or _CN_SIX_DIGIT_RE.match(raw):
        return MarketCode.CN
    if _CRYPTO_RE.match(raw):
        return MarketCode.CRYPTO
    if raw.isalpha() and len(raw) <= 5:
        return MarketCode.US
    return MarketCode.CN


def _normalize_symbol(symbol: str, market: MarketCode) -> str:
    raw = (symbol or "").strip().upper()
    if ":" in raw:
        _, sym = raw.split(":", 1)
        raw = sym.strip().upper()
    if market == MarketCode.CN:
        raw = raw.replace(".SH", "").replace(".SZ", "")
        if raw.startswith(("SH", "SZ", "BJ")) and len(raw) > 2:
            raw = raw[2:]
    if market == MarketCode.HK and not raw.endswith(".HK"):
        raw = f"{raw}.HK" if raw.isdigit() else raw
    return raw


def resolve_execution_route(
    symbol: str,
    *,
    market_hint: str | None = None,
    mode: str = "paper",
    exchange_hint: str = "",
) -> ExecutionRouteDescriptor:
    market = infer_market(symbol, market_hint)
    sym = _normalize_symbol(symbol, market)
    currency = MARKET_CURRENCIES.get(market, "USD")

    driver_id, exchange, evidence = _pick_driver(market, mode, exchange_hint)
    return ExecutionRouteDescriptor(
        symbol=sym,
        market=market,
        driver_id=driver_id,
        exchange=exchange,
        currency=currency,
        mode=mode,
        evidence=evidence,
        confidence=0.92 if market != MarketCode.CRYPTO else 0.85,
    )


def _pick_driver(market: MarketCode, mode: str, exchange_hint: str) -> tuple[str, str, str]:
    m = (mode or "paper").strip().lower()
    if m == "qmt" and market == MarketCode.CN:
        return "qmt_cn", exchange_hint or "qmt", "QMT gateway for A-share live execution"
    if m == "redis" or market == MarketCode.CRYPTO:
        ex = exchange_hint or {
            MarketCode.CN: "simulate_cn",
            MarketCode.US: "simulate_us",
            MarketCode.HK: "simulate_hk",
            MarketCode.CRYPTO: "binance",
        }.get(market, "binance")
        return f"redis_{market.value.lower()}", ex, f"Redis stream executor ({market.value})"
    ex = exchange_hint or {
        MarketCode.CN: "paper_cn",
        MarketCode.US: "paper_us",
        MarketCode.HK: "paper_hk",
        MarketCode.CRYPTO: "paper_crypto",
    }.get(market, "paper")
    return f"paper_{market.value.lower()}", ex, f"Paper/simulated fill ({market.value})"


__all__ = ["infer_market", "resolve_execution_route"]
