from __future__ import annotations

"""API v2 Context - carries dependencies for v2 routes."""


from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ApiV2Context:
    """Immutable context for API v2 routes."""

    market_service: Any
    stock_service: Any
    news_provider: Any
    fundamental_access: Any
    news_archive: Any
    qlib_pipeline_service: Any
    strategy_service: Any
    pool_service: Any
    ai_analysis_service: Any
    ai_research_service: Any
    analysis_service: Any
    watchlist_service: Any
    stock_group_service: Any
    user_service: Any
    rdagent_run_service: Any
    prediction_service: Any
    selection_source_service: Any
    basic_market_data_service: Any
    task_message_store: Any
    market_facade: Any = None
    backtest_facade: Any = None
    ai_facade: Any = None
    portfolio_service: Any = None
    risk_service: Any = None
    system_service: Any = None
    signal_flag_service: Any = None
    investment_manager_service: Any = None
    moments_service: Any = None
    integration_stack_service: Any = None
    fingpt_application_service: Any = None
    strategy_sop_service: Any = None
    auth_service: Any = None
    enable_celery: bool = False
    enable_qlib: bool = False
    enable_rd_agent: bool = False
    enable_dto_validation: bool = True

    @classmethod
    def from_v1_context(cls, v1_ctx, **overrides) -> ApiV2Context:
        """Create v2 context from v1 context with optional overrides."""
        fields = {
            f.name: getattr(v1_ctx, f.name, None)
            for f in v1_ctx.__dataclass_fields__.values()
        }
        fields.update(overrides)
        return cls(**fields)
