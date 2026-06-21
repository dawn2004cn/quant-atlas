"""Analysis Report Repository — re-exports SQLite implementation.

Replaces broken facade chain (analysis->facade->analysis = circular).
"""
from app.infrastructure.repositories.sqlite.sqlite_analysis_report_repository import (
    SQLiteAnalysisReportRepository as AnalysisReportRepository,
)

__all__ = ["AnalysisReportRepository"]
