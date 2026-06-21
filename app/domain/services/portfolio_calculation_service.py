from __future__ import annotations
"""Portfolio Calculation Domain Service.

Pure domain logic for portfolio valuation and risk metrics.
"""


from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class PositionSide(str, Enum):
    """Position side."""
    LONG = "long"
    SHORT = "short"


@dataclass(frozen=True)
class Position:
    """A portfolio position."""
    stock_code: str
    quantity: float
    avg_price: float
    side: PositionSide = PositionSide.LONG
    
    @property
    def market_value(self) -> float:
        return self.quantity * self.avg_price
    
    @property
    def cost(self) -> float:
        return self.quantity * self.avg_price


@dataclass(frozen=True)
class PositionSnapshot:
    """Position at a point in time."""
    stock_code: str
    quantity: float
    avg_price: float
    current_price: float
    side: PositionSide = PositionSide.LONG
    
    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price
    
    @property
    def cost_basis(self) -> float:
        return self.quantity * self.avg_price
    
    @property
    def pnl(self) -> float:
        if self.side == PositionSide.LONG:
            return (self.current_price - self.avg_price) * self.quantity
        return (self.avg_price - self.current_price) * self.quantity
    
    @property
    def pnl_pct(self) -> float:
        if self.cost_basis == 0:
            return 0.0
        return (self.pnl / self.cost_basis) * 100


@dataclass(frozen=True)
class PortfolioSnapshot:
    """Portfolio snapshot at a point in time."""
    positions: list[PositionSnapshot]
    cash: float
    captured_at: datetime
    
    @property
    def total_market_value(self) -> float:
        return sum(p.market_value for p in self.positions)
    
    @property
    def total_cost_basis(self) -> float:
        return sum(p.cost_basis for p in self.positions)
    
    @property
    def total_pnl(self) -> float:
        return sum(p.pnl for p in self.positions)
    
    @property
    def total_assets(self) -> float:
        return self.total_market_value + self.cash
    
    @property
    def pnl_pct(self) -> float:
        if self.total_cost_basis == 0:
            return 0.0
        return (self.total_pnl / self.total_cost_basis) * 100


@dataclass(frozen=True)
class RiskMetrics:
    """Portfolio risk metrics."""
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    beta: float = 1.0
    var_95: float = 0.0
    
    @property
    def risk_score(self) -> str:
        if self.volatility < 0.1:
            return "low"
        elif self.volatility < 0.2:
            return "moderate"
        return "high"


