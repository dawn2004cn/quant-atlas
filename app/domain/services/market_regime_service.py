"""Market regime domain service - pure logic, zero framework dependency."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DEFAULT_CONFIG_PATH = "config/market_regime_config.json"

_DEFAULT_CONFIG = {
    "stances": {
        "score_thresholds": {"aggressive_lower": 62, "defensive_upper": 38},
        "labels": {"aggressive": "aggressive", "defensive": "defensive", "neutral": "neutral"},
        "messages": {
            "aggressive": "Environment favorable; execute plan around core holdings.",
            "defensive": "Overall pressure; control positions, avoid bottom-fishing.",
            "neutral": "Rotational divergence; verify signals step by step.",
        },
    },
    "adjustments": {
        "down_ratio_high": {"threshold": 0.55, "penalty": 6},
        "up_dominance": {"ratio": 1.4, "bonus": 4},
        "stop_hit_base": 4, "stop_hit_per": 3, "stop_hit_max": 12,
        "target_hit_base": 2, "target_hit_per": 2, "target_hit_max": 8,
        "watchlist_avg_bear": {"threshold": -1.5, "penalty": 4},
        "watchlist_avg_bull": {"threshold": 1.2, "bonus": 3},
    },
    "bounds": {"min_score": 8, "max_score": 94},
    "confidence": {"min": 0.35, "max": 0.92, "offset": 0.45, "factor": 0.5},
}


def _load_config(path: str | None = None) -> dict[str, Any]:
    """Load market regime config from JSON file, falling back to defaults."""
    if path is None:
        root = Path(__file__).resolve().parents[3]
        path = str(root / _DEFAULT_CONFIG_PATH)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(_DEFAULT_CONFIG)


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Safely convert value to float, returning default on failure."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


class MarketRegimeService:
    """Pure domain service for market stance determination.

    Encapsulates all scoring rules so that consumers (e.g. DailyWorkbenchService)
    only call a single method and receive a structured decision.
    """

    def __init__(self, config_path: str | None = None) -> None:
        cfg = _load_config(config_path)
        self._stances = cfg["stances"]
        self._adj = cfg["adjustments"]
        self._bounds = cfg["bounds"]
        self._conf = cfg["confidence"]

    def evaluate_stance(
        self,
        *,
        sentiment_score: float = 50.0,
        up_count: int = 0,
        down_count: int = 0,
        flat_count: int = 0,
        observation_cards: list[dict[str, Any]] | None = None,
        watchlist_items: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Determine the market stance based on quantitative signals.

        Returns a structured decision dict with stance, score, action,
        evidence list, and confidence.
        """
        base = int(round(_safe_float(sentiment_score, 50.0)))
        up = int(_safe_float(up_count))
        down = int(_safe_float(down_count))
        flat = int(_safe_float(flat_count))
        total = max(up + down + flat, 1)
        down_ratio = down / total

        obs = observation_cards or []
        stop_n = sum(1 for o in obs if o.get("trigger_status") == "stop_hit")
        tgt_n = sum(1 for o in obs if o.get("trigger_status") == "target_hit")

        wl = watchlist_items or []
        wl_chg = [_safe_float(x.get("change_pct")) for x in wl]
        wl_avg = sum(wl_chg) / len(wl_chg) if wl_chg else 0.0

        score = max(self._bounds["min_score"], min(self._bounds["max_score"], base))
        adj = self._adj

        if down_ratio > adj["down_ratio_high"]["threshold"]:
            score -= adj["down_ratio_high"]["penalty"]
        if up > down * adj["up_dominance"]["ratio"]:
            score += adj["up_dominance"]["bonus"]
        if stop_n:
            score -= min(adj["stop_hit_max"], adj["stop_hit_base"] + stop_n * adj["stop_hit_per"])
        if tgt_n:
            score += min(adj["target_hit_max"], adj["target_hit_base"] + tgt_n * adj["target_hit_per"])
        if wl_avg < adj["watchlist_avg_bear"]["threshold"]:
            score -= adj["watchlist_avg_bear"]["penalty"]
        elif wl_avg > adj["watchlist_avg_bull"]["threshold"]:
            score += adj["watchlist_avg_bull"]["bonus"]
        score = max(self._bounds["min_score"], min(self._bounds["max_score"], score))

        thresholds = self._stances["score_thresholds"]
        if score >= thresholds["aggressive_lower"]:
            stance = self._stances["labels"]["aggressive"]
            action = self._stances["messages"]["aggressive"]
        elif score <= thresholds["defensive_upper"]:
            stance = self._stances["labels"]["defensive"]
            action = self._stances["messages"]["defensive"]
        else:
            stance = self._stances["labels"]["neutral"]
            action = self._stances["messages"]["neutral"]

        c = self._conf
        confidence = round(min(c["max"], max(c["min"], abs(score - 50) / 50.0 * c["factor"] + c["offset"])), 2)

        evidence = [
            {
                "kind": "sentiment",
                "label": "Market Sentiment",
                "value": f"score={base}",
                "confidence": round(min(0.9, 0.55 + abs(base - 50) / 80), 2),
            },
            {
                "kind": "breadth",
                "label": "Up/Down Structure",
                "value": f"{up}:{down}:{flat}",
                "confidence": 0.72,
            },
        ]
        if obs:
            evidence.append({
                "kind": "observation",
                "label": "Open Cards",
                "value": f"open={len(obs)} stop={stop_n} target={tgt_n}",
                "confidence": 0.68,
            })

        return {
            "stance": stance,
            "score": score,
            "action": action,
            "confidence": confidence,
            "evidence": evidence,
        }
