from __future__ import annotations
"""Trading Policy Domain Service.

Pure domain logic for trading rules enforcement.
"""


from dataclasses import dataclass
from datetime import datetime, time
from enum import Enum
from typing import Any, Optional


class PolicyViolation(str, Enum):
    """Policy violation types."""
    POSITION_LIMIT_EXCEEDED = "position_limit_exceeded"
    SINGLE_TRADE_LIMIT_EXCEEDED = "single_trade_limit_exceeded"
    DAILY_LOSS_LIMIT_EXCEEDED = "daily_loss_limit_exceeded"
    TRADING_HALTED = "trading_halted"
    MARKET_CLOSED = "market_closed"
    CIRCUIT_BREAKER_TRIGGERED = "circuit_breaker_triggered"
    RESTRICTED_STOCK = "restricted_stock"
    INSUFFICIENT_CAPITAL = "insufficient_capital"


class TradingAction(str, Enum):
    """Trading actions."""
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"
    REVIEW = "review"


@dataclass(frozen=True)
class TradingPolicy:
    """Trading policy configuration."""
    max_position_size: float = 0.1  # 10% of portfolio
    max_single_trade: float = 0.05  # 5% of portfolio
    max_daily_loss: float = 0.02  # 2% of portfolio
    max_sectors_concentration: float = 0.30  # 30% in one sector
    circuit_breaker_loss: float = 0.05  # 5% daily loss triggers halt
    trading_start_time: time = time(9, 30)
    trading_end_time: time = time(15, 0)
    restricted_stocks: tuple[str, ...] = ()


@dataclass(frozen=True)
class PolicyResult:
    """Result of policy check."""
    action: TradingAction
    violations: list[PolicyViolation]
    message: str
    
    @property
    def is_allowed(self) -> bool:
        return self.action == TradingAction.ALLOW
    
    @property
    def is_blocked(self) -> bool:
        return self.action == TradingAction.BLOCK
    
    @property
    def needs_review(self) -> bool:
        return self.action == TradingAction.REVIEW


