from __future__ import annotations

"""Arbiter review learning — adjust debate stance weights from outcome feedback."""

import json
from pathlib import Path
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_WEIGHTS: dict[str, float] = {
    "bullish": 1.0,
    "bearish": -1.0,
    "risk_seeking": 0.35,
    "risk_averse": -0.35,
    "neutral": 0.0,
}

_MIN_WEIGHT = 0.15
_MAX_WEIGHT = 1.5


class ArbiterReviewLearningService:
    """Persist arbiter outcomes and nudge stance weights for future synthesize calls."""

    def __init__(
        self,
        store_path: Path | str | None = None,
        *,
        cross_team_meta_learning_service: Any | None = None,
    ) -> None:
        from app.config import BASE_DIR

        self._path = Path(store_path or BASE_DIR / "instance" / "arbiter_learning.json")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()
        self._cross_team = cross_team_meta_learning_service

    def get_stance_weights(self) -> dict[str, float]:
        adj = self._data.get("weight_adjustments") or {}
        out = dict(_DEFAULT_WEIGHTS)
        for key, base in _DEFAULT_WEIGHTS.items():
            delta = float(adj.get(key, 0.0) or 0.0)
            val = base + delta if key != "neutral" else base
            if key == "bearish":
                val = max(-_MAX_WEIGHT, min(-_MIN_WEIGHT, val))
            elif key != "neutral":
                val = max(_MIN_WEIGHT, min(_MAX_WEIGHT, abs(val)))
                if key == "bearish":
                    val = -val
            out[key] = val
        return out

    def record_review(
        self,
        *,
        provenance_id: str,
        symbol: str,
        market: str,
        predicted_verdict: str,
        actual_outcome: str,
        pnl_pct: float | None = None,
        notes: str = "",
    ) -> dict[str, Any]:
        """Record a post-trade review and adjust weights when prediction was wrong."""
        review = {
            "provenance_id": provenance_id,
            "symbol": symbol.strip().lower(),
            "market": market.upper(),
            "predicted_verdict": predicted_verdict.strip().lower(),
            "actual_outcome": actual_outcome.strip().lower(),
            "pnl_pct": pnl_pct,
            "notes": notes,
        }
        reviews: list[dict[str, Any]] = list(self._data.get("reviews") or [])
        reviews.append(review)
        self._data["reviews"] = reviews[-200:]

        adjustment = self._compute_adjustment(review)
        if adjustment:
            adj_map: dict[str, float] = dict(self._data.get("weight_adjustments") or {})
            for stance, delta in adjustment.items():
                adj_map[stance] = round(float(adj_map.get(stance, 0.0)) + delta, 4)
            self._data["weight_adjustments"] = adj_map
            review["weight_adjustment"] = adjustment

        self._save()
        pattern_shared = None
        if self._cross_team is not None:
            try:
                pattern_shared = self._cross_team.share_pattern_from_review(
                    predicted_verdict=predicted_verdict,
                    actual_outcome=actual_outcome,
                    market=market,
                    pnl_pct=pnl_pct,
                )
            except Exception as exc:
                logger.debug("arbiter_review cross_team pattern: %s", exc)
        logger.info(
            "Arbiter review recorded sym=%s predicted=%s outcome=%s adj=%s",
            symbol,
            predicted_verdict,
            actual_outcome,
            review.get("weight_adjustment"),
        )
        return {
            "ok": True,
            "review": review,
            "stance_weights": self.get_stance_weights(),
            "anonymous_pattern": pattern_shared,
        }

    def list_reviews(self, *, symbol: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        rows = list(self._data.get("reviews") or [])
        if symbol:
            sym = symbol.strip().lower()
            rows = [r for r in rows if str(r.get("symbol", "")).lower() == sym]
        return rows[-limit:]

    def _compute_adjustment(self, review: dict[str, Any]) -> dict[str, float]:
        predicted = str(review.get("predicted_verdict") or "")
        outcome = str(review.get("actual_outcome") or "")
        pnl = review.get("pnl_pct")
        wrong = (
            (predicted == "bullish" and outcome in ("loss", "bearish", "stop_hit"))
            or (predicted == "bearish" and outcome in ("gain", "bullish", "missed_rally"))
            or (predicted == "bullish" and isinstance(pnl, (int, float)) and pnl < -1.0)
            or (predicted == "bearish" and isinstance(pnl, (int, float)) and pnl > 1.0)
        )
        if not wrong:
            return {}
        delta = 0.08
        adj: dict[str, float] = {}
        if predicted == "bullish":
            adj["bullish"] = -delta
            adj["bearish"] = delta * 0.5
        elif predicted == "bearish":
            adj["bearish"] = delta
            adj["bullish"] = -delta * 0.5
        else:
            adj["neutral"] = -delta * 0.25
        return adj

    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {"weight_adjustments": {}, "reviews": []}
        try:
            with self._path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                return data
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("arbiter_learning load failed: %s", exc)
        return {"weight_adjustments": {}, "reviews": []}

    def _save(self) -> None:
        try:
            with self._path.open("w", encoding="utf-8") as fh:
                json.dump(self._data, fh, ensure_ascii=False, indent=2)
        except OSError as exc:
            logger.warning("arbiter_learning save failed: %s", exc)
