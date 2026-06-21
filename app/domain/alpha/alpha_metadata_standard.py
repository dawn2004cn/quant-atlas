"""Shared Feature Canvas — exchangeable, composable factor metadata standard."""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class FactorCategory(str, Enum):
    MOMENTUM = "momentum"
    REVERSAL = "reversal"
    VOLATILITY = "volatility"
    LIQUIDITY = "liquidity"
    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"
    TECHNICAL = "technical"
    HYBRID = "hybrid"


class CompositionOp(str, Enum):
    ADD = "add"
    MULTIPLY = "multiply"
    ORTHOGONALIZE = "orthogonalize"
    RANK = "rank"
    NEUTRALIZE = "neutralize"
    SMOOTH = "smooth"


@dataclass
class FactorExpression:
    raw_expression: str
    tokens: list[dict[str, Any]] = field(default_factory=list)
    category: FactorCategory = FactorCategory.TECHNICAL
    source: str = "manual"
    smooth_window: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_expression": self.raw_expression,
            "tokens": self.tokens,
            "category": self.category.value,
            "source": self.source,
            "smooth_window": self.smooth_window,
        }


@dataclass
class FactorComposition:
    expression_a: str
    expression_b: str
    operation: CompositionOp
    weight_a: float = 0.5
    weight_b: float = 0.5

    def combined_expression(self) -> str:
        return f"Compose({self.expression_a}, {self.expression_b}, op={self.operation.value})"


@dataclass
class AlphaNote:
    note_id: str
    symbol: str = ""
    market: str = "ALL"
    title: str = ""
    narrative: str = ""
    expression: FactorExpression | None = None
    composition: FactorComposition | None = None
    ic: float | None = None
    ir: float | None = None
    stability: float | None = None
    backtest_pnl: float | None = None
    sharpe: float | None = None
    max_drawdown: float | None = None
    author: str = "system"
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    payload: dict[str, Any] = field(default_factory=dict)

    def to_evidence_note(self) -> dict[str, Any]:
        return {
            "note_id": self.note_id,
            "symbol": self.symbol,
            "market": self.market,
            "title": self.title,
            "narrative": self.narrative,
            "agent_role": "alpha_lab",
            "evidence_key": f"alpha_lab.{self.note_id}",
            "evidence_value": self.narrative or (self.expression.raw_expression if self.expression else ""),
            "strength": "strong" if (self.ic or 0) > 0.05 else "medium",
            "payload": {
                "expression": self.expression.to_dict() if self.expression else None,
                "composition": dataclasses.asdict(self.composition) if self.composition else None,
                "ic": self.ic,
                "ir": self.ir,
                "stability": self.stability,
                "backtest_pnl": self.backtest_pnl,
                "sharpe": self.sharpe,
                "max_drawdown": self.max_drawdown,
                "tags": self.tags,
                "author": self.author,
            },
        }


def ensure_composable(a: dict, b: dict) -> dict:
    return {
        "expression_a": a,
        "expression_b": b,
        "operation": CompositionOp.ADD.value,
        "schema_version": "v1",
    }


__all__ = [
    "FactorCategory",
    "CompositionOp",
    "FactorExpression",
    "FactorComposition",
    "AlphaNote",
    "ensure_composable",
]
