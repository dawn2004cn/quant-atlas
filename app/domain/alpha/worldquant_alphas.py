from __future__ import annotations
"""WorldQuant 101 Alpha Factors knowledge base for rd-agent guidance.

提供 101 Classic Alphas 作为 rd-agent 生成因子的知识引导。
参考: https://www.worldquant.com/alphas/
"""


from typing import Any


ALPHA_CATEGORIES = {
    "momentum": "动量因子",
    "mean_reversion": "均值回归",
    "volume": "成交量因子",
    "volatility": "波动率因子",
    "correlation": "相关性因子",
    "fundamental": "基本面因子",
    "rank": "排序因子",
    "time_series": "时间序列因子",
}


ALPHA_EXAMPLES = [
    {
        "id": "alpha_001",
        "name": "Rank Correlation",
        "formula": "rank(Ts_ArgMax(SUMS(returns_0_1, 20), 2))",
        "category": "momentum",
        "description": "Returns the rank of the correlation between the volume and returns over the past 20 days, capped at 2",
    },
    {
        "id": "alpha_002",
        "name": "Log Volume Weighted",
        "formula": "rank(Ts_ArgMax(SignedPower(Ts_Skewness(returns_0_1, 30), 2.5), 3))",
        "category": "momentum",
        "description": "Calculate the skewness of returns over 30 days, raise to power 2.5, find argmax over 3 days, take rank",
    },
    {
        "id": "alpha_003",
        "name": "Tick Size Sensitive",
        "formula": "rank(Ts_ArgMax(Ts_ResInd(close_0, Ts_Max(close_0, 30)), 4))",
        "category": "momentum",
        "description": "Residual indicator based on max close in 30 days, find argmax over 4 days, take rank",
    },
    {
        "id": "alpha_004",
        "name": "Market Breadth",
        "formula": "rank(Ts_ArgMax(Ts_Correlation(close_0, volume_0, 10), 5))",
        "category": "correlation",
        "description": "Correlation between close and volume over 10 days, argmax over 5 days, rank",
    },
    {
        "id": "alpha_005",
        "name": "Price-Volume Trend",
        "formula": "rank(Ts_ArgMax(Ts_Sum(Ts_Delay(volume_0, 10), 2) / Ts_Sum(Ts_Delay(volume_0, 1), 2), 1))",
        "category": "volume",
        "description": "Volume ratio with 10-day delay, rolling sum over 2 days, argmax over 1 day, rank",
    },
    {
        "id": "alpha_006",
        "name": "Oscillator",
        "formula": "rank(Ts_Skewness(returns_0_1, 20))",
        "category": "volatility",
        "description": "20-day skewness of returns",
    },
    {
        "id": "alpha_007",
        "name": "Volume Oscillator",
        "formula": "rank(Ts_Skewness(Ts_Delta(Ts_Ln(volume_0), 2), 20))",
        "category": "volume",
        "description": "20-day skewness of log volume differences",
    },
    {
        "id": "alpha_008",
        "name": "Mean Reversion",
        "formula": "rank(Ts_Decay_Array(Ts_ArgMax(rank(close_0), 10), 4))",
        "category": "mean_reversion",
        "description": "Rank of close, argmax over 10 days, decay array over 4 days",
    },
    {
        "id": "alpha_009",
        "name": "Liquidity",
        "formula": "rank(Ts_Delta(Ts_Sum(Ts_Mean(volume_0, 5) / Ts_Mean(volume_0, 120), 3), 1))",
        "category": "volume",
        "description": "5-day to 120-day volume ratio, sum over 3 days, delta over 1 day, rank",
    },
    {
        "id": "alpha_010",
        "name": "Price Normalization",
        "formula": "rank(Ts_Decay_Array(Ts_Delta(Ts_Ln(volume_0), 2), 20))",
        "category": "volume",
        "description": "Log volume delta over 2 days, decay over 20 days, rank",
    },
    {
        "id": "alpha_011",
        "name": "Relative Strength",
        "formula": "rank(Ts_Mean(correlation(close_0, volume_0, 10), 3))",
        "category": "correlation",
        "description": "10-day correlation between close and volume, mean over 3 days, rank",
    },
    {
        "id": "alpha_012",
        "name": "Volume Momentum",
        "formula": "rank(Ts_Mean(correlation(Ts_Delta(Ts_Ln(volume_0), 2), returns_0_1, 6), 3))",
        "category": "momentum",
        "description": "Log volume delta correlation with returns over 6 days, mean over 3 days, rank",
    },
    {
        "id": "alpha_013",
        "name": "Decay Momentum",
        "formula": "rank(Ts_Decay_Sequential(Ts_Max(Ts_Delta(close_0, 1), 5), 5, 3))",
        "category": "momentum",
        "description": "5-day max close delta, sequential decay over 5 days, 3 periods, rank",
    },
    {
        "id": "alpha_014",
        "name": "Volume Price Trend",
        "formula": "rank(Ts_Decay_Ranked(Ts_Delta(Ts_Ln(returns_0_1), 3), 10))",
        "category": "momentum",
        "description": "Log returns delta over 3 days, decay rank over 10 days",
    },
    {
        "id": "alpha_015",
        "name": "High-Low Range",
        "formula": "rank(Ts_Delta(Ts_Sum(close_0, 20) / Ts_Sum(Ts_Delay(close_0, 20), 20) - 1, 1))",
        "category": "momentum",
        "description": "20-day sum ratio, compare with 20-day delayed, delta over 1 day",
    },
    {
        "id": "alpha_016",
        "name": "Price Acceleration",
        "formula": "rank(Ts_Delta(Ts_Sum(close_0, 20) / Ts_Sum(Ts_Delay(close_0, 20), 20) - 1, 1) - Ts_Delta(Ts_Sum(close_0, 10) / Ts_Sum(Ts_Delay(close_0, 10), 10) - 1, 1))",
        "category": "momentum",
        "description": "20-day momentum minus 10-day momentum",
    },
    {
        "id": "alpha_017",
        "name": "Volatility Ratio",
        "formula": "rank(Ts_Delta(Ts_Sum(ts_mean(returns_0_1, 30), 2) / ts_stddev(returns_0_1, 30), 1))",
        "category": "volatility",
        "description": "Mean returns over stddev, 30-day window, ratio, delta",
    },
    {
        "id": "alpha_018",
        "name": "Cross Asset Momentum",
        "formula": "rank(correlation(Ts_Delta(Ts_Ln(volume_0), 1), ts_mean(returns_0_1, 10), 10))",
        "category": "correlation",
        "description": "Log volume delta correlation with 10-day mean returns",
    },
    {
        "id": "alpha_019",
        "name": "Lead-Lag Effect",
        "formula": "rank(Ts_Covariance(Ts_Delta(Ts_Ln(volume_0), 2), ts_mean(returns_0_1, 3), 30))",
        "category": "correlation",
        "description": "Covariance between log volume delta and 3-day mean returns, 30-day window",
    },
    {
        "id": "alpha_020",
        "name": "Trend Strength",
        "formula": "rank(Ts_Sum(returns_0_1, 30) / (Ts_Sum(abs(ts_delta(returns_0_1, 1)), 30) + 1e-10))",
        "category": "momentum",
        "description": "Mean returns over 30 days divided by sum of absolute returns",
    },
]


