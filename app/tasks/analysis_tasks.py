from __future__ import annotations

"""Celery tasks for automated analysis and validation."""


from celery import shared_task

from app.config import AppSettings, get_settings
from app.core.logger import get_logger

logger = get_logger(__name__)


def _get_analysis_repo(s: AppSettings):
    from app.infrastructure.repositories.deps import create_analysis_report_repository

    return create_analysis_report_repository(s)


@shared_task(name="app.tasks.scheduled_daily_analysis")
def scheduled_daily_analysis(user_id: int):
    """每日自选股定时分析任务。"""
    logger.info(f"触发每日自选股分析任务: user_id={user_id}")

    settings = get_settings()

    from app.agents.trading_agents_service import TradingAgentsService
    from app.bootstrap_components.repositories import create_repositories
    from app.modules.ai_agent.services.fingpt_application_service import FinGPTApplicationService
    from app.modules.strategy.services.analytics.daily_analysis_application_service import (
        DailyAnalysisApplicationService,
    )

    repositories = create_repositories(settings)
    fingpt_app = FinGPTApplicationService(
        repositories.fingpt_repository,
        write_research_sentiment=settings.fingpt_write_research_sentiment,
        write_research_prediction=settings.fingpt_write_research_prediction,
        write_ai_analyze=settings.fingpt_write_ai_analyze,
    )
    agents_service = TradingAgentsService(fingpt_application_service=fingpt_app)
    service = DailyAnalysisApplicationService(agents_service)

    from app.application.request_executor import run_async

    run_async(service.run_daily_watchlist_analysis(user_id))

    logger.info("每日自选股分析任务完成")


@shared_task(name="app.tasks.validate_ai_predictions")
def validate_ai_predictions():
    """验证 AI 历史预测的准确性任务。"""
    logger.info("触发 AI 预测验证任务...")

    settings = get_settings()

    from app.bootstrap_components.providers import create_providers
    from app.modules.ai_agent.services.analysis.analysis_prediction_service import AnalysisPredictionService

    repo = _get_analysis_repo(settings)
    providers = create_providers()
    validator = AnalysisPredictionService(repo, providers.market_provider)

    from app.application.request_executor import run_async

    run_async(validator.validate_all_pending())

    logger.info("AI 预测验证任务完成")
