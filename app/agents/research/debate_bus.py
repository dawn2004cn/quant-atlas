from __future__ import annotations
"""Publish LangGraph debate rounds to EventBus (Hybrid Arbiter pattern)."""

import re
import threading
from collections import deque
from typing import Any

from app.core.event_bus import (
    EVENT_PRIORITY_NORMAL,
    DebateRoundEvent,
    get_event_bus,
)
from app.core.logger import get_logger

logger = get_logger(__name__)

_MAX_ROUNDS_PER_SYMBOL = 60
_lock = threading.Lock()
_rounds_by_symbol: dict[str, deque[dict[str, Any]]] = {}

_STANCE_BY_ROLE = {
    "bull": "bullish",
    "bear": "bearish",
    "risky_analyst": "risk_seeking",
    "safe_analyst": "risk_averse",
}

_UNCERTAINTY_RE = re.compile(
    r"不确定|无法判断|数据不足|证据不足|尚难|难以确认|insufficient|uncertain",
    re.IGNORECASE,
)


def _symbol_key(symbol: str, market: str = "CN") -> str:
    return f"{(market or 'CN').strip().upper()}:{(symbol or '').strip().upper()}"


def _parse_symbol_market(ticker: str) -> tuple[str, str]:
    raw = (ticker or "").strip().upper()
    if ":" in raw:
        market, sym = raw.split(":", 1)
        return sym.strip(), market.strip() or "CN"
    return raw, "CN"


def estimate_debate_confidence(chunk: str) -> float:
    """Heuristic confidence from response length and uncertainty markers."""
    text = (chunk or "").strip()
    if len(text) < 40:
        return 0.25
    score = 0.55
    if len(text) >= 200:
        score += 0.15
    if len(text) >= 600:
        score += 0.1
    if _UNCERTAINTY_RE.search(text):
        score -= 0.2
    return max(0.1, min(0.95, round(score, 2)))


def publish_debate_round(
    *,
    ticker: str,
    agent_role: str,
    chunk: str,
    round_num: int,
    debate_phase: str = "investment",
    market: str | None = None,
) -> None:
    """Emit ``DebateRoundEvent`` and buffer for Arbiter synthesis."""
    symbol, inferred_market = _parse_symbol_market(ticker)
    mkt = (market or inferred_market or "CN").upper()
    if not symbol:
        return

    confidence = estimate_debate_confidence(chunk)
    stance = _STANCE_BY_ROLE.get(agent_role, "neutral")
    summary = (chunk or "").strip()[:500]

    evt = DebateRoundEvent(
        source="research_graph",
        symbol=symbol,
        market=mkt,
        round_num=round_num,
        agent_role=agent_role,
        stance=stance,
        evidence_summary=summary,
        confidence=confidence,
        priority=EVENT_PRIORITY_NORMAL,
        ttl_seconds=3600.0,
    )
    get_event_bus().publish(evt)

    record = {
        "symbol": symbol,
        "market": mkt,
        "round_num": round_num,
        "agent_role": agent_role,
        "stance": stance,
        "debate_phase": debate_phase,
        "confidence": confidence,
        "evidence_summary": summary,
        "timestamp": evt.timestamp.isoformat(),
    }
    key = _symbol_key(symbol, mkt)
    with _lock:
        buf = _rounds_by_symbol.setdefault(key, deque(maxlen=_MAX_ROUNDS_PER_SYMBOL))
        buf.append(record)
    try:
        from app.infrastructure.replay.evidence_replay_store import append_snapshot

        append_snapshot(
            symbol,
            mkt,
            event_type="DebateRoundEvent",
            payload=record,
            source="research_graph",
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("debate replay snapshot skipped: %s", exc)
    logger.debug(
        "DebateRound published sym=%s role=%s round=%s conf=%.2f",
        symbol,
        agent_role,
        round_num,
        confidence,
    )


def clear_debate_buffer() -> None:
    """Clear in-memory debate buffer (tests)."""
    with _lock:
        _rounds_by_symbol.clear()


def get_recent_debate_rounds(
    symbol: str,
    market: str = "CN",
    *,
    limit: int = 30,
    min_confidence: float = 0.0,
) -> list[dict[str, Any]]:
    """Return buffered debate rounds for Arbiter (newest last)."""
    key = _symbol_key(symbol, market)
    with _lock:
        rows = list(_rounds_by_symbol.get(key, deque()))
    filtered = [r for r in rows if float(r.get("confidence") or 0) >= min_confidence]
    return filtered[-limit:]
