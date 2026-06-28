from __future__ import annotations
"""
AI 投资委员会 - 核心架构

Design Patterns Applied:
- Strategy: StrategyLibrary for different market regimes
- Observer: MarketAnalysisObserver for event notifications
- State: MarketStateMachine for regime transitions
- Command: TradeCommand for trade execution
- Template: AnalysisTemplate for market analysis
- Visitor: MarketDataVisitor for data operations
- Composite: Portfolio composite structure
- Facade: InvestmentCommitteeFacade for simplified interface
"""


from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from collections.abc import Callable

from app.core.llm_config import get_llm
from app.core.patterns.behavioral import (
    Command, Strategy as PatternStrategy,
    Observer as PatternObserver, Visitor as PatternVisitor
)
from app.core.patterns.structural import Composite


class MarketIndex(Enum):
    """五大市场指数"""
    SHANGHAI = "上证指数"
    SHENZHEN = "深证成指"
    CHINEXT = "创业板指"
    STAR = "科创50"
    BEIJING = "北证50"


class MarketRegime(Enum):
    """市场状态"""
    BULL = "牛市"
    BEAR = "熊市"
    SIDEWAYS = "震荡市"
    UNKNOWN = "未知"


@dataclass(frozen=True)
class MarketState:
    """单个市场状态 (Immutable Value Object)"""
    index: MarketIndex
    regime: MarketRegime
    confidence: float
    adx: float
    ma50_position: str
    trend_strength: float
    last_updated: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))


@dataclass(frozen=True)
class MarketAnalysis:
    """五大市场综合分析 (Immutable Value Object)"""
    markets: tuple[tuple[MarketIndex, MarketState], ...]
    overall_regime: MarketRegime
    recommended_strategies: tuple[str, ...]
    risk_level: str
    analysis_time: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))


@dataclass(frozen=True)
class StockSignal:
    """个股信号 (Immutable Value Object)"""
    symbol: str
    name: str
    market: str
    strategy: str
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    reasoning: str
    regime_suitability: str


@dataclass(frozen=True)
class TradeRecord:
    """交易记录 (Immutable Value Object)"""
    id: int
    symbol: str
    name: str
    strategy: str
    direction: str
    price: float
    quantity: int
    amount: float
    trade_time: str
    pnl: float
    pnl_pct: float
    status: str


@dataclass
class PortfolioState:
    """组合状态 (Mutable)"""
    total_capital: float = 500000.0
    available_cash: float = 500000.0
    positions: list[dict] = field(default_factory=list)
    total_value: float = 500000.0
    total_pnl: float = 0.0
    daily_pnl: float = 0.0


class Strategy(PatternStrategy):
    """Trading strategy interface."""

    def execute(self, data: Any) -> Any:
        return None

    @abstractmethod
    def select_stocks(self, stock_pool: list[dict], market_analysis: MarketAnalysis) -> list[StockSignal]:
        """Select stocks based on strategy."""
        pass

    @abstractmethod
    def calculate_stop_loss(self, price: float) -> float:
        """Calculate stop loss price."""
        pass

    @abstractmethod
    def calculate_take_profit(self, price: float) -> float:
        """Calculate take profit price."""
        pass


class BullStrategy(Strategy):
    """Bull market strategy."""

    def select_stocks(self, stock_pool: list[dict], market_analysis: MarketAnalysis) -> list[StockSignal]:
        signals = []
        for stock in stock_pool[:10]:
            price = stock.get("close", 0)
            if price <= 0:
                continue
            signals.append(StockSignal(
                symbol=stock.get("symbol", ""),
                name=stock.get("name", ""),
                market=stock.get("market", ""),
                strategy="牛市策略",
                entry_price=price,
                stop_loss=self.calculate_stop_loss(price),
                take_profit=self.calculate_take_profit(price),
                confidence=0.75,
                reasoning="牛市突破形态",
                regime_suitability="牛市"
            ))
        return signals

    def calculate_stop_loss(self, price: float) -> float:
        return price * 0.95

    def calculate_take_profit(self, price: float) -> float:
        return price * 1.15


class BearStrategy(Strategy):
    """Bear market strategy."""

    def select_stocks(self, stock_pool: list[dict], market_analysis: MarketAnalysis) -> list[StockSignal]:
        return []

    def calculate_stop_loss(self, price: float) -> float:
        return price * 0.90

    def calculate_take_profit(self, price: float) -> float:
        return price * 1.05


