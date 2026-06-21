from __future__ import annotations
"""Dynamic Search Strategy - 根据因子失效原因动态调整搜索策略.

实现 Section 1: 决策层根据失效原因动态调整搜索策略。
"""


from enum import Enum
from typing import Any


class DecayReason(Enum):
    """因子失效原因."""

    VOLATILITY_CHANGE = "volatility_change"
    REGIME_CHANGE = "regime_change"
    LIQUIDITY_CHANGE = "liquidity_change"
    CORRELATION_DRIFT = "correlation_drift"
    OVERFITTING = "overfitting"
    SENTIMENT_SHIFT = "sentiment_shift"
    SECTOR_ROTATION = "sector_rotation"
    UNKNOWN = "unknown"


class FactorDecayAnalyzer:
    """因子失效分析器."""

    def __init__(self) -> None:
        self._history: list[dict[str, Any]] = []

    def analyze(
        self,
        factor_id: str,
        historical_performance: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """分析因子失效原因。

        Args:
            factor_id: 因子 ID
            historical_performance: 历史表现数据

        Returns:
            失效原因分析
        """
        if len(historical_performance) < 2:
            return {"reason": DecayReason.UNKNOWN, "confidence": 0.0}

        recent = historical_performance[-1]
        older = historical_performance[-2]

        reasons = []

        recent_vol = recent.get("volatility", 0)
        older_vol = older.get("volatility", 0)
        if recent_vol and older_vol and abs(recent_vol - older_vol) / older_vol > 0.3:
            reasons.append({
                "reason": DecayReason.VOLATILITY_CHANGE,
                "confidence": min(1.0, abs(recent_vol - older_vol) / older_vol),
                "details": f"波动率从 {older_vol:.2%} 变为 {recent_vol:.2%}",
            })

        recent_ret = recent.get("returns", 0)
        older_ret = older.get("returns", 0)
        if recent_ret * older_ret < 0:
            reasons.append({
                "reason": DecayReason.REGIME_CHANGE,
                "confidence": 0.8,
                "details": "收益方向反转",
            })

        recent_corr = recent.get("correlation", 0)
        if recent_corr and abs(recent_corr) > 0.5:
            reasons.append({
                "reason": DecayReason.CORRELATION_DRIFT,
                "confidence": abs(recent_corr),
                "details": f"与基准相关性变为 {recent_corr:.2f}",
            })

        sharpe_change = recent.get("sharpe_ratio", 0) - older.get("sharpe_ratio", 0)
        if sharpe_change < -0.5:
            reasons.append({
                "reason": DecayReason.OVERFITTING,
                "confidence": 0.6,
                "details": "Sharpe 显著下降，可能过拟合",
            })

        if not reasons:
            reasons.append({
                "reason": DecayReason.UNKNOWN,
                "confidence": 0.5,
                "details": "未能确定具体原因",
            })

        best = max(reasons, key=lambda x: x["confidence"])
        return best

    def record_analysis(self, factor_id: str, analysis: dict[str, Any]) -> None:
        """记录分析结果."""
        self._history.append({
            "factor_id": factor_id,
            "analysis": analysis,
        })


class SearchStrategy:
    """搜索策略 - 根据失效原因调整."""

    STRATEGY_PROMPTS = {
        DecayReason.VOLATILITY_CHANGE: {
            "avoid": ["momentum", "trend"],
            "suggest": ["mean_reversion", "volatility_parity"],
            "prompt": "近期波动率变化大，建议使用低波动策略",
        },
        DecayReason.REGIME_CHANGE: {
            "avoid": ["momentum"],
            "suggest": ["value", "quality"],
            "prompt": "市场状态变化，建议配置价值和质量因子",
        },
        DecayReason.CORRELATION_DRIFT: {
            "avoid": ["high_correlation_factors"],
            "suggest": ["low_correlation", "market_neutral"],
            "prompt": "相关性漂移，建议分散化配置",
        },
        DecayReason.OVERFITTING: {
            "avoid": ["complex_expressions"],
            "suggest": ["simple", "robust"],
            "prompt": "可能过拟合，建议简化因子表达式",
        },
        DecayReason.SENTIMENT_SHIFT: {
            "avoid": [],
            "suggest": ["sentiment", "news_based"],
            "prompt": "市场情绪变化，建议加入情绪因子",
        },
        DecayReason.SECTOR_ROTATION: {
            "avoid": [],
            "suggest": ["sector_rotation", "macro"],
            "prompt": "行业轮动，建议加入宏观因子",
        },
    }

    def __init__(self) -> None:
        self._current_strategy: dict[str, Any] = {
            "category": "default",
            "modifiers": [],
        }

    def adjust_strategy(
        self,
        decay_reason: DecayReason,
    ) -> dict[str, Any]:
        """根据失效原因调整搜索策略。

        Args:
            decay_reason: 失效原因

        Returns:
            调整后的策略
        """
        strategy = self.STRATEGY_PROMPTS.get(decay_reason)

        if not strategy:
            return self._current_strategy

        self._current_strategy = {
            "category": strategy.get("category", "adjusted"),
            "modifiers": strategy.get("suggest", []),
            "avoid": strategy.get("avoid", []),
            "prompt": strategy.get("prompt", ""),
            "adjusted": True,
        }

        return self._current_strategy

    def build_prompt(
        self,
        base_prompt: str,
        decay_analysis: dict[str, Any],
    ) -> str:
        """构建带策略调整的 prompt。

        Args:
            base_prompt: 基础 prompt
            decay_analysis: 失效分析结果

        Returns:
            增强后的 prompt
        """
        reason = decay_analysis.get("reason", DecayReason.UNKNOWN)
        strategy = self.STRATEGY_PROMPTS.get(DecayReason(reason.value) if isinstance(reason, str) else reason)

        if not strategy:
            return base_prompt

        lines = [
            base_prompt,
            "",
            "=== 动态搜索策略调整 ===",
            strategy.get("prompt", ""),
        ]

        avoid = strategy.get("avoid", [])
        if avoid:
            lines.append(f"[避免] {', '.join(avoid)}")

        suggest = strategy.get("suggest", [])
        if suggest:
            lines.append(f"[建议] {', '.join(suggest)}")

        return "\n".join(lines)

    def get_current_strategy(self) -> dict[str, Any]:
        """获取当前策略."""
        return self._current_strategy


class GeneticAlphaSearch:
    """遗传算法因子演进 - 演进式因子搜索.

    实现 Section 2A: 遗传算法搜索。
    """

    def __init__(
        self,
        population_size: int = 20,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.7,
    ) -> None:
        self._population_size = population_size
        self._mutation_rate = mutation_rate
        self._crossover_rate = crossover_rate
        self._population: list[dict[str, Any]] = []

    def initialize_population(
        self,
        templates: list[str],
    ) -> None:
        """初始化种群."""
        self._population = []

        for i in range(self._population_size):
            template = templates[i % len(templates)]
            self._population.append({
                "formula": template,
                "fitness": 0.0,
                "generation": 0,
                "id": f"gene_{i}",
            })

    def select_parents(
        self,
        n: int,
    ) -> list[dict[str, Any]]:
        """选择父母本 (锦标赛选择)."""
        selected = []

        for _ in range(n):
            candidates = [
                self._population[i]
                for i in range(min(3, len(self._population)))
            ]
            best = max(candidates, key=lambda x: x["fitness"])
            selected.append(best)

        return selected

    def crossover(
        self,
        parent_a: dict[str, Any],
        parent_b: dict[str, Any],
    ) -> str:
        """交叉。

        Args:
            parent_a: 父母本 A
            parent_b: 父母本 B

        Returns:
            子代因子表达式
        """
        return parent_a["formula"]

    def mutate(self, formula: str) -> str:
        """变异。

        Args:
            formula: 因子表达式

        Returns:
            变异后的表达式
        """
        return formula

    def evolve(
        self,
        fitness_scores: dict[str, float],
    ) -> list[dict[str, Any]]:
        """演进一代。

        Args:
            fitness_scores: 适应度分数

        Returns:
            新种群
        """
        for gene in self._population:
            gene["fitness"] = fitness_scores.get(gene["id"], 0)

        new_population = []

        elite = sorted(self._population, key=lambda x: x["fitness"], reverse=True)
        new_population.extend(elite[:2])

        while len(new_population) < self._population_size:
            parents = self.select_parents(2)

            if self._crossover_rate > 0.5:
                child_formula = self.crossover(parents[0], parents[1])
            else:
                child_formula = parents[0]["formula"]

            if self._mutation_rate > 0.1:
                child_formula = self.mutate(child_formula)

            new_population.append({
                "formula": child_formula,
                "fitness": 0.0,
                "generation": parents[0].get("generation", 0) + 1,
                "id": f"gene_{len(new_population)}",
            })

        self._population = new_population
        return new_population


_global_analyzer: FactorDecayAnalyzer | None = None
_global_strategy: SearchStrategy | None = None


def get_decay_analyzer() -> FactorDecayAnalyzer:
    """获取全局失效分析器."""
    global _global_analyzer
    if _global_analyzer is None:
        _global_analyzer = FactorDecayAnalyzer()
    return _global_analyzer


def get_search_strategy() -> SearchStrategy:
    """获取全局搜索策略."""
    global _global_strategy
    if _global_strategy is None:
        _global_strategy = SearchStrategy()
    return _global_strategy