class TradingPolicyService:
    """Domain service for trading policy enforcement."""
    
    def __init__(self, policy: Optional[TradingPolicy] = None):
        self._policy = policy or TradingPolicy()
        self._daily_loss = 0.0
        self._daily_pnl = 0.0
    
    def check_buy(
        self,
        stock_code: str,
        trade_value: float,
        portfolio_value: float,
        current_positions: dict[str, float],
        sector_allocation: dict[str, float]
    ) -> PolicyResult:
        """Check if buy order is allowed."""
        violations = []
        
        if stock_code in self._policy.restricted_stocks:
            violations.append(PolicyViolation.RESTRICTED_STOCK)
            return PolicyResult(
                action=TradingAction.BLOCK,
                violations=violations,
                message=f"Stock {stock_code} is restricted"
            )
        
        single_trade_pct = trade_value / portfolio_value if portfolio_value > 0 else 0
        if single_trade_pct > self._policy.max_single_trade:
            violations.append(PolicyViolation.SINGLE_TRADE_LIMIT_EXCEEDED)
        
        position_pct = sum(current_positions.values()) / portfolio_value if portfolio_value > 0 else 0
        if position_pct + single_trade_pct > self._policy.max_position_size:
            violations.append(PolicyViolation.POSITION_LIMIT_EXCEEDED)
        
        for sector, alloc in sector_allocation.items():
            if alloc > self._policy.max_sectors_concentration:
                violations.append(PolicyViolation.POSITION_LIMIT_EXCEEDED)
        
        market_status = self._check_market_hours()
        if market_status != TradingAction.ALLOW:
            violations.append(PolicyViolation.MARKET_CLOSED)
            return PolicyResult(
                action=market_status,
                violations=violations,
                message="Market is closed"
            )
        
        if self._daily_pnl < -self._policy.circuit_breaker_loss * portfolio_value:
            violations.append(PolicyViolation.CIRCUIT_BREAKER_TRIGGERED)
            return PolicyResult(
                action=TradingAction.BLOCK,
                violations=violations,
                message="Circuit breaker triggered - daily loss limit"
            )
        
        if violations:
            return PolicyResult(
                action=TradingAction.REVIEW,
                violations=violations,
                message=f"Policy warnings: {[v.value for v in violations]}"
            )
        
        return PolicyResult(
            action=TradingAction.ALLOW,
            violations=[],
            message="Buy allowed"
        )
    
    def check_sell(
        self,
        stock_code: str,
        trade_value: float,
        portfolio_value: float
    ) -> PolicyResult:
        """Check if sell order is allowed."""
        violations = []
        
        market_status = self._check_market_hours()
        if market_status != TradingAction.ALLOW:
            violations.append(PolicyViolation.MARKET_CLOSED)
            return PolicyResult(
                action=market_status,
                violations=violations,
                message="Market is closed"
            )
        
        return PolicyResult(
            action=TradingAction.ALLOW,
            violations=[],
            message="Sell allowed"
        )
    
    def _check_market_hours(self) -> TradingAction:
        """Check if market is open."""
        now = datetime.now().time()
        
        if now < self._policy.trading_start_time or now > self._policy.trading_end_time:
            return TradingAction.WARN
        
        return TradingAction.ALLOW
    
    def record_trade(
        self,
        trade_value: float,
        is_buy: bool,
        pnl: float = 0.0
    ) -> None:
        """Record trade for daily tracking."""
        if not is_buy:
            self._daily_pnl += pnl
        
        self._daily_loss += trade_value if not is_buy else 0
    
    def reset_daily(self) -> None:
        """Reset daily counters."""
        self._daily_loss = 0.0
        self._daily_pnl = 0.0
    
    def get_daily_loss_pct(self, portfolio_value: float) -> float:
        """Get daily loss percentage."""
        if portfolio_value == 0:
            return 0.0
        return self._daily_loss / portfolio_value
    
    def circuit_breaker_triggered(self, portfolio_value: float) -> bool:
        """Check if circuit breaker is triggered."""
        return self._daily_pnl < -self._policy.circuit_breaker_loss * portfolio_value
    
    def get_policy(self) -> TradingPolicy:
        """Get current policy."""
        return self._policy


class TradingRuleEngine:
    """Rule engine for trading policies."""
    
    def __init__(self):
        self._services: list[TradingPolicyService] = []
    
    def add_policy(self, policy: TradingPolicy) -> "TradingRuleEngine":
        """Add a policy service."""
        self._services.append(TradingPolicyService(policy))
        return self
    
    def check_buy_all(
        self,
        stock_code: str,
        trade_value: float,
        portfolio_value: float,
        current_positions: dict[str, float],
        sector_allocation: dict[str, float]
    ) -> PolicyResult:
        """Check against all policies."""
        for service in self._services:
            result = service.check_buy(
                stock_code, trade_value, portfolio_value,
                current_positions, sector_allocation
            )
            if result.is_blocked:
                return result
        
        return PolicyResult(
            action=TradingAction.ALLOW,
            violations=[],
            message="All policies passed"
        )
    
    def get_strictest_policy(self, policies: list[TradingPolicy]) -> TradingPolicy:
        """Get the strictest policy from list."""
        if not policies:
            return TradingPolicy()
        
        return TradingPolicy(
            max_position_size=min(p.max_position_size for p in policies),
            max_single_trade=min(p.max_single_trade for p in policies),
            max_daily_loss=min(p.max_daily_loss for p in policies),
            max_sectors_concentration=min(p.max_sectors_concentration for p in policies),
            circuit_breaker_loss=min(p.circuit_breaker_loss for p in policies),
        )


__all__ = [
    "PolicyViolation",
    "TradingAction",
    "TradingPolicy",
    "PolicyResult",
    "TradingPolicyService",
    "TradingRuleEngine",
]