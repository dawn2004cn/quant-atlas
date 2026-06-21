from __future__ import annotations
"""Meta-Learner: 自动选择最优模型 (大盘股/小盘股/数字货币).

This implements Section 2C from the roadmap:
- Meta-Learner: 根据标的类型自动选择模型
- 大盘股: 线性模型 (强解释性)
- 小盘股/数字货币: GRU/Transformer (捕捉非线性)
- 增量学习: Warm Start 增量训练
"""


from enum import Enum
from typing import Any


class ModelType(Enum):
    """可用的模型类型."""

    LINEAR = "linear"
    LIGHTGBM = "lightgbm"
    XGBOOST = "xgboost"
    GRU = "gru"
    TRANSFORMER = "transformer"
    RANDOM_FOREST = "random_forest"


class MarketCapTier(Enum):
    """市值层级."""

    LARGE = "large"  # > 500亿
    MID = "mid"  # 50-500亿
    SMALL = "small"  # < 50亿
    CRYPTO = "crypto"


MODEL_SELECTION_RULES = {
    MarketCapTier.LARGE: {
        "recommended": [ModelType.LINEAR, ModelType.LIGHTGBM],
        "fallback": [ModelType.LIGHTGBM],
        "rationale": "大盘股流动性好，线性模型解释性强",
    },
    MarketCapTier.MID: {
        "recommended": [ModelType.LIGHTGBM, ModelType.XGBOOST],
        "fallback": [ModelType.LIGHTGBM],
        "rationale": "中盘股需要一定非线性能力",
    },
    MarketCapTier.SMALL: {
        "recommended": [ModelType.XGBOOST, ModelType.GRU],
        "fallback": [ModelType.LIGHTGBM],
        "rationale": "小盘股波动大，需要强非线性模型",
    },
    MarketCapTier.CRYPTO: {
        "recommended": [ModelType.GRU, ModelType.TRANSFORMER],
        "fallback": [ModelType.XGBOOST],
        "rationale": "数字货币24/7交易，需要时序模型",
    },
}


MODEL_CONFIG_TEMPLATES = {
    ModelType.LINEAR: {
        "model_type": "linear",
        "params": {
            "fit_intercept": True,
            "positive": False,
            "alpha": 0.1,
        },
        "max_train_days": 250,
    },
    ModelType.LIGHTGBM: {
        "model_type": "lightgbm",
        "params": {
            "n_estimators": 100,
            "max_depth": 6,
            "learning_rate": 0.05,
            "num_leaves": 31,
            "min_child_samples": 20,
        },
        "max_train_days": 500,
    },
    ModelType.XGBOOST: {
        "model_type": "xgboost",
        "params": {
            "n_estimators": 100,
            "max_depth": 6,
            "learning_rate": 0.05,
            "subsample": 0.8,
        },
        "max_train_days": 500,
    },
    ModelType.GRU: {
        "model_type": "gru",
        "params": {
            "hidden_size": 64,
            "num_layers": 2,
            "dropout": 0.2,
            "learning_rate": 0.001,
        },
        "sequence_length": 20,
        "max_train_days": 1000,
    },
    ModelType.TRANSFORMER: {
        "model_type": "transformer",
        "params": {
            "d_model": 64,
            "nhead": 4,
            "num_layers": 2,
            "dropout": 0.2,
            "learning_rate": 0.0005,
        },
        "sequence_length": 20,
        "max_train_days": 1500,
    },
}


def infer_market_cap_tier(symbol: str, market_cap: float | None = None) -> MarketCapTier:
    """根据代码和市场cap推断市值层级.

    Args:
        symbol: 股���代码
        market_cap: 市值（单位：亿）

    Returns:
        MarketCapTier
    """
    if market_cap is not None:
        if market_cap > 500:
            return MarketCapTier.LARGE
        if market_cap > 50:
            return MarketCapTier.MID
        return MarketCapTier.SMALL

    if symbol.startswith(("688", "600")):
        return MarketCapTier.LARGE
    if symbol.startswith(("000", "002", "300")):
        return MarketCapTier.MID
    if symbol.startswith(("8", "4")):
        return MarketCapTier.CRYPTO

    return MarketCapTier.MID


def select_model(
    symbol: str | None = None,
    market_cap: float | None = None,
    prefer_explainability: bool = False,
) -> tuple[ModelType, dict[str, Any]]:
    """自动选择最优模型.

    Args:
        symbol: 股票代码
        market_cap: 市值（亿）
        prefer_explainability: 是否优先可解释性

    Returns:
        (ModelType, model_config)
    """
    tier = infer_market_cap_tier(symbol or "", market_cap)

    if prefer_explainability and tier != MarketCapTier.CRYPTO:
        return ModelType.LINEAR, MODEL_CONFIG_TEMPLATES[ModelType.LINEAR].copy()

    rule = MODEL_SELECTION_RULES[tier]
    primary = rule["recommended"][0]
    config = MODEL_CONFIG_TEMPLATES[primary].copy()

    return primary, config


def get_warm_start_config(
    model_type: ModelType,
    previous_model_path: str | None = None,
) -> dict[str, Any]:
    """获取增量学习/热启动配置.

    Args:
        model_type: 模型类型
        previous_model_path: 上一个模型路径

    Returns:
        热启动配置
    """
    config = {
        "warm_start": True,
        "increment_only": True,
    }

    if previous_model_path:
        config["previous_model_path"] = previous_model_path

    if model_type in (ModelType.LIGHTGBM, ModelType.XGBOOST):
        config["params"] = {"warm_start": True}

    return config


def format_model_selection_prompt(
    symbols: list[str] | None = None,
    market_caps: dict[str, float] | None = None,
) -> str:
    """生成模型选择说明的 prompt.

    用于 rd-agent 生成因子后的模型选择指导。
    """
    lines = [
        "=== Meta-Learner: 模型自动选择 ===",
        "[规则]",
    ]

    for tier, rule in MODEL_SELECTION_RULES.items():
        tier_name = {
            MarketCapTier.LARGE: "大盘股 (>500亿)",
            MarketCapTier.MID: "中盘股 (50-500亿)",
            MarketCapTier.SMALL: "小盘股 (<50亿)",
            MarketCapTier.CRYPTO: "数字货币",
        }.get(tier, str(tier))

        models = ", ".join([m.value for m in rule["recommended"]])
        lines.append(f"- {tier_name}: {models} ({rule['rationale']})")

    if symbols and market_caps:
        lines.append("\n[当前标的]")
        for sym in symbols[:5]:
            cap = market_caps.get(sym)
            _, config = select_model(sym, cap)
            lines.append(f"- {sym}: {config['model_type']}")

    return "\n".join(lines)