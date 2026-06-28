from __future__ import annotations
"""Application DTOs for strategy optimization."""


from enum import Enum
from pydantic import BaseModel, Field


class ComparisonOperator(str, Enum):
    GT = ">"
    LT = "<"
    GTE = ">="
    LTE = "<="
    EQ = "="
    NE = "!="


class LogicalOperator(str, Enum):
    AND = "AND"
    OR = "OR"
    NOT = "NOT"


class ScreeningCondition(BaseModel):
    """单个筛选条件"""
    field: str = Field(..., description="筛选字段，如 RSI_14, price, pe, change_pct, avg_sentiment_score")
    operator: ComparisonOperator = Field(..., description="比较运算符")
    value: float = Field(..., description="阈值")


class ScreeningRule(BaseModel):
    """筛选规则，支持多条件组合"""
    operator: LogicalOperator = Field(default=LogicalOperator.AND, description="逻辑运算符")
    conditions: list[ScreeningCondition] = Field(default_factory=list, description="条件列表")


class ScreeningCriteria(BaseModel):
    """用户自定义选股筛选规则"""
    rules: list[ScreeningRule] = Field(default_factory=list, description="规则列表")
    top_n: int = Field(default=10, ge=1, le=500, description="返回数量限制")


class WalkForwardWindowDTO(BaseModel):
    """A single walk-forward window."""
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    train_return: float = 0.0
    test_return: float = 0.0
    params: dict[str, float] = Field(default_factory=dict)


class WalkForwardResultDTO(BaseModel):
    """Result of walk-forward optimization."""
    strategy_name: str
    symbol: str
    param_space: dict[str, list[float]] = Field(default_factory=dict)
    optimal_params: dict[str, float] = Field(default_factory=dict)
    windows: list[WalkForwardWindowDTO] = Field(default_factory=list)
    avg_train_return: float = 0.0
    avg_test_return: float = 0.0
    in_sample_score: float = 0.0
    out_sample_score: float = 0.0
    stability_score: float = 0.0
    conclusion: str = ""
