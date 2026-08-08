"""Hard Risk Guard rules independent of AI (SRS REQ-SRS-01)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RiskAction = Literal["allow", "flatten_all", "suspend_execution"]


@dataclass(frozen=True, slots=True)
class RiskGuardDecision:
    action: RiskAction
    block_new_orders: bool
    reason: str


def evaluate_account_risk(
    *,
    equity: float,
    day_start_equity: float,
    consecutive_stop_outs: int,
    max_daily_drawdown_pct: float = 0.05,
    max_consecutive_stop_outs: int = 3,
) -> RiskGuardDecision:
    """Evaluate account risk before allowing new orders.

    Priority: invalid state → daily drawdown flatten → consecutive stop-outs suspend → allow.
    """
    if day_start_equity <= 0:
        return RiskGuardDecision("suspend_execution", True, "invalid_day_start_equity")
    drawdown = (day_start_equity - equity) / day_start_equity
    if drawdown >= max_daily_drawdown_pct:
        return RiskGuardDecision(
            "flatten_all",
            True,
            f"daily_drawdown={drawdown:.4f}>={max_daily_drawdown_pct}",
        )
    if consecutive_stop_outs >= max_consecutive_stop_outs:
        return RiskGuardDecision(
            "suspend_execution",
            True,
            f"consecutive_stop_outs={consecutive_stop_outs}",
        )
    return RiskGuardDecision("allow", False, "ok")