class SidewaysStrategy(Strategy):
    """Sideways market strategy."""

    def select_stocks(self, stock_pool: list[dict], market_analysis: MarketAnalysis) -> list[StockSignal]:
        signals = []
        for stock in stock_pool[:10]:
            price = stock.get("close", 0)
            if price <= 0:
                continue
            signals.append(StockSignal(
                symbol=stock.get("symbol", ""),
                name=stock.get("name", ""),
                market=stock.get("market", ""),
                strategy="震荡市策略",
                entry_price=price,
                stop_loss=self.calculate_stop_loss(price),
                take_profit=self.calculate_take_profit(price),
                confidence=0.65,
                reasoning="震荡区间整理",
                regime_suitability="震荡市"
            ))
        return signals

    def calculate_stop_loss(self, price: float) -> float:
        return price * 0.93

    def calculate_take_profit(self, price: float) -> float:
        return price * 1.08


class StrategyFactory:
    """Factory for creating strategies."""

    _strategies: dict[str, type[Strategy]] = {
        "bull": BullStrategy,
        "bear": BearStrategy,
        "sideways": SidewaysStrategy,
    }

    @classmethod
    def create(cls, regime: str) -> Strategy:
        strategy_class = cls._strategies.get(regime.lower(), SidewaysStrategy)
        return strategy_class()

    @classmethod
    def register(cls, name: str, strategy_class: type[Strategy]) -> None:
        cls._strategies[name.lower()] = strategy_class


class MarketRegimeManager:
    """Market regime manager (Simplified)."""

    def get_current_regime(self) -> str:
        return "震荡市"


class StrategyLibrary:
    """十大天王策略库 (Library pattern)"""

    BULL_STRATEGIES = (
        "米勒维尼 VCP",
        "缺口动量",
        "一目均衡表",
    )

    BEAR_STRATEGIES = (
        "康纳斯 RSI(2)",
        "VSA 恐慌停止量",
        "维克多 2B",
    )

    SIDEWAYS_STRATEGIES = (
        "TTM 挤压",
        "机构 VWAP 回踩",
        "超级趋势",
        "布林+RSI 极限反转",
    )

    def get_strategies_for_regime(self, regime: str) -> tuple[str, ...]:
        if regime == "牛市":
            return self.BULL_STRATEGIES
        elif regime == "熊市":
            return self.BEAR_STRATEGIES
        return self.SIDEWAYS_STRATEGIES

    def get_all_strategies(self) -> dict[str, tuple[str, ...]]:
        return {
            "牛市主攻": self.BULL_STRATEGIES,
            "熊市防守": self.BEAR_STRATEGIES,
            "震荡/万能": self.SIDEWAYS_STRATEGIES,
        }


class TradeCommand(Command):
    """Command for trade execution."""

    def __init__(
        self,
        receiver: Any,
        execute_fn: Callable,
        undo_fn: Callable | None = None
    ) -> None:
        self._receiver = receiver
        self._execute_fn = execute_fn
        self._undo_fn = undo_fn
        self._executed = False

    def execute(self) -> Any:
        result = self._execute_fn(self._receiver)
        self._executed = True
        return result

    def undo(self) -> None:
        if self._executed and self._undo_fn:
            self._undo_fn(self._receiver)
            self._executed = False


