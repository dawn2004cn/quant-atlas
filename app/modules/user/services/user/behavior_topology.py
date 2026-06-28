from __future__ import annotations

from datetime import datetime
from typing import Any


def analyze_behavior_topology(profile: dict[str, Any]) -> dict[str, Any]:
    """Analyze a user's behavioral profile and return topology insights.

    Detects cognitive biases, fatigue levels, and generates alerts.
    """
    interaction_events: list[dict[str, Any]] = profile.get("interaction_events", [])
    decision_patterns: list[dict[str, Any]] = profile.get("decision_patterns", [])
    user_id: str = profile.get("user_id", "unknown")

    result: dict[str, Any] = {
        "user_id": user_id,
        "cognitive_biases": [],
        "fatigue_level": "low",
        "alerts": [],
    }

    # --- Cognitive Bias Detection ---
    biases = _detect_cognitive_biases(interaction_events, decision_patterns)
    result["cognitive_biases"] = biases

    # --- Fatigue Detection ---
    fatigue = _compute_fatigue_level(interaction_events)
    result["fatigue_level"] = fatigue

    if fatigue == "high":
        result["alerts"].append({
            "code": "research_fatigue",
            "level": "warning",
            "message": "Research fatigue detected — consider taking a break.",
        })

    return result


def _detect_cognitive_biases(
    events: list[dict[str, Any]],
    patterns: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Detect cognitive biases from interaction events and decision patterns."""
    biases: list[dict[str, Any]] = []

    # Confirmation bias: repeated bullish/bearish stances without counter-views
    stance_counts: dict[str, int] = {}
    for ev in events:
        stance = ev.get("stance", "")
        if stance:
            stance_counts[stance] = stance_counts.get(stance, 0) + 1

    if stance_counts:
        dominant = max(stance_counts, key=stance_counts.get)
        total = sum(stance_counts.values())
        ratio = stance_counts[dominant] / total if total else 0
        if ratio > 0.7 and total >= 5:
            biases.append({
                "type": "confirmation_bias",
                "severity": "warning",
                "detail": f"Overwhelmingly {dominant} stance ({ratio:.0%})",
                "suggestion": "Seek contrary viewpoints before final decisions.",
            })

    # Herding bias: many events on same symbols
    symbol_counts: dict[str, int] = {}
    for ev in events:
        for sym in ev.get("symbols", []):
            symbol_counts[sym] = symbol_counts.get(sym, 0) + 1

    if symbol_counts:
        top_symbol, top_count = max(symbol_counts.items(), key=lambda x: x[1])
        if top_count >= 5:
            biases.append({
                "type": "herding_bias",
                "severity": "info",
                "detail": f"Heavy focus on {top_symbol} ({top_count} interactions)",
                "suggestion": "Verify independent rationale for concentrated positions.",
            })

    # Overtrading: excessive event frequency
    if len(events) >= 15:
        biases.append({
            "type": "overtrading_tendency",
            "severity": "warning",
            "detail": f"{len(events)} interaction events in observed window",
            "suggestion": "Review trade frequency against strategy rules.",
        })

    return biases


def _compute_fatigue_level(events: list[dict[str, Any]]) -> str:
    """Compute fatigue level based on event density and recency."""
    if len(events) < 5:
        return "low"

    timestamps: list[datetime] = []
    for ev in events:
        ts_str = ev.get("recorded_at", "")
        if ts_str:
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                timestamps.append(ts)
            except ValueError:
                continue

    if len(timestamps) < 3:
        return "low"

    timestamps.sort()
    span = (timestamps[-1] - timestamps[0]).total_seconds()

    # High fatigue: 15+ events within 30 minutes
    if len(timestamps) >= 15 and span > 0 and span < 1800:
        return "high"

    # Medium: 10+ events within 1 hour
    if len(timestamps) >= 10 and span > 0 and span < 3600:
        return "medium"

    return "low"
