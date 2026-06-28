from __future__ import annotations
"""Rich domain models with business logic encapsulated."""


from dataclasses import dataclass, field
from datetime import datetime


from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Position:
    """Position entity with risk management and P&L calculation."""

    symbol: str
    quantity: float = 0.0
    avg_cost: float = 0.0
    current_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0

    # Risk parameters
    stop_loss: float = 0.0
    take_profit: float = 0.0
    max_position_size: float = 10.0  # percentage of portfolio

    # Metadata
    open_date: datetime | None = None
    last_updated: datetime = field(default_factory=datetime.now)

    def update_price(self, new_price: float) -> None:
        """Update current price and recalculate P&L."""
        self.current_price = new_price
        self.market_value = self.quantity * new_price
        self.unrealized_pnl = (new_price - self.avg_cost) * self.quantity
        self.last_updated = datetime.now()

    def update_quantity(self, quantity: float, price: float) -> None:
        """Update position with new trade."""
        if self.quantity == 0:
            self.avg_cost = price
            self.open_date = datetime.now()
        else:
            total_cost = self.avg_cost * self.quantity + price * quantity
            self.quantity += quantity
            self.avg_cost = total_cost / self.quantity if self.quantity > 0 else 0

        self.update_price(price)

    @property
    def pnl_percentage(self) -> float:
        """Calculate P&L as percentage."""
        if self.avg_cost == 0 or self.quantity == 0:
            return 0.0
        return ((self.current_price - self.avg_cost) / self.avg_cost) * 100

    @property
    def is_profitable(self) -> bool:
        """Check if position is in profit."""
        return self.unrealized_pnl > 0

    @property
    def is_stop_loss_triggered(self) -> bool:
        """Check if stop loss is triggered."""
        if self.stop_loss == 0:
            return False
        return self.current_price <= self.stop_loss

    @property
    def is_take_profit_triggered(self) -> bool:
        """Check if take profit is triggered."""
        if self.take_profit == 0:
            return False
        return self.current_price >= self.take_profit

    def calculate_risk(self, portfolio_value: float) -> dict:
        """Calculate position risk metrics."""
        position_pct = (self.market_value / portfolio_value * 100) if portfolio_value > 0 else 0

        return {
            "position_pct": position_pct,
            "exceeds_limit": position_pct > self.max_position_size,
            "unrealized_pnl": self.unrealized_pnl,
            "pnl_percentage": self.pnl_percentage,
            "stop_loss_distance": ((self.avg_cost - self.stop_loss) / self.avg_cost * 100) if self.stop_loss > 0 else None,
            "risk_level": "high" if position_pct > 10 else ("medium" if position_pct > 5 else "low")
        }

    def should_close(self) -> tuple[bool, str]:
        """Determine if position should be closed."""
        if self.is_stop_loss_triggered:
            return True, "stop_loss"
        if self.is_take_profit_triggered:
            return True, "take_profit"
        return False, ""


@dataclass
class Portfolio:
    """Portfolio entity with diversification and rebalancing logic."""

    user_id: str
    cash: float = 0.0
    positions: dict[str, Position] = field(default_factory=dict)

    @property
    def total_value(self) -> float:
        """Calculate total portfolio value."""
        return self.cash + sum(p.market_value for p in self.positions.values())

    @property
    def total_pnl(self) -> float:
        """Calculate total unrealized P&L."""
        return sum(p.unrealized_pnl for p in self.positions.values())

    def get_position(self, symbol: str) -> Position | None:
        """Get position by symbol."""
        return self.positions.get(symbol)

    def add_position(self, symbol: str, quantity: float, price: float) -> None:
        """Add or update a position."""
        if symbol in self.positions:
            self.positions[symbol].update_quantity(quantity, price)
        else:
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                avg_cost=price
            )
            self.positions[symbol].update_price(price)

    def remove_position(self, symbol: str, quantity: float, price: float) -> None:
        """Remove shares from position."""
        if symbol not in self.positions:
            return

        pos = self.positions[symbol]
        if quantity >= pos.quantity:
            realized = (price - pos.avg_cost) * pos.quantity
            pos.realized_pnl += realized
            del self.positions[symbol]
        else:
            pos.update_quantity(-quantity, price)

    def can_buy(self, symbol: str, quantity: float, price: float) -> tuple[bool, str]:
        """Check if buy order is valid."""
        required = quantity * price

        if required > self.cash:
            return False, "insufficient_cash"

        if symbol in self.positions:
            pos = self.positions[symbol]
            new_value = pos.market_value + required
            new_pct = new_value / self.total_value * 100 if self.total_value > 0 else 0

            if new_pct > pos.max_position_size:
                return False, "exceeds_position_limit"

        return True, ""

    def get_diversification_score(self) -> float:
        """Calculate portfolio diversification score (0-100)."""
        if not self.positions:
            return 0.0

        positions_count = len(self.positions)

        if positions_count >= 10:
            return 100.0

        if positions_count >= 5:
            return 70.0

        if positions_count >= 3:
            return 40.0

        return 10.0

    def get_risk_summary(self) -> dict:
        """Get overall portfolio risk summary."""
        total_value = self.total_value
        if total_value == 0:
            return {"risk_level": "none", "concentration": 0}

        largest_position = max((p.market_value for p in self.positions.values()), default=0)
        concentration = (largest_position / total_value * 100) if total_value > 0 else 0

        return {
            "total_value": total_value,
            "cash": self.cash,
            "positions_count": len(self.positions),
            "total_pnl": self.total_pnl,
            "concentration": concentration,
            "diversification": self.get_diversification_score(),
            "risk_level": "high" if concentration > 30 else ("medium" if concentration > 15 else "low")
        }


@dataclass
class RiskControl:
    """Risk control entity with validation logic."""

    max_position_pct: float = 10.0
    max_single_loss_pct: float = 5.0
    max_daily_loss_pct: float = 10.0
    require_stop_loss: bool = True

    def validate_trade(
        self,
        portfolio: Portfolio,
        symbol: str,
        quantity: float,
        price: float
    ) -> tuple[bool, str]:
        """Validate if trade meets risk requirements."""
        required = quantity * price

        # Check cash
        if required > portfolio.cash:
            return False, "insufficient_cash"

        # Check position limit
        new_position_value = 0
        if symbol in portfolio.positions:
            new_position_value = portfolio.positions[symbol].market_value
        new_position_value += required

        new_pct = new_position_value / portfolio.total_value * 100 if portfolio.total_value > 0 else 0

        if new_pct > self.max_position_pct:
            return False, f"exceeds_position_limit_{new_pct:.1f}%"

        return True, ""

    def check_daily_loss(self, daily_pnl: float, portfolio_value: float) -> bool:
        """Check if daily loss exceeds limit."""
        if portfolio_value == 0:
            return False

        loss_pct = abs(daily_pnl) / portfolio_value * 100

        if daily_pnl < 0 and loss_pct > self.max_daily_loss_pct:
            logger.warning(f"Daily loss {loss_pct:.2f}% exceeds limit {self.max_daily_loss_pct}%")
            return True

        return False


__all__ = ["Position", "Portfolio", "RiskControl"]
