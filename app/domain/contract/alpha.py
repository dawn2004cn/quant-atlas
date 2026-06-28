from __future__ import annotations

"""Alpha Entity Contract - Unified Alpha representation."""


from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AlphaSource(Enum):
    """Source of the alpha factor."""
    RD_AGENT = "rd_agent"
    TECHNICAL_ANALYST = "technical_analyst"
    FUNDAMENTAL_ANALYST = "fundamental_analyst"
    MANUAL = "manual"
    DISCOVERY = "discovery"


class AlphaStatus(Enum):
    """Lifecycle status of alpha."""
    EXPERIMENT = "experiment"
    BACKTEST = "backtest"
    VALIDATION = "validation"
    SHADOW_TEST = "shadow_test"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"
    FAILED = "failed"


@dataclass
class AlphaMetrics:
    """Performance metrics for an alpha."""
    ic_mean: float = 0.0
    ic_std: float = 0.0
    ir: float = 0.0
    sharpe: float = 0.0
    max_drawdown: float = 0.0
    turnover: float = 0.0
    returns: float = 0.0
    backtest_start: datetime | None = None
    backtest_end: datetime | None = None


@dataclass
class AlphaEntity:
    """Unified Alpha representation across all sources.

    This is the canonical form that all alpha generators (RD-Agent,
    Technical Analyst, etc.) must produce.
    """
    id: str
    formula: str
    name: str
    source: AlphaSource
    status: AlphaStatus
    description: str = ""

    metrics: AlphaMetrics = field(default_factory=AlphaMetrics)
    parameters: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    experiment_id: str | None = None
    backtest_id: str | None = None
    model_id: str | None = None

    lineage: dict[str, Any] = field(default_factory=dict)

    def is_production_ready(self) -> bool:
        """Check if alpha is ready for production."""
        return (
            self.status in [AlphaStatus.VALIDATION, AlphaStatus.SHADOW_TEST, AlphaStatus.PRODUCTION]
            and self.metrics.ir > 0.5
            and self.metrics.sharpe > 1.0
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "formula": self.formula,
            "name": self.name,
            "source": self.source.value,
            "status": self.status.value,
            "description": self.description,
            "metrics": {
                "ic_mean": self.metrics.ic_mean,
                "ic_std": self.metrics.ic_std,
                "ir": self.metrics.ir,
                "sharpe": self.metrics.sharpe,
                "max_drawdown": self.metrics.max_drawdown,
                "turnover": self.metrics.turnover,
                "returns": self.metrics.returns,
            },
            "parameters": self.parameters,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "experiment_id": self.experiment_id,
            "backtest_id": self.backtest_id,
            "model_id": self.model_id,
            "lineage": self.lineage,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AlphaEntity:
        """Deserialize from dictionary."""
        metrics_data = data.get("metrics", {})
        metrics = AlphaMetrics(
            ic_mean=metrics_data.get("ic_mean", 0.0),
            ic_std=metrics_data.get("ic_std", 0.0),
            ir=metrics_data.get("ir", 0.0),
            sharpe=metrics_data.get("sharpe", 0.0),
            max_drawdown=metrics_data.get("max_drawdown", 0.0),
            turnover=metrics_data.get("turnover", 0.0),
            returns=metrics_data.get("returns", 0.0),
        )

        return cls(
            id=data["id"],
            formula=data["formula"],
            name=data["name"],
            source=AlphaSource(data["source"]),
            status=AlphaStatus(data["status"]),
            description=data.get("description", ""),
            metrics=metrics,
            parameters=data.get("parameters", {}),
            tags=data.get("tags", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            experiment_id=data.get("experiment_id"),
            backtest_id=data.get("backtest_id"),
            model_id=data.get("model_id"),
            lineage=data.get("lineage", {}),
        )
