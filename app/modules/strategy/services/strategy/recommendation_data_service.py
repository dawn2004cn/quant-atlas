"""Data fetching service for recommendation — Phase C split.

Extracted from recommendation_service.py to separate data access concerns.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.logger import get_logger
from app.domain.dto.service_result import GenericResponseDTO
from app.domain.enums import MarketCode

logger = get_logger(__name__)


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


class RecommendationDataService:
    """Fetches and loads raw recommendation data from various sources."""

    def __init__(
        self,
        *,
        signal_flag_service: Any | None = None,
        selection_source_service: object | None = None,
        ai_evidence_service: object | None = None,
        signal_observation_service: Any | None = None,
    ) -> None:
        self._signal_flag = signal_flag_service
        self._selection = selection_source_service
        self._ai_evidence = ai_evidence_service
        self._observations = signal_observation_service

    def candidate_rows(self, market: MarketCode, *, limit: int) -> list[dict[str, Any]]:
        """Fetch candidate stock rows from signal flag pool or selection fallback."""
        rows: list[dict[str, Any]] = []
        if self._signal_flag is not None and market == MarketCode.CN:
            try:
                pool_date = datetime.now().strftime("%Y-%m-%d")
                pool = self._signal_flag.get_pool(pool_date) or []
                if isinstance(pool, dict):
                    return rows
                for item in pool:
                    code = str(item.get("code") or item.get("symbol") or "").strip()
                    if not code:
                        continue
                    rows.append(
                        {
                            "code": code,
                            "name": item.get("name") or code,
                            "score": item.get("score"),
                            "safety_score": item.get("safety_score") or item.get("score"),
                            "amount": item.get("amount"),
                            "industry": item.get("industry"),
                            "source": "signal_flag",
                            "signal_strategies": item.get("signal_strategies")
                            or item.get("buy_signals"),
                            "price": item.get("price") or item.get("current_price"),
                        }
                    )
            except Exception as exc:
                logger.warning("recommendation signal_flag pool: %s", exc)

        if not rows:
            try:
                selected = self._selection.select_stocks(
                    strategy="horizon:mid",
                    market=market,
                    top_n=limit,
                    data_source="legacy",
                    enable_qlib=False,
                )
                rows = list(selected.get("candidates") or [])
                for row in rows:
                    row.setdefault("source", "selection")
            except Exception as exc:
                logger.warning("recommendation selection fallback unavailable: %s", exc)

        rows.sort(
            key=lambda x: (
                _safe_float(x.get("safety_score") or x.get("score")),
                _safe_float(x.get("amount")),
            ),
            reverse=True,
        )
        return rows[:limit]

    def safe_evidence(self, code: str, market: MarketCode) -> GenericResponseDTO:
        """Fetch AI evidence bundle for a given stock."""
        try:
            return self._ai_evidence.build_bundle(symbol=code, market=market, include_news=True)
        except Exception as exc:
            logger.warning("recommendation evidence failed for %s: %s", code, exc)
            return {"trust": {"score": 0, "level": ""}, "calibration": {}}

    def agent_calibration(self, code: str) -> dict[str, Any]:
        """Blend AutoValidator agent-memory accuracy into ranking."""
        try:
            from app.agents.agent_memory import get_agent_memory

            patterns = get_agent_memory().get_historical_patterns(code)
            if patterns.get("pattern") == "insufficient_data":
                return {"boost": 0.0, "samples": 0, "avg_accuracy": 0.0, "source": "auto_validator"}

            samples = int(patterns.get("total_decisions") or 0)
            avg_accuracy = float(patterns.get("avg_accuracy") or 0.5)
            boost = round((avg_accuracy - 0.5) * 14.0, 2) if samples >= 2 else 0.0

            return {
                "boost": boost,
                "samples": samples,
                "avg_accuracy": round(avg_accuracy, 4),
                "source": "auto_validator",
            }
        except Exception as exc:
            logger.debug("recommendation agent calibration %s: %s", code, exc)
            return {"boost": 0.0, "samples": 0, "avg_accuracy": 0.0, "source": "auto_validator"}

    def estimated_win_rate(
        self,
        code: str,
        agent_cal: dict[str, Any] | None = None,
        *,
        user_id: int | None = None,
    ) -> GenericResponseDTO:
        """Estimate win rate combining observation data and agent calibration."""
        base: dict[str, Any] = {"rate": 0.0, "samples": 0, "source": "no_observation_data"}
        if self._observations is not None:
            try:
                uid = int(user_id) if user_id else 1
                rows = self._observations.list_observations(
                    user_id=uid, status="all", refresh=True
                ).get("items") or []
            except Exception:
                rows = []

            matched = [r for r in rows if str(r.get("symbol") or "").upper() == code.upper()]
            if matched:
                wins = len(
                    [
                        r
                        for r in matched
                        if _safe_float(r.get("return_pct")) > 0
                        or r.get("trigger_status") == "target_hit"
                    ]
                )
                base = {
                    "rate": round(wins / len(matched) * 100, 2),
                    "samples": len(matched),
                    "source": "symbol_observation",
                }
            else:
                stats = self._observations.stats().get("items") or []
                signal_stats = next(
                    (x for x in stats if x.get("source") in ("signal_flag", "daily_workbench")),
                    None,
                )
                base = {
                    "rate": signal_stats.get("target_hit_rate", 0) if signal_stats else 0,
                    "samples": signal_stats.get("count", 0) if signal_stats else 0,
                    "source": "source_level_observation",
                }

        cal = agent_cal or {}
        agent_samples = int(cal.get("samples") or 0)
        if agent_samples >= 2:
            agent_rate = round(float(cal.get("avg_accuracy") or 0.0) * 100, 2)
            obs_rate = _safe_float(base.get("rate"))
            obs_n = int(base.get("samples") or 0)
            if obs_n > 0:
                blended = round(obs_rate * 0.6 + agent_rate * 0.4, 2)
            else:
                blended = agent_rate
            base["rate"] = blended
            base["agent_accuracy_pct"] = agent_rate
            base["agent_samples"] = agent_samples
            base["source"] = f"{base.get('source', 'obs')}+auto_validator"

        return base
