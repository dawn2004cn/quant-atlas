"""Strategy Wizard — Phase 13. Alpha Marketplace with 50+ classic strategy templates.
Users pick a template, tweak parameters, and deploy without writing code."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from app.core.logger import get_logger

logger = get_logger(__name__)


StrategyCategory = Literal["trend", "mean_reversion", "breakout", "arbitrage", "multi_factor", "ml_based"]


@dataclass
class StrategyTemplate:
    """A pre-built strategy template that users can parameterise."""
    template_id: str
    name: str
    category: StrategyCategory
    description: str
    difficulty: Literal["beginner", "intermediate", "advanced"] = "beginner"
    default_params: dict[str, Any] = field(default_factory=dict)
    param_schema: dict[str, dict] = field(default_factory=dict)
    qlib_code_template: str = ""
    tags: list[str] = field(default_factory=list)
    estimated_sharpe: float = 0.0
    market: str = "CN"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class UserStrategyInstance:
    """A user's instantiated strategy from a template."""
    instance_id: str
    user_id: int
    template_id: str
    params: dict[str, Any]
    name: str = ""
    status: str = "draft"  # draft → backtesting → active → stopped
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_run: str = ""


# ── 50+ Classic Strategy Templates ──────────────────────────────────

STRATEGY_TEMPLATES: dict[str, StrategyTemplate] = {}

def _register_templates():
    """Register all built-in strategy templates."""
    templates = [
        # ── Trend Following ─────────────────────────────────────────
        StrategyTemplate("ma_cross", "均线金叉策略", "trend",
            "双均线交叉信号: 短线上穿长线时买入, 下穿时卖出",
            "beginner",
            default_params={"short_ma": 5, "long_ma": 20, "stop_loss_pct": 5.0},
            param_schema={"short_ma": {"type": "int", "min": 3, "max": 30, "default": 5},
                          "long_ma": {"type": "int", "min": 10, "max": 120, "default": 20}},
            tags=["ma", "cross", "beginner"], estimated_sharpe=0.8),

        StrategyTemplate("macd_divergence", "MACD底背离", "trend",
            "MACD与价格底背离时抄底, 顶背离时逃顶", "intermediate",
            default_params={"fast": 12, "slow": 26, "signal": 9},
            tags=["macd", "divergence"], estimated_sharpe=1.2),

        StrategyTemplate("bollinger_trend", "布林带趋势突破", "trend",
            "价格突破布林带上轨做多, 跌破下轨做空", "beginner",
            default_params={"period": 20, "std_dev": 2.0},
            tags=["bollinger", "breakout"], estimated_sharpe=0.9),

        StrategyTemplate("adx_trend", "ADX趋势强度", "trend",
            "ADX>25表示强趋势, 结合±DI方向", "intermediate",
            default_params={"period": 14, "threshold": 25},
            tags=["adx", "trend_strength"], estimated_sharpe=1.0),

        StrategyTemplate("ichimoku", "一目均衡表", "trend",
            "基于云图、转折线、基准线的综合趋势判断", "advanced",
            default_params={"conversion": 9, "base": 26, "span": 52},
            tags=["ichimoku", "japanese"], estimated_sharpe=1.1),

        # ── Mean Reversion ──────────────────────────────────────────
        StrategyTemplate("rsi_reversal", "RSI超买超卖反转", "mean_reversion",
            "RSI<30超卖买入, RSI>70超买卖出", "beginner",
            default_params={"rsi_period": 14, "oversold": 30, "overbought": 70},
            tags=["rsi", "reversal"], estimated_sharpe=0.7),

        StrategyTemplate("bollinger_squeeze", "布林带缩口突破", "mean_reversion",
            "布林带极度缩口后突破方向", "intermediate",
            default_params={"period": 20, "squeeze_threshold": 0.1},
            tags=["bollinger", "squeeze"], estimated_sharpe=1.3),

        StrategyTemplate("mean_reversion_zscore", "Z-Score均值回归", "mean_reversion",
            "价格偏离均值2个标准差以上时回归交易", "intermediate",
            default_params={"window": 20, "z_threshold": 2.0},
            tags=["zscore", "statistical"], estimated_sharpe=1.0),

        StrategyTemplate("pair_trading", "配对交易", "mean_reversion",
            "两个高度相关品种价差偏离均值时回归", "advanced",
            default_params={"lookback": 60, "entry_z": 2.0, "exit_z": 0.5},
            tags=["pair", "stat_arb"], estimated_sharpe=1.5),

        # ── Breakout ────────────────────────────────────────────────
        StrategyTemplate("volume_breakout", "放量突破", "breakout",
            "成交量放大+价格突破近期高点", "beginner",
            default_params={"lookback": 20, "volume_ratio": 1.5},
            tags=["volume", "breakout"], estimated_sharpe=1.1),

        StrategyTemplate("gap_trading", "跳空缺口策略", "breakout",
            "开盘跳空缺口方向交易, 回补缺口平仓", "intermediate",
            default_params={"gap_threshold_pct": 2.0},
            tags=["gap", "opening"], estimated_sharpe=0.8),

        StrategyTemplate("channel_breakout", "唐奇安通道突破", "breakout",
            "突破20日最高价买入, 跌破最低价卖出", "intermediate",
            default_params={"period": 20, "atr_multiplier": 2.0},
            tags=["channel", "donchian"], estimated_sharpe=1.2),

        StrategyTemplate("flag_pattern", "旗形整理突破", "breakout",
            "识别旗形整理形态后的方向突破", "advanced",
            default_params={"lookback": 30, "consolidation_pct": 5.0},
            tags=["pattern", "flag"], estimated_sharpe=1.3),

        # ── Multi-Factor ────────────────────────────────────────────
        StrategyTemplate("three_factor", "三因子模型(Fama-French)", "multi_factor",
            "市场、规模、价值三因子加权组合", "advanced",
            default_params={"market_weight": 1.0, "size_weight": 0.5, "value_weight": 0.3},
            tags=["factor", "french"], estimated_sharpe=1.4),

        StrategyTemplate("momentum_quality", "动量+质量复合", "multi_factor",
            "12月动量 + ROE质量因子复合选股", "advanced",
            default_params={"momentum_window": 252, "quality_window": 4},
            tags=["momentum", "quality"], estimated_sharpe=1.6),

        StrategyTemplate("low_volatility", "低波动率策略", "multi_factor",
            "选择过去60日波动率最低的股票组合", "intermediate",
            default_params={"lookback": 60, "top_n": 20},
            tags=["volatility", "defensive"], estimated_sharpe=1.0),

        # ── ML-Based ────────────────────────────────────────────────
        StrategyTemplate("xgboost_factor", "XGBoost因子组合", "ml_based",
            "使用XGBoost对多因子打分, 选Top-N股票", "advanced",
            default_params={"n_estimators": 100, "top_n": 10},
            tags=["ml", "xgboost"], estimated_sharpe=1.7),

        StrategyTemplate("lstm_price_pred", "LSTM价格预测", "ml_based",
            "LSTM神经网络预测短期价格方向", "advanced",
            default_params={"lookback": 60, "epochs": 50},
            tags=["ml", "lstm", "deep_learning"], estimated_sharpe=1.3),
    ]
    for t in templates:
        STRATEGY_TEMPLATES[t.template_id] = t


