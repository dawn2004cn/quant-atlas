from __future__ import annotations
"""Strategy DSL - Configurable stock selection using JSON/YAML."""


import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FactorConfig:
    """Configuration for a single factor."""
    name: str
    field: str
    operator: str  # "gt", "lt", "eq", "between", "in"
    value: Any
    weight: float = 1.0


@dataclass
class StrategyConfig:
    """Strategy configuration using DSL."""
    name: str
    description: str = ""
    factors: List[FactorConfig] = field(default_factory=list)
    min_score: float = 0.0
    max_results: int = 100
    order_by: str = "score"
    ascending: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StrategyConfig":
        """Create from dictionary (JSON/YAML parsed)."""
        factors = []
        for f in data.get("factors", []):
            factors.append(FactorConfig(
                name=f.get("name", ""),
                field=f.get("field", ""),
                operator=f.get("operator", "gt"),
                value=f.get("value"),
                weight=f.get("weight", 1.0)
            ))
        return cls(
            name=data.get("name", "unnamed"),
            description=data.get("description", ""),
            factors=factors,
            min_score=data.get("min_score", 0.0),
            max_results=data.get("max_results", 100),
            order_by=data.get("order_by", "score"),
            ascending=data.get("ascending", False)
        )

    @classmethod
    def from_json(cls, json_str: str) -> "StrategyConfig":
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def to_dict(self) -> Dict[str, Any]:
        """Convert back to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "factors": [
                {"name": f.name, "field": f.field, "operator": f.operator, 
                 "value": f.value, "weight": f.weight}
                for f in self.factors
            ],
            "min_score": self.min_score,
            "max_results": self.max_results,
            "order_by": self.order_by,
            "ascending": self.ascending
        }


class StrategyEngine:
    """Engine to evaluate stocks against strategy config."""

    def __init__(self):
        self._operators = {
            "gt": lambda x, y: x > y,
            "lt": lambda x, y: x < y,
            "eq": lambda x, y: x == y,
            "gte": lambda x, y: x >= y,
            "lte": lambda x, y: x <= y,
            "between": lambda x, y: y[0] <= x <= y[1],
            "in": lambda x, y: x in y,
            "contains": lambda x, y: str(y) in str(x),
        }

    def evaluate(self, strategy: StrategyConfig, stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Evaluate stocks against strategy and return ranked results."""
        if not stocks:
            return []

        results = []
        for stock in stocks:
            score = self._calculate_score(strategy, stock)
            if score >= strategy.min_score:
                stock_copy = dict(stock)
                stock_copy["score"] = score
                results.append(stock_copy)

        # Sort by score
        results.sort(
            key=lambda x: x.get("score", 0) if strategy.ascending else -x.get("score", 0),
            reverse=not strategy.ascending
        )

        return results[:strategy.max_results]

    def _calculate_score(self, strategy: StrategyConfig, stock: Dict[str, Any]) -> float:
        """Calculate weighted score for a stock."""
        total_score = 0.0
        total_weight = 0.0

        for factor in strategy.factors:
            value = stock.get(factor.field)
            if value is None:
                continue

            try:
                op_func = self._operators.get(factor.operator, lambda x, y: False)
                
                # Handle special operators
                if factor.operator == "between":
                    match = op_func(value, factor.value)
                elif factor.operator == "in":
                    match = op_func(value, factor.value)
                elif factor.operator == "contains":
                    match = op_func(str(value), factor.value)
                else:
                    match = op_func(float(value), float(factor.value))

                if match:
                    total_score += factor.weight
                total_weight += factor.weight
            except (TypeError, ValueError):
                continue

        return (total_score / total_weight * 100) if total_weight > 0 else 0.0


# Example strategy configs
EXAMPLE_STRATEGIES = {
    "growth_stocks": {
        "name": "高成长股票",
        "description": "选择营收增长高、利润率好的股票",
        "factors": [
            {"name": "营收增长", "field": "revenue_growth", "operator": "gt", "value": 20, "weight": 2.0},
            {"name": "净利润增长", "field": "profit_growth", "operator": "gt", "value": 15, "weight": 2.0},
            {"name": "ROE", "field": "roe", "operator": "gt", "value": 10, "weight": 1.5},
            {"name": "毛利率", "field": "gross_margin", "operator": "gt", "value": 20, "weight": 1.0},
        ],
        "min_score": 50,
        "max_results": 50
    },
    "value_stocks": {
        "name": "价值股票",
        "description": "选择低估值、高分红的股票",
        "factors": [
            {"name": "低PE", "field": "pe", "operator": "lt", "value": 15, "weight": 2.0},
            {"name": "低PB", "field": "pb", "operator": "lt", "value": 2, "weight": 1.5},
            {"name": "高股息", "field": "dividend_yield", "operator": "gt", "value": 3, "weight": 1.5},
            {"name": "低负债", "field": "debt_ratio", "operator": "lt", "value": 50, "weight": 1.0},
        ],
        "min_score": 40,
        "max_results": 30
    },
    "momentum_stocks": {
        "name": "动量股票",
        "description": "选择近期涨幅较好的股票",
        "factors": [
            {"name": "近5日涨幅", "field": "change_5d", "operator": "gt", "value": 3, "weight": 2.0},
            {"name": "近20日涨幅", "field": "change_20d", "operator": "gt", "value": 5, "weight": 1.5},
            {"name": "成交量放大", "field": "volume_ratio", "operator": "gt", "value": 1.5, "weight": 1.0},
        ],
        "min_score": 30,
        "max_results": 20
    }
}


def get_strategy(name: str) -> Optional[StrategyConfig]:
    """Get a predefined strategy by name."""
    if name in EXAMPLE_STRATEGIES:
        return StrategyConfig.from_dict(EXAMPLE_STRATEGIES[name])
    return None


def load_strategy_from_file(path: str) -> Optional[StrategyConfig]:
    """Load strategy from JSON/YAML file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return StrategyConfig.from_dict(data)
    except Exception as e:
        logger.error(f"Failed to load strategy from {path}: {e}")
        return None


__all__ = ["StrategyConfig", "FactorConfig", "StrategyEngine", "get_strategy", "load_strategy_from_file", "EXAMPLE_STRATEGIES"]