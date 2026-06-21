from __future__ import annotations

"""Fast strategy sensitivity simulation for Strategy Copilot."""

from typing import Any


class SensitivitySandboxService:
    """Adjust Copilot scores without running a heavy backtest."""

    def simulate(
        self,
        copilot_result: dict[str, Any],
        *,
        market_shock_pct: float = 0.0,
        volatility_threshold: float | None = None,
        stop_loss_pct: float | None = None,
    ) -> dict[str, Any]:
        base_recs = copilot_result.get("recommendations") or []
        volatility = self._safe_float(copilot_result.get("volatility"), 0.0)
        threshold = volatility_threshold if volatility_threshold is not None else 5.0
        stop_loss = stop_loss_pct if stop_loss_pct is not None else 8.0

        adjusted = []
        for rec in base_recs:
            base_score = self._safe_float(rec.get("score"), 0.0)
            strategy = str(rec.get("strategy") or "")
            score = base_score
            reasons: list[str] = []

            if market_shock_pct < 0:
                penalty = min(abs(market_shock_pct) * 0.04, 0.2)
                score -= penalty
                reasons.append(f"market shock penalty {round(penalty * 100)}bp")
            elif market_shock_pct > 0 and strategy in {"momentum", "trend_following", "breakout"}:
                boost = min(market_shock_pct * 0.03, 0.15)
                score += boost
                reasons.append(f"trend shock boost {round(boost * 100)}bp")

            if volatility > threshold and strategy in {"trend_following", "momentum", "breakout"}:
                score -= 0.08
                reasons.append("above volatility threshold")
            if volatility > threshold and strategy in {"grid_trading", "mean_reversion"}:
                score += 0.05
                reasons.append("volatility favors range strategies")
            if stop_loss < 5 and strategy in {"grid_trading", "mean_reversion"}:
                score -= 0.05
                reasons.append("tight stop loss reduces range strategy fit")

            adjusted.append(
                {
                    "strategy": strategy,
                    "base_score": round(base_score, 4),
                    "adjusted_score": round(max(0.0, min(score, 1.0)), 4),
                    "delta": round(max(0.0, min(score, 1.0)) - base_score, 4),
                    "reasons": reasons or ["unchanged"],
                }
            )

        adjusted.sort(key=lambda item: item["adjusted_score"], reverse=True)
        return {
            "inputs": {
                "market_shock_pct": market_shock_pct,
                "volatility_threshold": threshold,
                "stop_loss_pct": stop_loss,
            },
            "base": {
                "volatility": volatility,
                "trend": copilot_result.get("trend"),
                "regime": copilot_result.get("regime"),
            },
            "strategies": adjusted,
            "top_pick": adjusted[0] if adjusted else None,
        }

    @staticmethod
    def _safe_float(value: Any, default: float) -> float:
        try:
            if value in (None, ""):
                return default
            return float(value)
        except (TypeError, ValueError):
            return default


__all__ = ["SensitivitySandboxService"]