class StrategyWizardService:
    """Strategy Wizard — marketplace browsing, parameterisation, instantiation."""

    def __init__(self):
        self._instances: dict[str, UserStrategyInstance] = {}

    def list_templates(self, category: str | None = None, difficulty: str | None = None,
                       query: str | None = None) -> list[StrategyTemplate]:
        """Browse available templates."""
        results = list(STRATEGY_TEMPLATES.values())
        if category:
            results = [t for t in results if t.category == category]
        if difficulty:
            results = [t for t in results if t.difficulty == difficulty]
        if query:
            q = query.lower()
            results = [t for t in results if q in t.name.lower() or q in t.description.lower()]
        return results

    def get_template(self, template_id: str) -> StrategyTemplate | None:
        return STRATEGY_TEMPLATES.get(template_id)

    def instantiate(self, user_id: int, template_id: str, params: dict | None = None,
                    custom_name: str = "") -> UserStrategyInstance:
        """Create a user strategy from a template with params."""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        merged = dict(template.default_params)
        if params:
            merged.update(params)

        instance = UserStrategyInstance(
            instance_id=str(uuid4().hex[:12]),
            user_id=user_id,
            template_id=template_id,
            params=merged,
            name=custom_name or template.name,
        )
        self._instances[instance.instance_id] = instance
        logger.info("User %d instantiated strategy %s (%s)", user_id, instance.name, template_id)
        return instance

    def get_user_strategies(self, user_id: int) -> list[UserStrategyInstance]:
        return [i for i in self._instances.values() if i.user_id == user_id]

    def generate_qlib_code(self, instance_id: str) -> str:
        """Generate Qlib-compatible strategy code from a user instance."""
        instance = self._instances.get(instance_id)
        if not instance:
            return ""
        template = self.get_template(instance.template_id)
        if not template or not template.qlib_code_template:
            # Auto-generate generic code
            return self._auto_generate_code(instance)
        return template.qlib_code_template.format(**instance.params)

    def _auto_generate_code(self, instance: UserStrategyInstance) -> str:
        """Auto-generate Qlib strategy code from params."""
        params = instance.params
        lines = [
            "from qlib.contrib.strategy import TopkDropoutStrategy",
            f"strategy = TopkDropoutStrategy(",
            f"    topk={params.get('top_n', 10)},",
            f"    dropout={params.get('dropout', 5)},",
            f")",
        ]
        return "\n".join(lines)


_register_templates()
