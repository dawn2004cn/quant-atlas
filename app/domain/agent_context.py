from __future__ import annotations

"""Standardized AgentContext for consistent data passing between agents."""


from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MarketSnapshot:
    """Snapshot of current market data."""
    market: str = "CN"
    index: float = 0.0
    change_pct: float = 0.0
    volume: int = 0
    turnover: float = 0.0
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "market": self.market,
            "index": self.index,
            "change_pct": self.change_pct,
            "volume": self.volume,
            "turnover": self.turnover,
            "timestamp": self.timestamp
        }


@dataclass
class StockData:
    """Stock information for agent context."""
    code: str = ""
    name: str = ""
    price: float = 0.0
    change_pct: float = 0.0
    volume: int = 0
    amount: float = 0.0
    industry: str = ""
    market_cap: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "price": self.price,
            "change_pct": self.change_pct,
            "volume": self.volume,
            "amount": self.amount,
            "industry": self.industry,
            "market_cap": self.market_cap
        }


@dataclass
class UserPreference:
    """User investment preferences."""
    risk_tolerance: str = "moderate"  # "conservative", "moderate", "aggressive"
    investment_horizon: str = "medium"  # "short", "medium", "long"
    sectors: list[str] = field(default_factory=list)
    excluded_sectors: list[str] = field(default_factory=list)
    max_position_size: float = 10.0  # percentage
    min_dividend_yield: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_tolerance": self.risk_tolerance,
            "investment_horizon": self.investment_horizon,
            "sectors": self.sectors,
            "excluded_sectors": self.excluded_sectors,
            "max_position_size": self.max_position_size,
            "min_dividend_yield": self.min_dividend_yield
        }


@dataclass
class HistoryMemory:
    """Historical context for the agent session."""
    recent_queries: list[str] = field(default_factory=list)
    selected_stocks: list[str] = field(default_factory=list)
    executed_trades: list[dict[str, Any]] = field(default_factory=list)
    session_start: str = ""

    def add_query(self, query: str) -> None:
        self.recent_queries.append(query)
        if len(self.recent_queries) > 10:
            self.recent_queries = self.recent_queries[-10:]

    def add_stock(self, code: str) -> None:
        if code not in self.selected_stocks:
            self.selected_stocks.append(code)
            if len(self.selected_stocks) > 20:
                self.selected_stocks = self.selected_stocks[-20:]

    def add_trade(self, trade: dict[str, Any]) -> None:
        self.executed_trades.append(trade)
        if len(self.executed_trades) > 50:
            self.executed_trades = self.executed_trades[-50:]

    def to_dict(self) -> dict[str, Any]:
        return {
            "recent_queries": self.recent_queries,
            "selected_stocks": self.selected_stocks,
            "executed_trades": self.executed_trades,
            "session_start": self.session_start
        }


@dataclass
class AgentContext:
    """Standardized context object for all agents."""
    user_id: str = ""
    session_id: str = ""
    market_snapshot: MarketSnapshot = field(default_factory=MarketSnapshot)
    current_stock: StockData | None = None
    watchlist: list[StockData] = field(default_factory=list)
    user_preference: UserPreference = field(default_factory=UserPreference)
    history: HistoryMemory = field(default_factory=HistoryMemory)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "market_snapshot": self.market_snapshot.to_dict(),
            "current_stock": self.current_stock.to_dict() if self.current_stock else None,
            "watchlist": [s.to_dict() for s in self.watchlist],
            "user_preference": self.user_preference.to_dict(),
            "history": self.history.to_dict(),
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentContext:
        """Create from dictionary."""
        ctx = cls(
            user_id=data.get("user_id", ""),
            session_id=data.get("session_id", ""),
            metadata=data.get("metadata", {})
        )

        if "market_snapshot" in data:
            ctx.market_snapshot = MarketSnapshot(**data["market_snapshot"])

        if "current_stock" in data and data["current_stock"]:
            ctx.current_stock = StockData(**data["current_stock"])

        if "watchlist" in data:
            ctx.watchlist = [StockData(**s) for s in data["watchlist"]]

        if "user_preference" in data:
            ctx.user_preference = UserPreference(**data["user_preference"])

        if "history" in data:
            ctx.history = HistoryMemory(**data["history"])

        return ctx

    def to_prompt_context(self) -> str:
        """Generate prompt-friendly context summary."""
        lines = [
            f"User: {self.user_id}",
            f"Market: {self.market_snapshot.market} Index: {self.market_snapshot.index:.2f}",
            f"Risk Tolerance: {self.user_preference.risk_tolerance}",
        ]

        if self.current_stock:
            lines.append(f"Current Stock: {self.current_stock.code} {self.current_stock.name}")

        if self.history.selected_stocks:
            lines.append(f"Recent: {', '.join(self.history.selected_stocks[-3:])}")

        return "\n".join(lines)


# Factory function for creating context
def create_agent_context(
    user_id: str,
    session_id: str,
    market_data: dict[str, Any] | None = None,
    user_prefs: dict[str, Any] | None = None
) -> AgentContext:
    """Factory function to create AgentContext with defaults."""
    ctx = AgentContext(
        user_id=user_id,
        session_id=session_id,
        history=HistoryMemory(session_start=datetime.now().isoformat())
    )

    if market_data:
        ctx.market_snapshot = MarketSnapshot(**market_data)

    if user_prefs:
        ctx.user_preference = UserPreference(**user_prefs)

    return ctx


__all__ = [
    "AgentContext",
    "MarketSnapshot",
    "StockData",
    "UserPreference",
    "HistoryMemory",
    "create_agent_context"
]
