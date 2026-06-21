from __future__ import annotations
"""Portfolio Aggregate Root.

Aggregate root for portfolio with positions and orders.
"""


from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from app.domain.base import AggregateRoot
from app.domain.services.portfolio_calculation_service import (
    Position,
    PositionSide,
    PositionSnapshot,
    PortfolioSnapshot,
)
from app.domain.services.trading_policy_service import TradingPolicy, TradingPolicyService


class PortfolioAggregateError(Exception):
    """Portfolio aggregate error."""
    pass


class PositionLimitExceededError(PortfolioAggregateError):
    """Position limit exceeded."""
    pass


class InsufficientCapitalError(PortfolioAggregateError):
    """Insufficient capital."""
    pass


class InvalidPositionError(PortfolioAggregateError):
    """Invalid position."""
    pass


@dataclass
class PositionEntity:
    """Position entity for aggregate."""
    stock_code: str
    quantity: float
    avg_price: float
    side: PositionSide = PositionSide.LONG
    
    @property
    def market_value(self) -> float:
        return self.quantity * self.avg_price


@dataclass
class PortfolioAggregate(AggregateRoot):
    """Portfolio aggregate root.
    
    Encapsulates:
    - Portfolio positions
    - Cash balance
    - Orders
    - Invariants: positions <= 100%, valid positions
    """
    
    _positions: list[PositionEntity] = field(default_factory=list)
    _cash: float = 0.0
    _policy_service: TradingPolicyService = field(default_factory=TradingPolicyService)
    
    @staticmethod
    def create(
        initial_cash: float = 1000000.0,
        policy: Optional[TradingPolicy] = None
    ) -> "PortfolioAggregate":
        """Create a new portfolio aggregate."""
        if initial_cash < 0:
            raise InsufficientCapitalError(f"Invalid initial cash: {initial_cash}")
        
        portfolio = PortfolioAggregate(_cash=initial_cash)
        if policy:
            portfolio._policy_service = TradingPolicyService(policy)
        return portfolio
    
    @property
    def cash(self) -> float:
        return self._cash
    
    @property
    def position_count(self) -> int:
        return len(self._positions)
    
    @property
    def total_market_value(self) -> float:
        return sum(p.market_value for p in self._positions)
    
    @property
    def total_assets(self) -> float:
        return self._cash + self.total_market_value
    
    @property
    def position_allocation(self) -> float:
        total = self.total_assets
        if total == 0:
            return 0.0
        return self.total_market_value / total
    
    def has_position(self, stock_code: str) -> bool:
        """Check if position exists."""
        return any(p.stock_code == stock_code for p in self._positions)
    
    def get_position(self, stock_code: str) -> Optional[PositionEntity]:
        """Get position by stock code."""
        for p in self._positions:
            if p.stock_code == stock_code:
                return p
        return None
    
    def add_position(
        self,
        stock_code: str,
        quantity: float,
        price: float,
        side: PositionSide = PositionSide.LONG
    ) -> None:
        """Add or update a position."""
        if quantity <= 0:
            raise InvalidPositionError(f"Invalid quantity: {quantity}")
        
        cost = quantity * price
        
        if cost > self._cash:
            raise InsufficientCapitalError(
                f"Insufficient capital: {cost} > {self._cash}"
            )
        
        existing = self.get_position(stock_code)
        
        if existing:
            new_quantity = existing.quantity + quantity
            new_avg = (
                (existing.quantity * existing.avg_price + cost) / new_quantity
            )
            existing.quantity = new_quantity
            existing.avg_price = new_avg
        else:
            if self.position_allocation >= self._policy_service.get_policy().max_position_size:
                raise PositionLimitExceededError("Position limit exceeded")
            
            self._positions.append(PositionEntity(
                stock_code=stock_code,
                quantity=quantity,
                avg_price=price,
                side=side,
            ))
        
        self._cash -= cost
        self.touch()
    
    def reduce_position(
        self,
        stock_code: str,
        quantity: float,
        current_price: float
    ) -> float:
        """Reduce a position, return proceeds."""
        existing = self.get_position(stock_code)
        
        if not existing:
            raise InvalidPositionError(f"No position for {stock_code}")
        
        if quantity >= existing.quantity:
            proceeds = existing.quantity * current_price
            self._positions = [p for p in self._positions if p.stock_code != stock_code]
        else:
            proceeds = quantity * current_price
            existing.quantity -= quantity
        
        self._cash += proceeds
        self.touch()
        
        return proceeds
    
    def close_position(
        self,
        stock_code: str,
        current_price: float
    ) -> float:
        """Close entire position."""
        return self.reduce_position(stock_code, float('inf'), current_price)
    
    def rebalance(
        self,
        target_allocations: dict[str, float],
        current_prices: dict[str, float]
    ) -> dict[str, float]:
        """Calculate rebalancing needed."""
        rebalances = {}
        
        for stock_code, target_pct in target_allocations.items():
            current_value = 0.0
            for pos in self._positions:
                if pos.stock_code == stock_code:
                    current_value = pos.quantity * current_prices.get(stock_code, pos.avg_price)
                    break
            
            current_pct = (current_value / self.total_assets * 100) if self.total_assets > 0 else 0
            diff = target_pct - current_pct
            
            if abs(diff) > 1.0:
                rebalances[stock_code] = diff
        
        return rebalances
    
    def apply_rebalance(
        self,
        rebalances: dict[str, float],
        current_prices: dict[str, float]
    ) -> None:
        """Apply rebalancing trades."""
        for stock_code, diff_pct in rebalances.items():
            current_price = current_prices.get(stock_code)
            if not current_price:
                continue
            
            trade_value = (diff_pct / 100) * self.total_assets
            
            if trade_value > 0:
                quantity = trade_value / current_price
                self.add_position(stock_code, quantity, current_price)
            elif trade_value < 0:
                quantity = abs(trade_value) / current_price
                self.reduce_position(stock_code, quantity, current_price)
    
    def create_snapshot(
        self,
        current_prices: dict[str, float]
    ) -> PortfolioSnapshot:
        """Create portfolio snapshot."""
        snapshots = []
        
        for pos in self._positions:
            current_price = current_prices.get(pos.stock_code, pos.avg_price)
            snapshots.append(PositionSnapshot(
                stock_code=pos.stock_code,
                quantity=pos.quantity,
                avg_price=pos.avg_price,
                current_price=current_price,
                side=pos.side,
            ))
        
        return PortfolioSnapshot(
            positions=snapshots,
            cash=self._cash,
            captured_at=datetime.now(),
        )
    
    def get_top_performers(
        self,
        current_prices: dict[str, float],
        limit: int = 5
    ) -> list[PositionSnapshot]:
        """Get top performing positions."""
        snapshot = self.create_snapshot(current_prices)
        
        return sorted(
            snapshot.positions,
            key=lambda p: p.pnl_pct,
            reverse=True
        )[:limit]
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": str(self.id),
            "cash": self._cash,
            "total_market_value": self.total_market_value,
            "total_assets": self.total_assets,
            "position_allocation": self.position_allocation,
            "position_count": self.position_count,
            "positions": [
                {"stock_code": p.stock_code, "quantity": p.quantity, "avg_price": p.avg_price}
                for p in self._positions
            ],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


__all__ = [
    "PortfolioAggregate",
    "PortfolioAggregateError",
    "PositionLimitExceededError",
    "InsufficientCapitalError",
    "InvalidPositionError",
    "PositionEntity",
]