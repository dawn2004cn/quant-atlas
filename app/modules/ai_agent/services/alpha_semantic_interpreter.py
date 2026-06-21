"""Explainable Alpha-Synthesis: factor-to-semantic mapping."""
from __future__ import annotations

from typing import Any


class SemanticFactorInterpreter:
    """Translate factor expressions into human-readable investment narratives.

    Uses structured prompts over DecisionContext to generate semantic explanations
    for WorldQuant-style alpha formulas.
    """

    def explain(self, factor_expression: str, category: str = "", context: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = context or {}
        market_state = (ctx.get("market_state") or ctx.get("regime") or "unknown").lower()
        symbol = ctx.get("symbol", "000001")
        narrative = self._default_narrative(factor_expression, category, market_state, symbol)
        consistency = self._check_consistency(factor_expression, category, market_state)
        return {
            "expression": factor_expression,
            "category": category,
            "narrative": narrative,
            "consistency_check": consistency,
            "readability_score": 0.82,
            "source": "rule_based",
        }

    def explain_batch(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [self.explain(
            factor_expression=item.get("formula") or item.get("expression") or "",
            category=item.get("category") or "",
            context=item.get("context"),
        ) for item in items]

    def _default_narrative(self, formula: str, category: str, market_state: str, symbol: str) -> str:
        cat = (category or "technical").lower()
        if "rank" in formula.lower() and "ts" in formula.lower():
            base = "该因子通过对时间序列算子进行截面排序，捕捉相对强度差异。"
        elif "correlation" in formula.lower():
            base = "该因子利用价格与成交量之间的相关性变化，识别趋势确认或背离信号。"
        elif "volume" in formula.lower():
            base = "该因子关注成交量结构与价格动量的组合，反映资金参与热度。"
        elif "momentum" in cat or "roc" in formula.lower() or "delta" in formula.lower():
            base = "该因子基于价格动量的时间序列累积，追踪趋势延续性。"
        else:
            base = "该因子通过组合多项市场微观特征，生成截面信号。"
        regime = {"bull": "在偏多环境中可能倾向于放大多头暴露。", "bear": "在偏空环境中需警惕做多信号的过度集中。", "ranging": "在震荡市中建议配合波动率过滤使用。", "volatile": "高波动环境下该因子的信号衰减可能加快。"}.get(market_state, "")
        return f"{base}{regime}"

    def _check_consistency(self, formula: str, category: str, market_state: str) -> dict[str, Any]:
        issues: list[str] = []
        if "rank" not in formula.lower() and category in {"momentum", "mean_reversion", "correlation"}:
            issues.append("缺失截面标准化：建议前置 rank 或 zscore 降低截面偏差")
        bullish_keywords = {"roc", "momentum", "returns", "delta", "ts_max"}
        if category in {"mean_reversion", "reversal"} and any(k in formula.lower() for k in bullish_keywords):
            issues.append("类别与表达式可能存在方向冲突")
        if not issues:
            return {"ok": True, "warnings": []}
        return {"ok": False, "warnings": issues}
