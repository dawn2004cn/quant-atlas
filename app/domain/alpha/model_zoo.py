from __future__ import annotations

"""Model Zoo - Multi-model support for qlib.

实现 Section 2C: 支持多种模型的 ModelZoo。
"""


from dataclasses import dataclass
from typing import Any


@dataclass
class ModelConfig:
    """模型配置."""

    name: str
    model_type: str
    params: dict[str, Any]
    requires_features: list[str]
    interpretability: float


class ModelZoo:
    """模型动物园 - 支持多种模型类型."""

    AVAILABLE_MODELS = {
        "linear": ModelConfig(
            name="Linear Regression",
            model_type="linear",
            params={
                "fit_intercept": True,
                "positive": False,
                "alpha": 0.1,
            },
            requires_features=["returns"],
            interpretability=1.0,
        ),
        "ridge": ModelConfig(
            name="Ridge Regression",
            model_type="ridge",
            params={
                "alpha": 1.0,
                "fit_intercept": True,
            },
            requires_features=["returns"],
            interpretability=0.9,
        ),
        "lasso": ModelConfig(
            name="Lasso Regression",
            model_type="lasso",
            params={
                "alpha": 0.1,
                "fit_intercept": True,
                "max_iter": 1000,
            },
            requires_features=["returns"],
            interpretability=0.85,
        ),
        "elastic_net": ModelConfig(
            name="Elastic Net",
            model_type="elastic_net",
            params={
                "alpha": 0.1,
                "l1_ratio": 0.5,
                "fit_intercept": True,
            },
            requires_features=["returns"],
            interpretability=0.8,
        ),
        "lightgbm": ModelConfig(
            name="LightGBM",
            model_type="lightgbm",
            params={
                "n_estimators": 100,
                "max_depth": 6,
                "learning_rate": 0.05,
                "num_leaves": 31,
                "min_child_samples": 20,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
            },
            requires_features=["returns", "volume", "volatility"],
            interpretability=0.5,
        ),
        "xgboost": ModelConfig(
            name="XGBoost",
            model_type="xgboost",
            params={
                "n_estimators": 100,
                "max_depth": 6,
                "learning_rate": 0.05,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "objective": "reg:squarederror",
            },
            requires_features=["returns", "volume"],
            interpretability=0.45,
        ),
        "random_forest": ModelConfig(
            name="Random Forest",
            model_type="random_forest",
            params={
                "n_estimators": 100,
                "max_depth": 10,
                "min_samples_split": 10,
                "min_samples_leaf": 5,
            },
            requires_features=["returns"],
            interpretability=0.6,
        ),
        "gradient_boosting": ModelConfig(
            name="Gradient Boosting",
            model_type="gradient_boosting",
            params={
                "n_estimators": 100,
                "max_depth": 5,
                "learning_rate": 0.05,
                "subsample": 0.8,
            },
            requires_features=["returns"],
            interpretability=0.55,
        ),
        "gru": ModelConfig(
            name="GRU",
            model_type="custom",
            params={
                "hidden_size": 64,
                "num_layers": 2,
                "dropout": 0.2,
                "learning_rate": 0.001,
                "sequence_length": 20,
            },
            requires_features=["returns", "volume", "volatility", "technical"],
            interpretability=0.2,
        ),
        "transformer": ModelConfig(
            name="Transformer",
            model_type="custom",
            params={
                "d_model": 64,
                "nhead": 4,
                "num_layers": 2,
                "dropout": 0.2,
                "learning_rate": 0.0005,
                "sequence_length": 20,
            },
            requires_features=["returns", "volume", "volatility", "technical", "sentiment"],
            interpretability=0.15,
        ),
    }

    def __init__(self) -> None:
        self._models: dict[str, Any] = {}
        self._training_history: list[dict[str, Any]] = []

    def get_model_config(self, model_name: str) -> ModelConfig | None:
        """获取模型配置."""
        return self.AVAILABLE_MODELS.get(model_name)

    def list_models(self) -> list[dict[str, Any]]:
        """列出所有可用模型."""
        return [
            {
                "name": config.name,
                "model_type": model_type,
                "interpretability": config.interpretability,
            }
            for model_type, config in self.AVAILABLE_MODELS.items()
        ]

    def list_by_interpretability(
        self,
        min_interpretability: float = 0.0,
    ) -> list[dict[str, Any]]:
        """按可解释性筛选模型."""
        return [
            {
                "name": config.name,
                "model_type": model_type,
                "interpretability": config.interpretability,
            }
            for model_type, config in self.AVAILABLE_MODELS.items()
            if config.interpretability >= min_interpretability
        ]

    def list_by_market(
        self,
        market_cap: float | None = None,
        prefer_explainability: bool = False,
    ) -> list[dict[str, Any]]:
        """根据市场规模推荐模型.

        Args:
            market_cap: 市值 (亿)
            prefer_explainability: 优先可解释性
        """
        if prefer_explainability:
            return self.list_by_interpretability(min_interpretability=0.7)

        if market_cap is None:
            return self.list_models()

        if market_cap > 500:
            candidates = ["linear", "ridge", "lasso"]
        elif market_cap > 50:
            candidates = ["ridge", "lightgbm", "xgboost"]
        else:
            candidates = ["xgboost", "lightgbm", "random_forest", "gru"]

        return [
            {"name": self.AVAILABLE_MODELS[m].name, "model_type": m}
            for m in candidates
            if m in self.AVAILABLE_MODELS
        ]

    def get_default_config(self, model_type: str) -> dict[str, Any]:
        """获取模型默认配置."""
        config = self.get_model_config(model_type)
        if config:
            return config.params.copy()
        return {}

    def format_model_zoo_prompt(self) -> str:
        """生成 Model Zoo prompt."""
        lines = [
            "=== Model Zoo: 可用模型列表 ===",
            "",
        ]

        categories = {
            "线性模型": ["linear", "ridge", "lasso", "elastic_net"],
            "树模型": ["lightgbm", "xgboost", "random_forest", "gradient_boosting"],
            "深度学习": ["gru", "transformer"],
        }

        for cat, models in categories.items():
            lines.append(f"\n[{cat}]")
            for m in models:
                config = self.AVAILABLE_MODELS.get(m)
                if config:
                    lines.append(
                        f"- {m}: {config.name} (可解释性: {config.interpretability:.0%})"
                    )

        return "\n".join(lines)