class PortfolioCalculationService:
    """Domain service for portfolio calculations."""
    
    def calculate_position_pnl(
        self,
        quantity: float,
        avg_price: float,
        current_price: float,
        side: PositionSide = PositionSide.LONG
    ) -> float:
        """Calculate position P&L."""
        if side == PositionSide.LONG:
            return (current_price - avg_price) * quantity
        return (avg_price - current_price) * quantity
    
    def calculate_position_pnl_pct(
        self,
        avg_price: float,
        current_price: float,
        side: PositionSide = PositionSide.LONG
    ) -> float:
        """Calculate position P&L percentage."""
        if avg_price == 0:
            return 0.0
        if side == PositionSide.LONG:
            return ((current_price - avg_price) / avg_price) * 100
        return ((avg_price - current_price) / avg_price) * 100
    
    def calculate_portfolio_value(
        self,
        positions: list[Position],
        prices: dict[str, float],
        cash: float
    ) -> float:
        """Calculate total portfolio value."""
        total = cash
        for pos in positions:
            current_price = prices.get(pos.stock_code, pos.avg_price)
            total += pos.quantity * current_price
        return total
    
    def calculate_allocation(
        self,
        positions: list[Position],
        prices: dict[str, float],
        cash: float
    ) -> dict[str, float]:
        """Calculate position allocations as percentages."""
        total_value = self.calculate_portfolio_value(positions, prices, cash)
        if total_value == 0:
            return {}
        
        allocations = {}
        for pos in positions:
            current_price = prices.get(pos.stock_code, pos.avg_price)
            value = pos.quantity * current_price
            allocations[pos.stock_code] = (value / total_value) * 100
        
        allocations["cash"] = (cash / total_value) * 100
        return allocations
    
    def calculate_risk_metrics(
        self,
        returns: list[float],
        risk_free_rate: float = 0.03
    ) -> RiskMetrics:
        """Calculate risk metrics from returns."""
        if not returns or len(returns) < 2:
            return RiskMetrics()
        
        import statistics
        mean_return = statistics.mean(returns)
        volatility = statistics.stdev(returns) if len(returns) > 1 else 0.0
        
        excess_return = mean_return - risk_free_rate
        sharpe = (excess_return / volatility) if volatility > 0 else 0.0
        
        running_max = returns[0]
        max_drawdown = 0.0
        for r in returns:
            running_max = max(running_max, r)
            drawdown = running_max - r
            max_drawdown = max(max_drawdown, drawdown)
        
        return RiskMetrics(
            volatility=volatility,
            sharpe_ratio=sharpe,
            max_drawdown=max_drawdown,
            beta=1.0,
            var_95=0.0,
        )
    
    def calculate_position_sizing(
        self,
        total_capital: float,
        risk_per_trade: float,
        entry_price: float,
        stop_loss_pct: float
    ) -> float:
        """Calculate position size based on risk."""
        if stop_loss_pct == 0:
            return 0.0
        
        risk_amount = total_capital * risk_per_trade
        position_size = risk_amount / (entry_price * stop_loss_pct / 100)
        return position_size
    
    def RebalanceTarget(
        self,
        current_allocations: dict[str, float],
        target_allocations: dict[str, float],
        threshold: float = 5.0
    ) -> dict[str, float]:
        """Calculate rebalancing needed."""
        rebalances = {}
        
        for asset, target in target_allocations.items():
            current = current_allocations.get(asset, 0)
            diff = target - current
            
            if abs(diff) > threshold:
                rebalances[asset] = diff
        
        return rebalances


class PortfolioValuator:
    """Service for valuing portfolio positions."""
    
    def __init__(self):
        self._service = PortfolioCalculationService()
    
    def create_snapshot(
        self,
        positions: list[dict],
        prices: dict[str, float],
        cash: float
    ) -> PortfolioSnapshot:
        """Create portfolio snapshot."""
        snapshots = []
        
        for pos in positions:
            stock_code = pos.get("stock_code", "")
            quantity = pos.get("quantity", 0)
            avg_price = pos.get("avg_price", 0)
            current_price = prices.get(stock_code, avg_price)
            side = PositionSide(pos.get("side", "long"))
            
            snapshots.append(PositionSnapshot(
                stock_code=stock_code,
                quantity=quantity,
                avg_price=avg_price,
                current_price=current_price,
                side=side,
            ))
        
        return PortfolioSnapshot(
            positions=snapshots,
            cash=cash,
            captured_at=datetime.now(),
        )
    
    def get_top_performers(
        self,
        snapshot: PortfolioSnapshot,
        limit: int = 5
    ) -> list[PositionSnapshot]:
        """Get top performing positions."""
        return sorted(
            snapshot.positions,
            key=lambda p: p.pnl_pct,
            reverse=True
        )[:limit]
    
    def get_bottom_performers(
        self,
        snapshot: PortfolioSnapshot,
        limit: int = 5
    ) -> list[PositionSnapshot]:
        """Get worst performing positions."""
        return sorted(
            snapshot.positions,
            key=lambda p: p.pnl_pct
        )[:limit]


__all__ = [
    "PositionSide",
    "Position",
    "PositionSnapshot",
    "PortfolioSnapshot",
    "RiskMetrics",
    "PortfolioCalculationService",
    "PortfolioValuator",
]