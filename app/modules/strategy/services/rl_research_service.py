"""Application wrapper for offline RL research (no live routing)."""

from __future__ import annotations

from typing import Any

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime, get_runtime_bool, get_runtime_int
from app.domain.alpha.rl_research import (
    RlLiveForbiddenError,
    assert_rl_research_only,
    infer_action,
    load_latest_policy,
    rl_live_enabled,
    run_rl_research,
)

logger = get_logger(__name__)


def rl_research_status(*, spec_name: str | None = None) -> dict[str, Any]:
    spec = (spec_name or get_runtime("RL_RESEARCH_SPEC", "cn_day_v0") or "cn_day_v0").strip()
    policy = load_latest_policy(spec_name=spec)
    return {
        "live_enabled": False,
        "rl_live_flag": rl_live_enabled(),
        "enroll_tournament": get_runtime_bool("RL_ENROLL_TOURNAMENT", False),
        "spec_name": spec,
        "has_policy": policy is not None,
        "policy": policy,
        "message": "RL research sidecar only — never submits broker orders",
    }


def run_rl_research_tick(
    *,
    bars: list[dict[str, Any]] | None = None,
    spec_name: str | None = None,
    symbol: str | None = None,
    episodes: int | None = None,
    prefer_live_bars: bool = True,
) -> dict[str, Any]:
    from app.modules.data.services.feature_pipeline_bars import load_cn_day_bars, synthetic_day_bars

    spec = (spec_name or get_runtime("RL_RESEARCH_SPEC", "cn_day_v0") or "cn_day_v0").strip()
    sym = (symbol or get_runtime("FEATURE_PIPELINE_SYMBOL", "600519") or "600519").strip()
    n_ep = int(episodes if episodes is not None else get_runtime_int("RL_RESEARCH_EPISODES", 8))
    synthetic = False
    source = "explicit"
    if bars is None and prefer_live_bars:
        loaded = load_cn_day_bars(symbol=sym)
        if loaded.get("ok") and loaded.get("bars"):
            bars = list(loaded["bars"])
            source = str(loaded.get("source") or "multi_source")
        else:
            logger.info("rl_research live bars unavailable (%s); synthetic", loaded.get("error"))
            source = "synthetic"
            synthetic = True
    if not bars:
        bars = synthetic_day_bars(periods=180)
        synthetic = True
        source = "synthetic"
    result = run_rl_research(
        bars,
        spec_name=spec,
        symbol=sym,
        episodes=max(1, min(n_ep, 64)),
        synthetic_bars=synthetic,
    )
    payload = result.as_dict()
    payload.update({"symbol": sym, "bars_source": source, "live_enabled": False})
    if get_runtime_bool("RL_ENROLL_TOURNAMENT", False) and not synthetic:
        try:
            from app.modules.strategy.services.tournament.enrollment import enroll_tournament_candidate

            verdict = enroll_tournament_candidate(
                strategy_id=f"rl_q_{spec}_{sym}",
                sharpe=float(result.valid_sharpe),
                max_drawdown=float(result.valid_max_drawdown),
                bias_passed=True,
                total_return=float(result.valid_return),
                metadata={"engine": "tabular_q_v0", "research_only": True},
            )
            payload["tournament"] = {
                "accepted": verdict.accepted,
                "reason": verdict.reason,
            }
        except Exception as exc:
            logger.warning("rl tournament enroll skipped: %s", exc, exc_info=True)
            payload["tournament"] = {"accepted": False, "error": str(exc)}
    logger.info(
        "rl_research_tick ok=%s n=%s valid_ret=%.4f synthetic=%s",
        payload.get("ok"),
        payload.get("n_rows"),
        float(payload.get("valid_return") or 0),
        synthetic,
    )
    return payload


def infer_rl_action(
    *,
    ret_1: float,
    ma_bias_5: float,
    spec_name: str | None = None,
) -> dict[str, Any]:
    spec = (spec_name or get_runtime("RL_RESEARCH_SPEC", "cn_day_v0") or "cn_day_v0").strip()
    return infer_action(ret_1=float(ret_1), ma_bias_5=float(ma_bias_5), spec_name=spec)


def refuse_live_execution() -> None:
    """Public hook for any future live adapter — always raises."""
    assert_rl_research_only()


__all__ = [
    "RlLiveForbiddenError",
    "infer_rl_action",
    "refuse_live_execution",
    "rl_research_status",
    "run_rl_research_tick",
]