ALPHA_OPERATORS = {
    "ts_sum": {"arity": 2, "description": "Rolling sum over N periods"},
    "ts_mean": {"arity": 2, "description": "Rolling mean over N periods"},
    "ts_stddev": {"arity": 2, "description": "Rolling standard deviation over N periods"},
    "ts_covariance": {"arity": 3, "description": "Rolling covariance over N periods"},
    "ts_correlation": {"arity": 3, "description": "Rolling correlation over N periods"},
    "ts_max": {"arity": 2, "description": "Rolling maximum over N periods"},
    "ts_min": {"arity": 2, "description": "Rolling minimum over N periods"},
    "ts_argmax": {"arity": 2, "description": "Index of rolling maximum over N periods"},
    "ts_argmin": {"arity": 2, "description": "Index of rolling minimum over N periods"},
    "ts_delta": {"arity": 2, "description": "Difference over N periods"},
    "ts_skewness": {"arity": 2, "description": "Rolling skewness over N periods"},
    "ts_kurtosis": {"arity": 2, "description": "Rolling kurtosis over N periods"},
    "ts_rank": {"arity": 1, "description": "Rolling rank"},
    "ts_quantile": {"arity": 2, "description": "Rolling quantile"},
    "ts_decay_linear": {"arity": 2, "description": "Linear decay over N periods"},
    "ts_decay_exponential": {"arity": 2, "description": "Exponential decay over N periods"},
    "ts_zscore": {"arity": 1, "description": "Rolling z-score"},
    "ts_residual": {"arity": 2, "description": "Residual after regression"},
    "rank": {"arity": 1, "description": "Cross-sectional rank"},
    "delay": {"arity": 2, "description": "Time shift by N periods"},
    "delta": {"arity": 2, "description": "Difference over N periods"},
    "signed_power": {"arity": 2, "description": "Signed power (handles negative values)"},
    "signed_log": {"arity": 1, "description": "Signed log (handles negative values)"},
    "log": {"arity": 1, "description": "Natural logarithm"},
    "abs": {"arity": 1, "description": "Absolute value"},
    "sqrt": {"arity": 1, "description": "Square root"},
    "sign": {"arity": 1, "description": "Sign of value (-1, 0, 1)"},
    "regression": {"arity": 2, "description": "Linear regression coefficient"},
}


