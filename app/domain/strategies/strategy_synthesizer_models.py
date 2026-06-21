"""Domain models for the Strategy Synthesizer pipeline.

These dataclasses represent a complete strategy as an abstract syntax tree (AST)
that can be compiled into multiple language targets (Python, PineScript, TDX, MQL5).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class OperatorKind(str, Enum):
    """Operators supported in factor comparisons."""

    EQUALS = "equals"
    GREATER = "greater"
    LESS = "less"
    GREATER_OR_EQUAL = "greater_or_equal"
    LESS_OR_EQUAL = "less_or_equal"
    ABOVE_SMA = "above_sma"
    BELOW_SMA = "below_sma"
    CROSS_ABOVE = "cross_above"
    CROSS_BELOW = "cross_below"
    RSI_OVERBOUGHT = "rsi_overbought"
    RSI_OVERSOLD = "rsi_oversold"
    VOLUME_SPIKE = "volume_spike"
    BREAKOUT = "breakout"
    BREAKDOWN = "breakdown"
    MACD_BULLISH = "macd_bullish"
    MACD_BEARISH = "macd_bearish"


class ExitMode(str, Enum):
    """Types of trade exit rules."""

    PERCENT_STOP = "percent_stop"
    INDICATOR_STOP = "indicator_stop"
    TIME_STOP = "time_stop"
    TRAILING_STOP = "trailing_stop"
    MANUAL = "manual"


class ConditionLogic(str, Enum):
    """Logical connectors between condition children."""

    AND = "and"
    OR = "or"
    NOT = "not"


class LanguageTarget(str, Enum):
    """Compilation target languages."""

    PYTHON = "python"
    PINE = "pine"
    TDX = "tdx"
    MQL5 = "mql5"

    @classmethod
    def to_label(cls, value: str) -> str:
        """Human-readable label for a target."""
        return {
            "python": "Python (回测引擎)",
            "pine": "PineScript (TradingView)",
            "tdx": "通达信 (TDX)",
            "mql5": "MQL5 (MT5)",
        }.get(value, value)


# ---------------------------------------------------------------------------
# AST node definitions
# ---------------------------------------------------------------------------


@dataclass
class FactorNode:
    """A leaf comparison between two factors.

    Examples::

        price > SMA(20)
        RSI < 30
        volume > MA(volume, 5) * 2
    """

    left_factor: str
    right_factor: str
    operator: OperatorKind
    params: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "left_factor": self.left_factor,
            "right_factor": self.right_factor,
            "operator": self.operator.value,
            "params": self.params,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FactorNode:
        return cls(
            left_factor=data["left_factor"],
            right_factor=data["right_factor"],
            operator=OperatorKind(data["operator"]),
            params=data.get("params", {}),
        )


@dataclass
class ConditionGroup:
    """A logical grouping of factor nodes or sub-groups.

    Examples::

        AND [price > SMA(20), RSI < 30]
        OR [price > EMA(60), volume > volume_ma_5 * 2]
    """

    logic: ConditionLogic
    children: list[FactorNode | ConditionGroup]

    def to_dict(self) -> dict[str, Any]:
        converted_children: list[dict[str, Any]] = []
        for child in self.children:
            if isinstance(child, ConditionGroup):
                converted_children.append(child.to_dict())
            else:
                converted_children.append(child.to_dict())
        return {
            "logic": self.logic.value,
            "children": converted_children,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConditionGroup:
        children: list[FactorNode | ConditionGroup] = []
        for child_data in data.get("children", []):
            if "logic" in child_data and "children" in child_data:
                children.append(cls.from_dict(child_data))
            else:
                children.append(FactorNode.from_dict(child_data))
        return cls(
            logic=ConditionLogic(data["logic"]),
            children=children,
        )


@dataclass
class ExitRule:
    """A stop-loss or take-profit rule."""

    exit_mode: ExitMode
    threshold: float  # e.g., 0.05 for 5 %
    reference: str  # "entry_price", "high_watermark"
    trailing: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "exit_mode": self.exit_mode.value,
            "threshold": self.threshold,
            "reference": self.reference,
            "trailing": self.trailing,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExitRule:
        return cls(
            exit_mode=ExitMode(data["exit_mode"]),
            threshold=float(data["threshold"]),
            reference=data.get("reference", "entry_price"),
            trailing=data.get("trailing", False),
        )


# ---------------------------------------------------------------------------
# Top-level strategy
# ---------------------------------------------------------------------------


@dataclass
class StrategySpec:
    """Complete strategy AST — compilable to Python, PineScript, TDX, MQL5.

    Usage::

        spec = StrategySpec(
            name="均线突破",
            description="股价突破20日均线且RSI低于30时买入",
            entry_conditions=...,
            exit_rules=[
                ExitRule(ExitMode.PERCENT_STOP, 0.05, "entry_price"),
                ExitRule(ExitMode.PERCENT_STOP, 0.10, "entry_price"),
            ],
        )
        code = strategy_synthesizer.compile_to_language(spec, LanguageTarget.PINE)
    """

    name: str
    description: str
    entry_conditions: ConditionGroup
    exit_rules: list[ExitRule] = field(default_factory=list)
    symbol: str = ""
    market: str = "CN"
    universe: str = "all_stocks"
    max_positions: int = 10
    capital_per_trade: float = 0.1
    timeframes: list[str] = field(default_factory=lambda: ["1d"])
    compiled_code: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the full AST to a dict (JSON-serializable)."""
        return {
            "name": self.name,
            "description": self.description,
            "entry_conditions": self.entry_conditions.to_dict(),
            "exit_rules": [r.to_dict() for r in self.exit_rules],
            "symbol": self.symbol,
            "market": self.market,
            "universe": self.universe,
            "max_positions": self.max_positions,
            "capital_per_trade": self.capital_per_trade,
            "timeframes": self.timeframes,
            "compiled_code": self.compiled_code,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StrategySpec:
        entry_conditions = ConditionGroup.from_dict(data["entry_conditions"])
        exit_rules = [ExitRule.from_dict(r) for r in data.get("exit_rules", [])]
        compiled_code = data.get("compiled_code", {})
        if isinstance(compiled_code, list):
            # Allow a list of {target, code} dicts
            compiled_code = {c.get("target", c.get("language", "")): c["code"] for c in compiled_code}
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            entry_conditions=entry_conditions,
            exit_rules=exit_rules,
            symbol=data.get("symbol", ""),
            market=data.get("market", "CN"),
            universe=data.get("universe", "all_stocks"),
            max_positions=data.get("max_positions", 10),
            capital_per_trade=float(data.get("capital_per_trade", 0.1)),
            timeframes=data.get("timeframes", ["1d"]),
            compiled_code=compiled_code,
            metadata=data.get("metadata", {}),
        )