class EnsembleModel:
    """集成模型 - 组合多个模型."""

    def __init__(self, model_types: list[str]) -> None:
        self.model_types = model_types
        self._weights: list[float] = []
        self._models: list[Any] = []

    def set_weights(self, weights: list[float]) -> None:
        """设置模型权重."""
        total = sum(weights)
        self._weights = [w / total for w in weights] if total > 0 else weights

    def predict(self, features: Any) -> float:
        """集成预测."""
        if not self._models or not self._weights:
            return 0.0

        predictions = []
        for model in self._models:
            pred = model.predict(features) if hasattr(model, "predict") else 0.0
            predictions.append(pred)

        return sum(p * w for p, w in zip(predictions, self._weights))

    def add_model(self, model: Any) -> None:
        """添加模型到集成."""
        self._models.append(model)


_zoo = ModelZoo()


def get_model_zoo() -> ModelZoo:
    """获取全局 ModelZoo 实例."""
    return _zoo


def format_model_zoo_prompt() -> str:
    """生成 Model Zoo prompt."""
    zoo = get_model_zoo()
    return zoo.format_model_zoo_prompt()


def format_model_selection_prompt(
    market_cap: float | None = None,
    prefer_explainability: bool = False,
) -> str:
    """生成模型选择 prompt."""
    zoo = get_model_zoo()
    candidates = zoo.list_by_market(market_cap, prefer_explainability)

    lines = [
        "=== 模型选择建议 ===",
        "",
    ]

    for c in candidates:
        lines.append(f"- {c['model_type']}: {c['name']}")

    return "\n".join(lines)
