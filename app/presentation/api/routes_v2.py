from __future__ import annotations
"""API v2 routes - DTO-validated endpoints with standardized response format.

This module provides the v2 REST API surface:
- DTO-based request validation using Pydantic
- Standardized response format (data + meta)
- Explicit version in URL path (/api/v2)
"""


import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from ...application.errors import ValidationError
from ...application.dto import (
    BacktestRequestDTO,
    SelectionRequestDTO,
    WatchlistCreateDTO,
    WatchlistAddStockDTO,
    StockHistoryDTO,
)
from ...application.dto.v2_dtos import (
    PredictionRequestDTO,
    NewsRequestDTO,
    PortfolioCreateDTO,
    PortfolioRebalanceDTO,
    PortfolioDetailDTO,
    StockSearchDTO,
)
from ...domain.enums import MarketCode
from .v2_context import ApiV2Context
from .request_parsers import parse_dto
from .responses import success_response, serialize

logger = logging.getLogger(__name__)


def create_api_v2_blueprint(
    market_service,
    stock_service,
    news_provider,
    fundamental_access,
    news_archive,
    qlib_pipeline_service,
    strategy_service,
    pool_service,
    ai_analysis_service,
    ai_research_service,
    analysis_service,
    watchlist_service,
    stock_group_service,
    user_service,
    rdagent_run_service,
    prediction_service,
    selection_source_service,
    basic_market_data_service,
    task_message_store,
    enable_celery: bool = False,
    enable_qlib: bool = False,
    enable_rd_agent: bool = False,
    enable_dto_validation: bool = True,
    signal_flag_service=None,
    investment_manager_service=None,
    moments_service=None,
    integration_stack_service=None,
    fingpt_application_service=None,
    portfolio_service=None,
    portfolio_trade_service=None,
    risk_service=None,
    system_service=None,
    strategy_sop_service=None,
    market_facade=None,
    backtest_facade=None,
    ai_facade=None,
    auth_service=None,
):
    blueprint = Blueprint("api_v2", __name__, url_prefix="/api/v2")

    ctx = ApiV2Context(
        market_service=market_service,
        market_facade=market_facade,
        stock_service=stock_service,
        news_provider=news_provider,
        fundamental_access=fundamental_access,
        news_archive=news_archive,
        qlib_pipeline_service=qlib_pipeline_service,
        strategy_service=strategy_service,
        pool_service=pool_service,
        ai_analysis_service=ai_analysis_service,
        ai_research_service=ai_research_service,
        analysis_service=analysis_service,
        watchlist_service=watchlist_service,
        stock_group_service=stock_group_service,
        user_service=user_service,
        rdagent_run_service=rdagent_run_service,
        prediction_service=prediction_service,
        selection_source_service=selection_source_service,
        basic_market_data_service=basic_market_data_service,
        task_message_store=task_message_store,
        backtest_facade=backtest_facade,
        ai_facade=ai_facade,
        enable_celery=enable_celery,
        enable_qlib=enable_qlib,
        enable_rd_agent=enable_rd_agent,
        enable_dto_validation=enable_dto_validation,
        signal_flag_service=signal_flag_service,
        investment_manager_service=investment_manager_service,
        moments_service=moments_service,
        integration_stack_service=integration_stack_service,
        fingpt_application_service=fingpt_application_service,
        strategy_sop_service=strategy_sop_service,
        auth_service=auth_service,
    )

    # ------------------------------------------------------------------ #
    # Modular Route Registration (V2 Gateway)
    # ------------------------------------------------------------------ #
    from .v2.auth_routes import create_auth_blueprint
    from .v2.system import create_system_blueprint
    from .v2.market import create_market_blueprint
    from .v2.strategy import create_strategy_blueprint
    from .v2.ai import create_ai_blueprint
    from .v2.user import create_user_blueprint
    from .v2.data import create_data_blueprint
    from .v2.trading import create_trading_blueprint
    
    blueprint.register_blueprint(create_auth_blueprint(ctx), url_prefix="")
    blueprint.register_blueprint(create_system_blueprint(ctx), url_prefix="/system")
    blueprint.register_blueprint(create_market_blueprint(ctx), url_prefix="")
    blueprint.register_blueprint(create_strategy_blueprint(ctx), url_prefix="/strategies")
    blueprint.register_blueprint(create_ai_blueprint(ctx), url_prefix="")
    blueprint.register_blueprint(create_user_blueprint(ctx), url_prefix="")
    blueprint.register_blueprint(create_data_blueprint(ctx), url_prefix="")
    blueprint.register_blueprint(create_trading_blueprint(ctx), url_prefix="")

    return blueprint


def register_v2_routes(blueprint: Blueprint, ctx: ApiV2Context) -> None:
    """Register modular v2 routes.

    Currently all routes are defined inline in ``create_api_v2_blueprint``.
    This function is reserved for future modular route registration
    (e.g. ``register_v2_portfolio_routes(blueprint, ctx)``).
    """
    pass