class MarketAnalysisObserver(PatternObserver):
    """Observer for market analysis events."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._updates: list[MarketAnalysis] = []

    def update(self, data: Any) -> None:
        if isinstance(data, MarketAnalysis):
            self._updates.append(data)

    def get_updates(self) -> list[MarketAnalysis]:
        return self._updates


class MarketStateMachine:
    """State machine for market regime transitions."""

    def __init__(self, initial_state: MarketRegime = MarketRegime.UNKNOWN) -> None:
        self._current_state = initial_state

    @property
    def current_state(self) -> MarketRegime:
        return self._current_state

    def transition_to(self, new_state: MarketRegime) -> None:
        self._current_state = new_state

    def can_transition_to(self, new_state: MarketRegime) -> bool:
        valid_transitions = {
            MarketRegime.BULL: [MarketRegime.SIDEWAYS],
            MarketRegime.BEAR: [MarketRegime.SIDEWAYS],
            MarketRegime.SIDEWAYS: [MarketRegime.BULL, MarketRegime.BEAR],
            MarketRegime.UNKNOWN: [MarketRegime.BULL, MarketRegime.BEAR, MarketRegime.SIDEWAYS],
        }
        return new_state in valid_transitions.get(self._current_state, [])


class MarketDataElement(PatternVisitor):
    """Element for visitor pattern."""

    def __init__(self, data: dict) -> None:
        self._data = data

    def accept(self, visitor: PatternVisitor) -> Any:
        return visitor.visit_data(self)

    @property
    def data(self) -> dict:
        return self._data


class MarketDataVisitor(PatternVisitor):
    """Visitor for market data operations."""

    def visit_data(self, element: MarketDataElement) -> dict:
        return element.data


class PortfolioComponent(Composite):
    """Component for portfolio composition."""

    def __init__(self, name: str) -> None:
        self._name = name

    def get_operation(self) -> str:
        return self._name


class InvestmentCommitteeFacade:
    """Facade for simplified investment committee interface."""

    def __init__(self) -> None:
        self._committee = AIInvestmentCommittee()

    def analyze_market(self, index_data: dict[MarketIndex, Any]) -> MarketAnalysis:
        return self._committee.analyze_markets(index_data)

    def execute_trade(self, signal: StockSignal) -> TradeRecord | None:
        return self._committee.execute_trade(signal)

    def get_portfolio_state(self) -> PortfolioState:
        return self._committee.portfolio


class AIInvestmentCommittee:
    """AI 投资委员会 - 总指挥

    Patterns Applied:
    - Strategy: StrategyLibrary for regime-based strategies
    - Observer: Market analysis event notification
    - State: Market regime state management
    - Command: Trade execution commands
    - Facade: Simplified interface
    """

    def __init__(self, llm=None) -> None:
        self._llm = llm or get_llm()
        self._agents: dict[str, object] = {}
        self._portfolio = PortfolioState()
        self._strategy_library = StrategyLibrary()
        self._state_machine = MarketStateMachine()
        self._observers: list[PatternObserver] = []
        self._command_history: list[Command] = []

    @property
    def portfolio(self) -> PortfolioState:
        return self._portfolio

    @property
    def strategy_library(self) -> StrategyLibrary:
        return self._strategy_library

    def attach_observer(self, observer: PatternObserver) -> None:
        if observer not in self._observers:
            self._observers.append(observer)

    def detach_observer(self, observer: PatternObserver) -> None:
        self._observers.remove(observer)

    def _notify_observers(self, data: Any) -> None:
        for observer in self._observers:
            observer.update(data)

    def analyze_markets(self, index_data: dict[MarketIndex, Any]) -> MarketAnalysis:
        markets = {}
        bullish_count = 0

        for index, df in index_data.items():
            if df is None or len(df) < 50:
                markets[index] = MarketState(
                    index=index,
                    regime=MarketRegime.UNKNOWN,
                    confidence=0.0,
                    adx=0.0,
                    ma50_position="unknown",
                    trend_strength=0.0
                )
                continue

            manager = MarketRegimeManager()
            regime_str = manager.get_current_regime()

            if regime_str == "牛市":
                regime = MarketRegime.BULL
                bullish_count += 1
            elif regime_str == "熊市":
                regime = MarketRegime.BEAR
            else:
                regime = MarketRegime.SIDEWAYS

            current = df.iloc[-1]
            adx = current.get("ADX", 0)
            confidence = min(adx / 50, 1.0) if adx else 0.5

            ma50 = current.get("MA50", 0)
            close = current.get("Close", 0)
            ma50_pos = "above" if close > ma50 else "below"

            markets[index] = MarketState(
                index=index,
                regime=regime,
                confidence=confidence,
                adx=adx,
                ma50_position=ma50_pos,
                trend_strength=current.get("MA200_Slope", 0) / close * 100
            )

        if bullish_count >= 4:
            overall = MarketRegime.BULL
            strategies = ("牛市主攻", "趋势跟随")
            risk = "medium"
            self._state_machine.transition_to(MarketRegime.BULL)
        elif bullish_count <= 1:
            overall = MarketRegime.BEAR
            strategies = ("熊市防守", "空仓等待")
            risk = "high"
            self._state_machine.transition_to(MarketRegime.BEAR)
        else:
            overall = MarketRegime.SIDEWAYS
            strategies = ("震荡/万能", "高抛低吸")
            risk = "low"
            self._state_machine.transition_to(MarketRegime.SIDEWAYS)

        analysis = MarketAnalysis(
            markets=tuple(markets.items()),
            overall_regime=overall,
            recommended_strategies=strategies,
            risk_level=risk
        )

        self._notify_observers(analysis)
        return analysis

    def select_stocks(self, market_analysis: MarketAnalysis, stock_pool: list[dict]) -> list[StockSignal]:
        regime = market_analysis.overall_regime.value
        self._strategy_library.get_strategies_for_regime(regime)

        strategy = StrategyFactory.create(regime)
        signals = strategy.select_stocks(stock_pool[:20], market_analysis)

        return signals[:5]

    def execute_trade(self, signal: StockSignal, direction: str = "buy") -> TradeRecord | None:
        price = signal.entry_price
        amount = self._portfolio.total_capital * 0.3
        quantity = int(amount / price / 100) * 100

        if quantity < 100:
            return None

        trade_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        record = TradeRecord(
            id=len(self._command_history) + 1,
            symbol=signal.symbol,
            name=signal.name,
            strategy=signal.strategy,
            direction=direction,
            price=price,
            quantity=quantity,
            amount=quantity * price,
            trade_time=trade_time,
            pnl=0.0,
            pnl_pct=0.0,
            status="holding"
        )

        command = TradeCommand(
            receiver=self._portfolio,
            execute_fn=lambda p: self._execute_trade(p, signal, record),
            undo_fn=lambda p: self._undo_trade(p, record)
        )
        command.execute()
        self._command_history.append(command)

        return record

    def _execute_trade(self, portfolio: PortfolioState, signal: StockSignal, record: TradeRecord) -> None:
        portfolio.available_cash -= record.amount
        portfolio.positions.append({
            "symbol": signal.symbol,
            "entry_price": signal.entry_price,
            "quantity": record.quantity,
            "stop_loss": signal.stop_loss,
            "take_profit": signal.take_profit,
            "strategy": signal.strategy
        })

    def _undo_trade(self, portfolio: PortfolioState, record: TradeRecord) -> None:
        portfolio.available_cash += record.amount
        portfolio.positions = [
            p for p in portfolio.positions if p.get("symbol") != record.symbol
        ]

    def undo_last_trade(self) -> bool:
        if self._command_history:
            command = self._command_history.pop()
            command.undo()
            return True
        return False

    def check_positions(self) -> list[TradeRecord]:
        closed = []
        to_remove = []

        for i, pos in enumerate(self._portfolio.positions):
            current_price = pos.get("entry_price", 0)

            if current_price <= pos.get("stop_loss", 0):
                pnl = (pos.get("stop_loss", 0) - pos.get("entry_price", 0)) * pos.get("quantity", 0)
                record = self._create_close_record(pos, pnl, "止损")
                closed.append(record)
                to_remove.append(i)

            elif current_price >= pos.get("take_profit", 0):
                pnl = (pos.get("take_profit", 0) - pos.get("entry_price", 0)) * pos.get("quantity", 0)
                record = self._create_close_record(pos, pnl, "止盈")
                closed.append(record)
                to_remove.append(i)

        for i in reversed(to_remove):
            self._portfolio.positions.pop(i)

        return closed

    def _create_close_record(self, pos: dict, pnl: float, reason: str) -> TradeRecord:
        entry_price = pos.get("entry_price", 0)
        quantity = pos.get("quantity", 0)
        return TradeRecord(
            id=0,
            symbol=pos.get("symbol", ""),
            name=pos.get("name", ""),
            strategy=pos.get("strategy", ""),
            direction="sell",
            price=entry_price,
            quantity=quantity,
            amount=entry_price * quantity,
            trade_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            pnl=pnl,
            pnl_pct=pnl / (entry_price * quantity) * 100 if entry_price * quantity > 0 else 0,
            status=f"closed_{reason}"
        )


__all__ = [
    'MarketIndex',
    'MarketRegime',
    'MarketState',
    'MarketAnalysis',
    'StockSignal',
    'TradeRecord',
    'PortfolioState',
    'Strategy',
    'BullStrategy',
    'BearStrategy',
    'SidewaysStrategy',
    'StrategyFactory',
    'StrategyLibrary',
    'TradeCommand',
    'MarketAnalysisObserver',
    'MarketStateMachine',
    'MarketDataElement',
    'MarketDataVisitor',
    'PortfolioComponent',
    'InvestmentCommitteeFacade',
    'AIInvestmentCommittee',
]
