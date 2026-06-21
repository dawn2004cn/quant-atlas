"""Workflow spine — unified task/workflow orchestration layer.

Provides:
- ``BaseWorkflow`` — abstract base wrapping ``AgentWorkflow`` state machine.
- ``ResearchWorkflow`` — AI research / analysis workflow.
- ``TradingWorkflow`` — signal → risk → order workflow.
- ``DataPipelineWorkflow`` — ETL / sync / backfill workflow.
- ``WorkflowService`` — registry & lifecycle management for web/Celery.
"""

from app.application.workflows.base_workflow import BaseWorkflow
from app.application.workflows.research_workflow import ResearchWorkflow
from app.application.workflows.trading_workflow import TradingWorkflow
from app.application.workflows.data_pipeline_workflow import DataPipelineWorkflow
from app.application.workflows.workflow_service import WorkflowService

__all__ = [
    "BaseWorkflow",
    "ResearchWorkflow",
    "TradingWorkflow",
    "DataPipelineWorkflow",
    "WorkflowService",
]
