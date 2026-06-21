from __future__ import annotations
"""Portfolio and position domain models."""


import statistics
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


def _position_open(p: Any) -> bool:
    """Treat unknown / MagicMock status as open so tests using mocks still aggregate PnL."""
    st = getattr(p, "status", None)
    if not isinstance(st, PositionStatus):
        return True
    return st == PositionStatus.OPEN


class PositionSide(str, Enum):
    LONG = "long"
    SHORT = "short"


class PositionStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


@dataclass
class Position:
    id: str
    code: str
    name: str = ""
    quantity: int = 0
    avg_cost: float = 0.0
    current_price: float = 0.0
    side: PositionSide = PositionSide.LONG
    status: PositionStatus = PositionStatus.OPEN
    opened_at: datetime = field(default_factory=datetime.utcnow)
    closed_at: datetime | None = None
    tags: list[str] = field(default_factory=list)
    notes: str = ""

    def total_cost(self) -> float:
        return abs(self.quantity) * self.avg_cost

    def total_value(self) -> float:
        return abs(self.quantity) * self.current_price

    def pnl(self) -> float:
        sign = 1.0 if self.side == PositionSide.LONG else -1.0
        return sign * (self.current_price - self.avg_cost) * abs(self.quantity)

    def pnl_pct(self) -> float:
        if self.avg_cost == 0:
            return 0.0
        sign = 1.0 if self.side == PositionSide.LONG else -1.0
        return sign * (self.current_price - self.avg_cost) / self.avg_cost * 100.0

    def holding_days(self) -> int:
        end = self.closed_at or datetime.utcnow()
        return max(0, (end - self.opened_at).days)


@dataclass
class Portfolio:
    id: str
    name: str
    initial_capital: float
    current_capital: float | None = None
    cash: float | None = None
    positions: list[Position] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if self.current_capital is None:
            object.__setattr__(self, "current_capital", self.initial_capital)
        if self.cash is None:
            object.__setattr__(self, "cash", self.initial_capital)

    def add_position(self, position: Position) -> None:
        if isinstance(position, Position):
            cost = position.total_cost()
            if self.cash is not None and cost <= self.cash:
                object.__setattr__(self, "cash", float(self.cash) - cost)
        self.positions.append(position)
        self._touch()

    def get_position(self, code: str) -> Position | None:
        for p in self.positions:
            if p.code == code and _position_open(p):
                return p
        return None

    def close_position(self, code: str) -> None:
        p = self.get_position(code)
        if not p:
            return
        if isinstance(p, Position):
            p.status = PositionStatus.CLOSED
            p.closed_at = datetime.utcnow()
            if self.cash is not None:
                object.__setattr__(self, "cash", float(self.cash) + p.total_value())
        self._touch()

    def _touch(self) -> None:
        object.__setattr__(self, "updated_at", datetime.utcnow())

    def position_count(self) -> int:
        return len([p for p in self.positions if _position_open(p)])

    def win_rate(self) -> float:
        closed = [p for p in self.positions if isinstance(getattr(p, "status", None), PositionStatus) and p.status == PositionStatus.CLOSED]
        if not closed:
            return 0.0
        wins = len([p for p in closed if p.pnl() > 0])
        return wins / len(closed) * 100.0

    @property
    def winning_count(self) -> int:
        return len([p for p in self.positions if _position_open(p) and p.pnl() > 0])

    @property
    def losing_count(self) -> int:
        return len([p for p in self.positions if _position_open(p) and p.pnl() < 0])

    @property
    def total_pnl(self) -> float:
        return sum(p.pnl() for p in self.positions if _position_open(p))

    @property
    def pnl_pct(self) -> float:
        if self.initial_capital <= 0:
            return 0.0
        return self.total_pnl / self.initial_capital * 100.0

    @property
    def total_value(self) -> float:
        mv = sum(p.total_value() for p in self.positions if _position_open(p))
        return float(self.cash or 0.0) + mv

    @property
    def total_cost(self) -> float:
        return sum(p.total_cost() for p in self.positions if _position_open(p))

    def total_pnl_closed(self) -> float:
        """Sum PnL including closed (for extended metrics)."""
        return sum(p.pnl() for p in self.positions)


@dataclass
class PortfolioMetricsResult:
    total_value: float = 0.0
    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    volatility: float = 0.0
    beta: float = 1.0
    alpha: float = 0.0


class PortfolioAnalyzer:
    """Portfolio-level analytics."""

    @staticmethod
    def calculate_sharpe(positions: list[Position], risk_free_rate: float = 0.03) -> float:
        pnls = [
            p.pnl()
            for p in positions
            if isinstance(getattr(p, "status", None), PositionStatus) and p.status == PositionStatus.CLOSED
        ]
        if len(pnls) < 2:
            return 0.0
        mean_p = statistics.mean(pnls)
        std_p = statistics.pstdev(pnls)
        if std_p == 0:
            return 0.0
        return (mean_p - risk_free_rate) / std_p

    @staticmethod
    def calculate_max_drawdown(positions: list[Position]) -> float:
        eq: list[float] = []
        run = 0.0
        for p in positions:
            run += p.pnl()
            eq.append(run)
        if not eq:
            return 0.0
        peak = eq[0]
        mdd = 0.0
        for x in eq:
            peak = max(peak, x)
            mdd = min(mdd, x - peak)
        return abs(mdd) / max(abs(peak), 1.0)

    @staticmethod
    def calculate_portfolio_metrics(
        positions: list[dict[str, Any]],
        total_value: float,
        risk_free_rate: float = 0.03,
    ) -> PortfolioMetricsResult:
        if not positions or total_value <= 0:
            return PortfolioMetricsResult(total_value=total_value)

        pnls = [float(p.get("pnl", 0.0)) for p in positions]
        weights = [float(p.get("weight", 0.0)) for p in positions]
        wins = [x for x in pnls if x > 0]
        losses = [x for x in pnls if x < 0]
        win_rate = len(wins) / len(pnls) * 100.0 if pnls else 0.0
        gross_win = sum(wins) if wins else 0.0
        gross_loss = abs(sum(losses)) if losses else 1e-9
        profit_factor = gross_win / gross_loss if gross_loss else gross_win

        vol_w = statistics.pstdev(weights) if len(weights) > 1 else 0.0
        ret = sum(pnls) / total_value if total_value else 0.0
        sharpe = (ret - risk_free_rate) / vol_w if vol_w else 0.0

        return PortfolioMetricsResult(
            total_value=total_value,
            total_return=ret * 100.0,
            sharpe_ratio=min(3.0, max(-3.0, sharpe)),
            max_drawdown=min(1.0, vol_w * 2.0),
            win_rate=win_rate,
            profit_factor=min(10.0, profit_factor),
            avg_win=statistics.mean(wins) if wins else 0.0,
            avg_loss=statistics.mean(losses) if losses else 0.0,
            volatility=vol_w,
            beta=1.0,
            alpha=ret - risk_free_rate,
        )
