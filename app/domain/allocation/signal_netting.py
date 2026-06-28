from __future__ import annotations

"""Signal Netting & Global Risk Control.

Implements from strategy_plan2.md:
- Signal netting: Buy 100 + Sell 50 = Net Buy 50
- Hierarchical risk control: strategy/manager/platform levels
- Platform-wide position limits

Usage:
    netting = SignalNetting()
    net_positions = nettingNet_orders(signals)
    risk.check_manager_risk("manager_001", positions)
"""


from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


class PositionDirection(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class RiskLevel(Enum):
    STRATEGY = "strategy"
    MANAGER = "manager"
    PLATFORM = "platform"


@dataclass
class Position:
    """Single position."""
    strategy_name: str
    manager_id: str
    symbol: str
    direction: PositionDirection
    quantity: int
    price: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class NetPosition:
    """Net position after netting."""
    symbol: str
    direction: PositionDirection
    net_quantity: int
    gross_quantity: int
    participating_strategies: list[str]
    participating_managers: list[str]


@dataclass
class RiskCheckResult:
    """Result of risk check."""
    allowed: bool
    blocked: bool = False
    violations: list[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.PLATFORM
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskLimit:
    """Risk limit configuration."""
    level: RiskLevel
    name: str
    limit: float
    unit: str = "percentage"


class SignalNetting:
    """Signal netting and aggregation."""

    def __init__(self):
        self._positions: list[Position] = []

    def add_signal(
        self,
        strategy_name: str,
        manager_id: str,
        symbol: str,
        direction: str,
        quantity: int,
        price: float = 0.0,
    ) -> None:
        """Add signal to netting engine."""
        dir_enum = PositionDirection.BUY if direction.upper() in ["BUY", "LONG"] else PositionDirection.SELL

        self._positions.append(Position(
            strategy_name=strategy_name,
            manager_id=manager_id,
            symbol=symbol,
            direction=dir_enum,
            quantity=quantity,
            price=price,
        ))

    def net_positions(self) -> list[NetPosition]:
        """Calculate net positions after netting."""
        symbol_positions: dict[str, list[Position]] = {}

        for pos in self._positions:
            if pos.symbol not in symbol_positions:
                symbol_positions[pos.symbol] = []
            symbol_positions[pos.symbol].append(pos)

        net_positions: list[NetPosition] = []

        for symbol, positions in symbol_positions.items():
            buy_qty = sum(p.quantity for p in positions if p.direction == PositionDirection.BUY)
            sell_qty = sum(p.quantity for p in positions if p.direction == PositionDirection.SELL)

            net_qty = buy_qty - sell_qty

            if net_qty > 0:
                direction = PositionDirection.BUY
            elif net_qty < 0:
                direction = PositionDirection.SELL
                net_qty = abs(net_qty)
            else:
                continue

            strategies = list(set(p.strategy_name for p in positions))
            managers = list(set(p.manager_id for p in positions))

            net_positions.append(NetPosition(
                symbol=symbol,
                direction=direction,
                net_quantity=net_qty,
                gross_quantity=buy_qty + sell_qty,
                participating_strategies=strategies,
                participating_managers=managers,
            ))

        logger.info(f"Netted {len(self._positions)} signals into {len(net_positions)} net positions")
        return net_positions

    def clear(self) -> None:
        """Clear pending signals."""
        self._positions.clear()

    def get_pending_count(self) -> int:
        """Get count of pending signals."""
        return len(self._positions)


class GlobalRiskManager:
    """Hierarchical risk control."""

    DEFAULT_LIMITS: list[RiskLimit] = [
        RiskLimit(RiskLevel.STRATEGY, "max_position_pct", 0.05, "percentage"),
        RiskLimit(RiskLevel.STRATEGY, "max_loss_daily", 0.02, "percentage"),
        RiskLimit(RiskLevel.MANAGER, "max_position_pct", 0.10, "percentage"),
        RiskLimit(RiskLevel.MANAGER, "max_loss_daily", 0.05, "percentage"),
        RiskLimit(RiskLevel.PLATFORM, "max_stock_weight", 0.02, "percentage"),
        RiskLimit(RiskLevel.PLATFORM, "max_total_leverage", 1.5, "ratio"),
    ]

    def __init__(self):
        self._limits: dict[RiskLevel, dict[str, RiskLimit]] = {}
        for limit in self.DEFAULT_LIMITS:
            if limit.level not in self._limits:
                self._limits[limit.level] = {}
            self._limits[limit.level][limit.name] = limit

    def check_strategy_risk(
        self,
        strategy_name: str,
        positions: list[Position],
        total_equity: float,
    ) -> RiskCheckResult:
        """Check strategy-level risk."""
        violations = []

        total_position_value = sum(p.quantity * p.price for p in positions if p.price > 0)
        position_pct = total_position_value / total_equity if total_equity > 0 else 0

        limit = self._limits.get(RiskLevel.STRATEGY, {}).get("max_position_pct")
        if limit and position_pct > limit.limit:
            violations.append(f"Strategy position {position_pct:.2%} exceeds limit {limit.limit:.2%}")

        return RiskCheckResult(
            allowed=len(violations) == 0,
            blocked=len(violations) > 0,
            violations=violations,
            risk_level=RiskLevel.STRATEGY,
            details={"position_pct": position_pct, "total_equity": total_equity},
        )

    def check_manager_risk(
        self,
        manager_id: str,
        strategy_positions: dict[str, list[Position]],
        total_equity: float,
    ) -> RiskCheckResult:
        """Check manager-level risk."""
        violations = []

        total_value = 0.0
        all_positions: list[Position] = []

        for strat_positions in strategy_positions.values():
            for pos in strat_positions:
                total_value += pos.quantity * pos.price if pos.price > 0 else 0
                all_positions.append(pos)

        position_pct = total_value / total_equity if total_equity > 0 else 0
        limit = self._limits.get(RiskLevel.MANAGER, {}).get("max_position_pct")
        if limit and position_pct > limit.limit:
            violations.append(f"Manager position {position_pct:.2%} exceeds limit {limit.limit:.2%}")

        return RiskCheckResult(
            allowed=len(violations) == 0,
            blocked=len(violations) > 0,
            violations=violations,
            risk_level=RiskLevel.MANAGER,
            details={"manager_id": manager_id, "position_pct": position_pct},
        )

    def check_platform_risk(
        self,
        all_positions: dict[str, list[Position]],
        total_equity: float,
        market_cap: dict[str, float],
    ) -> RiskCheckResult:
        """Check platform-level risk."""
        violations = []

        symbol_weights: dict[str, float] = {}
        for symbol, positions in all_positions.items():
            total_value = sum(p.quantity * p.price for p in positions if p.price > 0)
            symbol_weights[symbol] = total_value / total_equity if total_equity > 0 else 0

        for symbol, weight in symbol_weights.items():
            limit = self._limits.get(RiskLevel.PLATFORM, {}).get("max_stock_weight")
            if limit and weight > limit.limit:
                violations.append(f"Platform weight {weight:.2%} exceeds limit {limit.limit:.2%} for {symbol}")

        return RiskCheckResult(
            allowed=len(violations) == 0,
            blocked=len(violations) > 0,
            violations=violations,
            risk_level=RiskLevel.PLATFORM,
            details={"symbol_weights": symbol_weights},
        )

    def add_limit(self, level: RiskLevel, name: str, limit: float, unit: str = "percentage") -> None:
        """Add or update risk limit."""
        risk_limit = RiskLimit(level, name, limit, unit)
        if level not in self._limits:
            self._limits[level] = {}
        self._limits[level][name] = risk_limit
        logger.info(f"Added risk limit: {level.value}.{name} = {limit} {unit}")


_global_risk_manager: GlobalRiskManager | None = None
_netting: SignalNetting | None = None


def get_risk_manager() -> GlobalRiskManager:
    """Get global risk manager."""
    global _global_risk_manager
    if _global_risk_manager is None:
        _global_risk_manager = GlobalRiskManager()
    return _global_risk_manager


def get_signal_netting() -> SignalNetting:
    """Get global signal netting engine."""
    global _netting
    if _netting is None:
        _netting = SignalNetting()
    return _netting
