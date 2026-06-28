from __future__ import annotations

"""Risk management ports - pre-flight order checks."""


from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RiskCheckResult:
    """Result of a pre-flight risk check."""

    allowed: bool
    reason: str
    blocked_rules: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def pass_() -> RiskCheckResult:
        return RiskCheckResult(allowed=True, reason="PASS")

    @staticmethod
    def fail(reason: str, blocked_rules: list[str] | None = None, details: dict[str, Any] | None = None) -> RiskCheckResult:
        return RiskCheckResult(
            allowed=False,
            reason=reason,
            blocked_rules=blocked_rules or [],
            details=details or {},
        )


@dataclass(frozen=True)
class OrderContext:
    """Order context for risk checks."""

    symbol: str
    side: str
    quantity: int
    price: float
    account_id: str
    total_equity: float
    cash_available: float
    current_positions: dict[str, int]
    daily_pnl: float
    market: str = "CN"


class RiskPreFlightPort(ABC):
    """Port for pre-flight risk checks before order submission."""

    @abstractmethod
    def check_order(self, order: OrderContext) -> RiskCheckResult:
        """Check if order passes all risk rules."""
        raise NotImplementedError

    @abstractmethod
    def check_portfolio_risk(self, orders: list[OrderContext]) -> RiskCheckResult:
        """Check portfolio-level risk across multiple orders."""
        raise NotImplementedError


@dataclass(frozen=True)
class KellyPositionSizing:
    """Kelly Criterion position sizing."""

    kelly_fraction: float
    recommended_shares: int
    max_shares: int
    risk_per_trade: float
    edge: float
    payoff_ratio: float


class PositionSizingPort(ABC):
    """Port for position sizing algorithms."""

    @abstractmethod
    def compute_kelly(self, win_rate: float, payoff_ratio: float, *, fraction: float = 0.5) -> KellyPositionSizing:
        """Compute Kelly Criterion based position sizing."""
        raise NotImplementedError

    @abstractmethod
    def compute_vol_target(self, equity: float, volatility: float, target_vol: float = 0.15) -> float:
        """Compute volatility-targeted position size."""
        raise NotImplementedError
