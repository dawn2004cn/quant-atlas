from __future__ import annotations

"""Domain entities.

Mappings to infra ORM models (P2-21):
  UserAccount          → app.infrastructure.database.models.User
  StockQuote           → app.infrastructure.database.models.Stock (partial)
  ChipDistribution     → app.infrastructure.database.models.ChipDistribution
  PerformanceMetrics   → (computed, not persisted)
  BacktestReport       → app.infrastructure.database.models.BacktestResult

StockQuote and UserAccount are canonical definitions in
``app.domain.shared.value_objects`` and re-exported here for
backward compatibility.
"""


from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .enums import MarketCode


@dataclass(frozen=True)
class MarketSnapshot:
    """Market overview aggregate."""

    market: MarketCode
    generated_at: datetime
    summary: dict[str, Any]
    rankings: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    sectors: list[dict[str, Any]] = field(default_factory=list)

    def top_gainers(self, n: int = 5) -> list[dict[str, Any]]:
        return self.rankings.get("gainers", [])[:n]

    def top_losers(self, n: int = 5) -> list[dict[str, Any]]:
        return self.rankings.get("losers", [])[:n]

    def is_stale(self, max_age_minutes: int = 5) -> bool:
        now = datetime.now()
        age = (now - self.generated_at).total_seconds() / 60
        return age > max_age_minutes

    def total_trading_volume(self) -> float:
        return sum(s.get("volume", 0) for s in self.sectors)


@dataclass(frozen=True)
class NewsItem:
    """Stock news model."""

    title: str
    published_at: str
    source: str
    url: str = ""
    summary: str = ""


@dataclass(frozen=True)
class StrategySelection:
    """Strategy selection result."""

    strategy: str
    market: MarketCode
    generated_at: datetime
    candidates: list[dict[str, Any]]


@dataclass(frozen=True)
class PerformanceMetrics:
    """Standardized performance metrics aggregate (DDD Value Object)."""

    final_value: float
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float = 0.0
    turnover_rate: float = 0.0
    slippage_cost_bps: float = 0.0
    total_fee: float = 0.0
    total_tax: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    calmar_ratio: float = 0.0
    volatility: float = 0.0
    stock_data: dict[str, Any] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def is_profitable(self) -> bool:
        """Overall profitability assessment."""
        return self.total_return > 0 and self.final_value > 0

    def risk_adjusted_score(self) -> float:
        """Composite risk-adjusted performance score."""
        if self.volatility <= 0 or self.max_drawdown <= -100:
            return 0.0
        return (self.annual_return / max(self.volatility, 0.01)) * (self.win_rate / 100.0)

    def summary_dict(self) -> dict[str, Any]:
        """Compact summary for display."""
        return {
            "return_pct": round(self.total_return, 2),
            "annual_return_pct": round(self.annual_return, 2),
            "max_drawdown_pct": round(self.max_drawdown, 2),
            "sharpe": round(self.sharpe_ratio, 3),
            "win_rate_pct": round(self.win_rate, 1),
        }


