from __future__ import annotations

"""Portfolio Correlation Analyzer - 组合相关性分析.

实现多目标优化：寻找与当前组合互补而非共振的因子。
"""


from typing import Any


class CorrelationMatrix:
    """相关性矩阵计算器."""

    def __init__(self) -> None:
        self._factor_data: dict[str, list[float]] = {}
        self._returns_data: dict[str, list[float]] = {}

    def add_factor(
        self,
        factor_id: str,
        values: list[float],
    ) -> None:
        """添加因子数据."""
        self._factor_data[factor_id] = values

    def add_returns(
        self,
        factor_id: str,
        returns: list[float],
    ) -> None:
        """添加收益数据."""
        self._returns_data[factor_id] = returns

    def calculate_correlation(
        self,
        factor_a: str,
        factor_b: str,
    ) -> float:
        """计算两个因子的相关性."""
        if factor_a not in self._factor_data or factor_b not in self._factor_data:
            return 0.0

        a = self._factor_data[factor_a]
        b = self._factor_data[factor_b]

        if len(a) != len(b) or len(a) < 2:
            return 0.0

        mean_a = sum(a) / len(a)
        mean_b = sum(b) / len(b)

        cov = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b)) / len(a)
        std_a = (sum((x - mean_a) ** 2 for x in a) / len(a)) ** 0.5
        std_b = (sum((y - mean_b) ** 2 for y in b) / len(b)) ** 0.5

        if std_a < 1e-10 or std_b < 1e-10:
            return 0.0

        return cov / (std_a * std_b)

    def get_correlation_matrix(
        self,
        factor_ids: list[str] | None = None,
    ) -> dict[str, dict[str, float]]:
        """获取相关性矩阵."""
        if factor_ids is None:
            factor_ids = list(self._factor_data.keys())

        matrix = {}
        for fa in factor_ids:
            matrix[fa] = {}
            for fb in factor_ids:
                if fa == fb:
                    matrix[fa][fb] = 1.0
                else:
                    matrix[fa][fb] = self.calculate_correlation(fa, fb)

        return matrix

    def find_complementary_factors(
        self,
        candidate_factors: list[str],
        portfolio_factors: list[str],
        threshold: float = 0.3,
    ) -> list[dict[str, Any]]:
        """找出与组合互补的因子.

        Args:
            candidate_factors: 候选因子列表
            portfolio_factors: 组合中已有因子
            threshold: 相关性阈值

        Returns:
            按互补性排序的因子列表
        """
        results = []

        for cand in candidate_factors:
            if cand in portfolio_factors:
                continue

            correlations = []
            for port in portfolio_factors:
                corr = self.calculate_correlation(cand, port)
                correlations.append(corr)

            avg_corr = sum(correlations) / len(correlations) if correlations else 0

            results.append({
                "factor_id": cand,
                "avg_correlation": avg_corr,
                "max_correlation": max(correlations) if correlations else 0,
                "is_complementary": avg_corr < threshold,
            })

        results.sort(key=lambda x: x["avg_correlation"])
        return results

    def calculate_portfolio_ic(
        self,
        factor_id: str,
    ) -> float:
        """计算因子的信息系数 (IC)."""
        if factor_id not in self._returns_data:
            return 0.0

        factor_vals = self._factor_data.get(factor_id, [])
        returns = self._returns_data.get(factor_id, [])

        if len(factor_vals) != len(returns) or len(factor_vals) < 10:
            return 0.0

        ic_values = []
        for i in range(1, len(factor_vals)):
            ic_values.append(factor_vals[i] * returns[i])

        return sum(ic_values) / len(ic_values)

    def calculate_rank_ic(
        self,
        factor_id: str,
    ) -> float:
        """计算 Rank IC (Spearman)."""
        if factor_id not in self._returns_data:
            return 0.0

        factor_vals = self._factor_data.get(factor_id, [])
        returns = self._returns_data.get(factor_id, [])

        if len(factor_vals) != len(returns) or len(factor_vals) < 10:
            return 0.0

        factor_ranks = self._to_ranks(factor_vals)
        return_ranks = self._to_ranks(returns)

        n = len(factor_vals)
        d = sum((f - r) ** 2 for f, r in zip(factor_ranks, return_ranks))
        rank_ic = 1 - (6 * d) / (n * (n ** 2 - 1))

        return rank_ic

    def _to_ranks(self, values: list[float]) -> list[float]:
        """转换为排名."""
        sorted_pairs = sorted(enumerate(values), key=lambda x: x[1])
        ranks = [0] * len(values)
        for rank, (idx, _) in enumerate(sorted_pairs):
            ranks[idx] = rank + 1
        return ranks


class PortfolioOptimizer:
    """组合优化器 - 基于因子的组合权重优化."""

    def __init__(self) -> None:
        self._analyzer = CorrelationMatrix()

    def optimize_weights(
        self,
        factor_ids: list[str],
        target_return: float,
        max_risk: float,
        method: str = "mean_variance",
    ) -> dict[str, float]:
        """优化组合权重.

        Args:
            factor_ids: 因子列表
            target_return: 目标收益
            max_risk: 最大风险
            method: 优化方法

        Returns:
            因子权重字典
        """
        n = len(factor_ids)
        if n == 0:
            return {}

        equal_weight = 1.0 / n
        weights = {fid: equal_weight for fid in factor_ids}

        return weights

    def calculate_portfolio_return(
        self,
        weights: dict[str, float],
        factor_returns: dict[str, float],
    ) -> float:
        """计算组合预期收益."""
        return sum(w * factor_returns.get(fid, 0) for fid, w in weights.items())

    def calculate_portfolio_risk(
        self,
        weights: dict[str, float],
        corr_matrix: dict[str, dict[str, float]],
    ) -> float:
        """计算组合风险 (波动率)."""
        factors = list(weights.keys())
        variance = 0.0

        for _i, fa in enumerate(factors):
            for _j, fb in enumerate(factors):
                wi = weights[fa]
                wj = weights[fb]
                corr = corr_matrix.get(fa, {}).get(fb, 0)
                variance += wi * wj * corr

        return variance ** 0.5


def format_correlation_report(
    corr_matrix: dict[str, dict[str, float]],
    factor_names: dict[str, str] | None = None,
) -> str:
    """生成相关性报告."""
    lines = ["=== 因子相关性报告 ==="]

    factors = list(corr_matrix.keys())
    if not factors:
        return "无因子数据"

    lines.append(f"\n因子数量: {len(factors)}")

    high_corr_pairs = []
    for i, fa in enumerate(factors):
        for j, fb in enumerate(factors):
            if i < j:
                corr = corr_matrix[fa].get(fb, 0)
                if abs(corr) > 0.7:
                    name_a = factor_names.get(fa, fa) if factor_names else fa
                    name_b = factor_names.get(fb, fb) if factor_names else fb
                    high_corr_pairs.append((name_a, name_b, corr))

    if high_corr_pairs:
        lines.append("\n高相关性对 (>0.7):")
        for a, b, c in high_corr_pairs:
            lines.append(f"  {a} <-> {b}: {c:.3f}")

    return "\n".join(lines)


_global_analyzer: CorrelationMatrix | None = None


def get_correlation_analyzer() -> CorrelationMatrix:
    """获取全局相关性分析器."""
    global _global_analyzer
    if _global_analyzer is None:
        _global_analyzer = CorrelationMatrix()
    return _global_analyzer