ALPHA_TEMPLATES = {
    "momentum": [
        "rank(ts_sum(returns_0_1, {window}) / ts_sum(abs(ts_delta(returns_0_1, 1)), {window}))",
        "rank(ts_delta(ts_mean(close_0, {window}) / ts_mean(ts_delay(close_0, {window}), {window}) - 1, 1))",
        "rank(ts_decay_linear(ts_delta(close_0, {window}), {decay}))",
    ],
    "mean_reversion": [
        "rank(ts_mean(correlation(close_0, volume_0, {window}), {mean_window}))",
        "rank(-ts_sum(returns_0_1, {window}) / (ts_sum(abs(ts_delta(returns_0_1, 1)), {window}) + 1e-10))",
    ],
    "volatility": [
        "rank(ts_stddev(returns_0_1, {window}) / ts_mean(abs(returns_0_1), {window}))",
        "rank(ts_skewness(returns_0_1, {window}))",
    ],
    "volume": [
        "rank(ts_delta(ts_mean(volume_0, {short}) / ts_mean(volume_0, {long}), 1))",
        "rank(ts_correlation(ts_delta(ts_log(volume_0), 1), ts_mean(returns_0_1, {window}), {window}))",
    ],
}


class WorldQuantKnowledge:
    """WorldQuant 101 Alphas 知识库封装类."""

    def __init__(self):
        self.alphas = ALPHA_EXAMPLES
        self.operators = ALPHA_OPERATORS
        self.templates = ALPHA_TEMPLATES
        self.categories = ALPHA_CATEGORIES

    def get_alpha(self, alpha_id: str) -> dict[str, Any] | None:
        """根据 ID 获取 alpha 因子."""
        for a in self.alphas:
            if a["id"] == alpha_id:
                return a
        return None

    def search(self, keyword: str) -> list[dict[str, Any]]:
        """搜索 alpha."""
        return get_alpha_by_keyword(keyword)

    def get_by_category(self, category: str) -> list[dict[str, Any]]:
        """获取类别的所有 alpha."""
        return get_alpha_by_category(category)


def get_alpha_by_category(category: str) -> list[dict[str, Any]]:
    """Get all alpha examples for a given category."""
    return [a for a in ALPHA_EXAMPLES if a["category"] == category]


def get_alpha_by_keyword(keyword: str) -> list[dict[str, Any]]:
    """Search alphas by keyword in formula or description."""
    keyword = keyword.lower()
    return [
        a for a in ALPHA_EXAMPLES
        if keyword in a["formula"].lower() or keyword in a["description"].lower()
    ]


def get_random_alpha_template(category: str = "momentum") -> str:
    """Get a random alpha template for a category."""
    import random
    templates = ALPHA_TEMPLATES.get(category, ALPHA_TEMPLATES["momentum"])
    return random.choice(templates)


def format_alpha_prompt(
    category: str | None = None,
    include_examples: int = 3,
    forbid_duplicate: bool = True,
) -> str:
    """Format WorldQuant 101 Alphas knowledge for rd-agent prompt.

    Args:
        category: Filter by category (momentum, mean_reversion, etc)
        include_examples: Number of examples to include
        forbid_duplicate: Whether to mention avoiding duplicates
    """
    lines = ["=== WorldQuant 101 Alphas Knowledge ==="]

    if forbid_duplicate:
        lines.append("\n[IMPORTANT] Avoid generating duplicate alphas already in Factor Vault.")

    lines.append("\n--- Core Operators ---")
    for op, info in ALPHA_OPERATORS.items():
        lines.append(f"- {op}({info['description']})")

    alphas = ALPHA_EXAMPLES
    if category:
        alphas = get_alpha_by_category(category)

    lines.append(f"\n--- Example Alphas ({len(alphas)}) ---")
    for a in alphas[:include_examples]:
        lines.append(f"- {a['id']}: {a['formula']}")

    lines.append("\n--- Template Patterns ---")
    for cat, templates in ALPHA_TEMPLATES.items():
        lines.append(f"\n[{ALPHA_CATEGORIES.get(cat, cat)}]")
        for t in templates[:2]:
            lines.append(f"  {t}")

    return "\n".join(lines)


def get_complementary_objective_prompt(current_portfolio_formulas: list[str]) -> str:
    """Generate prompt for finding alphas complementary to current portfolio.

    This implements the "Low Correlation with Current Portfolio" optimization.
    """
    lines = [
        "\n=== Multi-Objective Optimization ===",
        "[GOAL] Find alphas that COMPLEMENT (not correlate with) current portfolio.",
    ]

    if current_portfolio_formulas:
        lines.append("\nCurrent portfolio formulas:")
        for i, f in enumerate(current_portfolio_formulas[:5], 1):
            lines.append(f"  {i}. {f}")

        lines.append("\n[STRATEGY]")
        lines.append("- Avoid: High correlation with existing portfolio (resonance)")
        lines.append("- Seek: Low/negative correlation with portfolio (diversification)")
        lines.append("- Optimize for: alpha_return / (portfolio_correlation + 0.01)")
    else:
        lines.append("\n[STRATEGY]")
        lines.append("- No portfolio constraints - optimize for Sharpe ratio")

    return "\n".join(lines)