@dataclass(frozen=True)
class BacktestReport:
    """Backtest report."""

    strategy: str
    symbol: str
    period: dict[str, str]
    metrics: PerformanceMetrics | dict[str, Any]
    trades: list[dict[str, Any]]

    def get_metrics(self) -> PerformanceMetrics:
        if isinstance(self.metrics, PerformanceMetrics):
            return self.metrics
        return PerformanceMetrics(
            final_value=self.metrics.get("final_value", 0.0),
            total_return=self.metrics.get("total_return", 0.0),
            annual_return=self.metrics.get("annual_return", 0.0),
            max_drawdown=self.metrics.get("max_drawdown", 0.0),
            sharpe_ratio=self.metrics.get("sharpe_ratio", self.metrics.get("sharpe", 0.0)),
            sortino_ratio=self.metrics.get("sortino_ratio", self.metrics.get("sortino", 0.0)),
            turnover_rate=self.metrics.get("turnover_rate", 0.0),
            slippage_cost_bps=self.metrics.get("slippage_cost_bps", 0.0),
            total_fee=self.metrics.get("total_fee", 0.0),
            total_tax=self.metrics.get("total_tax", 0.0),
            win_rate=self.metrics.get("win_rate", 0.0),
            profit_factor=self.metrics.get("profit_factor", 0.0),
            calmar_ratio=self.metrics.get("calmar_ratio", 0.0),
            volatility=self.metrics.get("volatility", 0.0),
            stock_data=self.metrics.get("stock_data", {}),
            diagnostics=self.metrics.get("diagnostics", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        """Flatten report for legacy /api/v1/backtest JSON consumers."""
        m = self.metrics if isinstance(self.metrics, dict) else {
            "final_value": self.metrics.final_value,
            "total_return": self.metrics.total_return,
            "annual_return": self.metrics.annual_return,
            "max_drawdown": self.metrics.max_drawdown,
            "sharpe_ratio": self.metrics.sharpe_ratio,
            "sortino_ratio": self.metrics.sortino_ratio,
            "stock_data": self.metrics.stock_data,
            "diagnostics": self.metrics.diagnostics,
        }
        stock_data = m.get("stock_data") or {}
        equity_curve = m.get("equity_curve") or []
        sharpe = m.get("sharpe_ratio", m.get("sharpe", 0.0))
        return {
            "strategy": self.strategy,
            "symbol": self.symbol,
            "period": dict(self.period),
            "trades": list(self.trades),
            "stock_data": stock_data,
            "equity_curve": equity_curve,
            "metrics": m,
            "final_value": m.get("final_value", 0.0),
            "total_return": m.get("total_return", 0.0),
            "annual_return": m.get("annual_return", 0.0),
            "max_drawdown": m.get("max_drawdown", 0.0),
            "sharpe_ratio": sharpe,
            "diagnostics": m.get("diagnostics", {}),
        }


@dataclass(frozen=True)
class ChipDistribution:
    """筹码分布实体 (移植自 DSA)。"""

    profit_ratio: float  # 获利比例
    avg_cost: float  # 平均成本
    concentration_90: float  # 90% 筹码集中度
    concentration_70: float  # 70% 筹码集中度
    winner_90_low: float = 0.0
    winner_90_high: float = 0.0
    winner_70_low: float = 0.0
    winner_70_high: float = 0.0

    def is_concentrated(self, threshold: float = 15.0) -> bool:
        """Check if chips are highly concentrated."""
        return self.concentration_90 < threshold

    def majority_profitable(self) -> bool:
        """Whether majority of holders are in profit."""
        return self.profit_ratio > 50.0


@dataclass(frozen=True)
class TrendAnalysisResult:
    """技术趋势分析结果 (移植自 DSA)。"""

    code: str
    current_price: float
    ma5: float
    ma10: float
    ma20: float
    bias_ma5: float
    trend_status: str  # 趋势状态：多头排列、空头排列、震荡等
    support_levels: list[float] = field(default_factory=list)
    resistance_levels: list[float] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)

    def is_bullish(self) -> bool:
        """Multi-indicator bullish check."""
        return (
            self.current_price > self.ma5 > self.ma10
            and "多头" in self.trend_status
        )

    def is_bearish(self) -> bool:
        """Multi-indicator bearish check."""
        return (
            self.current_price < self.ma20
            and "空头" in self.trend_status
        )

    def nearest_support(self) -> float | None:
        """Nearest support level below current price."""
        below = [s for s in self.support_levels if s < self.current_price]
        return max(below) if below else None

    def nearest_resistance(self) -> float | None:
        """Nearest resistance level above current price."""
        above = [r for r in self.resistance_levels if r > self.current_price]
        return min(above) if above else None


@dataclass(frozen=True)
class FinGPTPrediction:
    """FinGPT 风格的预测结果。"""

    ticker: str
    prediction_date: str
    predicted_movement: str  # e.g., "up by 1-2%"
    analysis_summary: str
    positive_factors: list[str]
    potential_concerns: list[str]
    confidence: float


@dataclass(frozen=True)
class StrategyConfig:
    """Configuration for a specific strategy."""

    strategy_id: str
    parameters: dict[str, Any] = field(default_factory=dict)
    is_enabled: bool = True
    display_name: str | None = None


@dataclass(frozen=True)
class Experiment:
    """Research experiment asset."""

    id: str
    name: str
    swarm_run_id: str
    preset_name: str
    status: str
    version: int = 1
    artifacts: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def is_complete(self) -> bool:
        """Check if experiment finished successfully."""
        return self.status == "completed"

    def mark_as_failed(self) -> Experiment:
        """Transition experiment to failed state."""
        return Experiment(
            id=self.id,
            name=self.name,
            swarm_run_id=self.swarm_run_id,
            preset_name=self.preset_name,
            status="failed",
            version=self.version + 1,
            artifacts=self.artifacts,
            metadata=self.metadata,
            created_at=self.created_at
        )

    def resolved_metrics(self) -> dict[str, Any]:
        """Metrics from metadata or artifacts (vault / qlib persistence)."""
        meta = self.metadata or {}
        artifacts = self.artifacts or {}
        metrics = meta.get("metrics") or artifacts.get("metrics") or {}
        return metrics if isinstance(metrics, dict) else {}

    def resolved_equity_curve(self) -> list[Any]:
        """Equity curve from artifacts, metadata, or nested metrics."""
        meta = self.metadata or {}
        artifacts = self.artifacts or {}
        metrics = self.resolved_metrics()
        curve = (
            artifacts.get("equity_curve")
            or meta.get("equity_curve")
            or metrics.get("equity_curve")
            or []
        )
        return curve if isinstance(curve, list) else []

    def to_api_summary(self) -> dict[str, Any]:
        """Stable list-view payload for ``GET /experiments``."""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metrics": self.resolved_metrics(),
        }

    def to_api_detail(self) -> dict[str, Any]:
        """Stable detail payload for ``GET /experiments/<id>``."""
        meta = self.metadata or {}
        artifacts = self.artifacts or {}
        return {
            "id": self.id,
            "name": self.name,
            "description": meta.get("description", ""),
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metrics": self.resolved_metrics(),
            "artifacts": artifacts,
            "equity_curve": self.resolved_equity_curve(),
            "strategy_code": meta.get("strategy_code") or artifacts.get("strategy_code") or "",
            "findings": meta.get("findings") or artifacts.get("findings") or [],
            "swarm_run_id": self.swarm_run_id,
            "preset_name": self.preset_name,
        }


@dataclass(frozen=True)
class Tenant:
    """Multi-tenant organization root (6.0 collaboration OS)."""

    id: int
    slug: str
    name: str
    plan: str = "standard"
    created_at: datetime | None = None


@dataclass(frozen=True)
class Team:
    """Research team within a tenant."""

    id: int
    tenant_id: int
    slug: str
    name: str
    created_at: datetime | None = None


@dataclass(frozen=True)
class TeamMembership:
    """User membership in a team with role-based access."""

    id: int
    team_id: int
    user_id: int
    role: str = "member"
    joined_at: datetime | None = None


@dataclass(frozen=True)
class EvidenceNote:
    """Evidence item used to explain a generated decision."""

    source: str
    title: str = ""
    confidence: float | None = None
    observed_at: datetime | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DecisionContext:
    """Replayable provenance for AI recommendations and strategy decisions."""

    decision_id: str
    subject: str
    input_snapshot: dict[str, Any] = field(default_factory=dict)
    model_version: str = "unknown"
    reasoning_trace: list[str] = field(default_factory=list)
    evidence: list[EvidenceNote] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
