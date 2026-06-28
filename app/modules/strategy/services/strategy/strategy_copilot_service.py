from __future__ import annotations

"""StrategyCoPilotService — shadow strategy evaluation and live handover suggestions."""

from datetime import datetime, timedelta
from typing import Any

from app.application.use_cases.strategy_copilot_use_case import StrategyCopilotUseCase
from app.core.logger import get_logger
from app.domain.enums import MarketCode
from app.domain.sequence_chain import new_provenance_id

logger = get_logger(__name__)

_HANDOVER_CONFIDENCE_MIN = 0.8
_SHADOW_HOURS = 48
_OUTPERFORM_MARGIN = 1.05  # shadow must beat active by 5%


class StrategyCoPilotService:
    """Orchestrate regime analysis, shadow runs and arbiter-gated handover."""

    def __init__(
        self,
        *,
        copilot_use_case: StrategyCopilotUseCase | None = None,
        debate_arbiter_service: Any | None = None,
        stock_service: Any | None = None,
    ) -> None:
        self._use_case = copilot_use_case or StrategyCopilotUseCase()
        self._arbiter = debate_arbiter_service
        self._stock = stock_service
        self._active_strategy: dict[str, str] = {}

    def set_active_strategy(self, symbol: str, strategy_id: str, market: str = "CN") -> None:
        key = f"{market.upper()}:{symbol.strip().lower()}"
        self._active_strategy[key] = strategy_id

    def get_active_strategy(self, symbol: str, market: str = "CN") -> str:
        key = f"{market.upper()}:{symbol.strip().lower()}"
        return self._active_strategy.get(key, "trend_following")

    def evaluate(
        self,
        symbol: str,
        market: MarketCode = MarketCode.CN,
        *,
        active_strategy_id: str | None = None,
    ) -> dict[str, Any]:
        """Run copilot analysis + 48h shadow comparison."""
        analysis = self._use_case.execute(symbol, market)
        if analysis.get("error"):
            return {"ok": False, **analysis}

        active_id = active_strategy_id or self.get_active_strategy(symbol, market.value)
        bars = self._load_recent_bars(symbol, market, days=5)
        shadows = self._run_shadows(analysis.get("recommendations") or [], bars)
        active_perf = self._simulate_strategy(active_id, bars)

        arbiter = self._arbiter_consensus(symbol, market.value)
        handover = self._build_handover(
            symbol=symbol,
            market=market.value,
            active_id=active_id,
            active_perf=active_perf,
            shadows=shadows,
            arbiter=arbiter,
        )

        return {
            "ok": True,
            "symbol": symbol,
            "market": market.value,
            "analysis": analysis,
            "active_strategy": {
                "strategy_id": active_id,
                "return_48h_pct": round(active_perf, 4),
            },
            "shadow_strategies": shadows,
            "arbiter": arbiter,
            "handover": handover,
            "evaluated_at": datetime.now().isoformat(),
        }

    def _run_shadows(
        self,
        recommendations: list[dict[str, Any]],
        bars: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        seen: set[str] = set()
        shadows: list[dict[str, Any]] = []
        for rec in recommendations[:5]:
            sid = str(rec.get("strategy") or "")
            if not sid or sid in seen:
                continue
            seen.add(sid)
            ret = self._simulate_strategy(sid, bars)
            shadows.append(
                {
                    "strategy_id": sid,
                    "fit_score": rec.get("score"),
                    "reason": rec.get("reason", ""),
                    "return_48h_pct": round(ret, 4),
                    "window_bars": len(bars),
                }
            )
        shadows.sort(key=lambda x: x["return_48h_pct"], reverse=True)
        return shadows

    def _build_handover(
        self,
        *,
        symbol: str,
        market: str,
        active_id: str,
        active_perf: float,
        shadows: list[dict[str, Any]],
        arbiter: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not shadows:
            return None
        best = shadows[0]
        conf = float(arbiter.get("confidence") or 0.0)
        beats = best["return_48h_pct"] >= active_perf * _OUTPERFORM_MARGIN
        if not beats or conf < _HANDOVER_CONFIDENCE_MIN:
            return {
                "eligible": False,
                "reason": "shadow_underperform_or_low_confidence",
                "required_confidence": _HANDOVER_CONFIDENCE_MIN,
                "arbiter_confidence": conf,
            }
        return {
            "eligible": True,
            "suggestion_id": new_provenance_id().replace("prov-", "handover-"),
            "from_strategy": active_id,
            "to_strategy": best["strategy_id"],
            "active_return_48h_pct": round(active_perf, 4),
            "shadow_return_48h_pct": best["return_48h_pct"],
            "arbiter_verdict": arbiter.get("verdict"),
            "arbiter_confidence": conf,
            "message": (
                f"影子策略 {best['strategy_id']} 近{_SHADOW_HOURS}h 表现优于当前 {active_id}，"
                f"仲裁置信度 {conf:.0%}，建议一键切换。"
            ),
            "action": {
                "method": "POST",
                "href": "/api/v1/strategy/copilot/handover",
                "body": {
                    "symbol": symbol,
                    "market": market,
                    "from_strategy": active_id,
                    "to_strategy": best["strategy_id"],
                },
            },
        }

    def apply_handover(
        self,
        symbol: str,
        to_strategy: str,
        market: str = "CN",
    ) -> dict[str, Any]:
        """Switch active strategy (in-memory; persisted via user prefs in future)."""
        from_id = self.get_active_strategy(symbol, market)
        self.set_active_strategy(symbol, to_strategy, market)
        return {
            "ok": True,
            "symbol": symbol.strip().lower(),
            "market": market.upper(),
            "from_strategy": from_id,
            "to_strategy": to_strategy,
            "switched_at": datetime.now().isoformat(),
        }

    def _arbiter_consensus(self, symbol: str, market: str) -> dict[str, Any]:
        if self._arbiter is None:
            return {"ok": False, "confidence": 0.0}
        try:
            result = self._arbiter.synthesize(symbol, market)
            return result if isinstance(result, dict) else {}
        except Exception as exc:
            logger.warning("copilot arbiter consensus failed: %s", exc)
            return {"ok": False, "confidence": 0.0}

    def _load_recent_bars(
        self,
        symbol: str,
        market: MarketCode,
        *,
        days: int = 5,
    ) -> list[dict[str, Any]]:
        if self._stock is None:
            return []
        end = datetime.now().date()
        start = end - timedelta(days=days)
        try:
            raw = self._stock.get_history(
                symbol, market, start.isoformat(), end.isoformat()
            )
            if isinstance(raw, list):
                return raw
            if isinstance(raw, dict):
                return list(raw.get("history") or [])
        except Exception as exc:
            logger.warning("copilot bars load failed: %s", exc)
        return []

    @staticmethod
    def _simulate_strategy(strategy_id: str, bars: list[dict[str, Any]]) -> float:
        """Lightweight 48h-ish return proxy from recent OHLCV bars."""
        closes = [
            float(b.get("close") or b.get("close_price") or 0)
            for b in bars
            if float(b.get("close") or b.get("close_price") or 0) > 0
        ]
        if len(closes) < 2:
            return 0.0
        total_ret = (closes[-1] - closes[0]) / closes[0] * 100
        last_ret = (closes[-1] - closes[-2]) / closes[-2] * 100

        sid = strategy_id.lower()
        if sid in ("momentum", "trend_following", "breakout", "dual_thrust"):
            return total_ret
        if sid in ("mean_reversion", "short_reversal", "grid_trading"):
            return -last_ret if abs(last_ret) > 0.1 else total_ret * 0.3
        if sid == "macd_divergence":
            return total_ret * 0.5
        return total_ret
