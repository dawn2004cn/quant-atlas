from __future__ import annotations

"""Financial Data Tools - 财务数据相关工具."""


from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field

from ..core.logger import get_logger

logger = get_logger(__name__)


class CnFinancialStatementsToolResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ticker: str
    ok: bool = True
    error: str | None = None
    statements: dict[str, Any] = Field(default_factory=dict)
    evidence: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class CnResearchReportsToolResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ticker: str
    ok: bool = True
    error: str | None = None
    reports: list[dict[str, Any]] = Field(default_factory=list)
    evidence: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class TdxFinancialDataToolResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ticker: str
    ok: bool = True
    error: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    evidence: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


def _confidence_cn_financial(bundle: dict[str, Any]) -> float:
    """根据财务数据完整性计算置信度."""
    if not bundle:
        return 0.2
    has_income = bool(bundle.get("income_statement"))
    has_balance = bool(bundle.get("balance_sheet"))
    has_cash = bool(bundle.get("cash_flow"))
    score = (has_income + has_balance + has_cash) / 3
    return 0.5 + score * 0.4


@tool
def get_cn_financial_statements(ticker: str) -> CnFinancialStatementsToolResult:
    """获取A股财务摘要与三表 (资产负债表、利润表、现金流量表)."""
    from datetime import datetime, timedelta

    from ..application.services.tool_facade_service import get_tool_facade_service

    try:
        service = get_tool_facade_service()
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=365 * 3)).strftime("%Y-%m-%d")

        bundle = service.get_financial_data(ticker, start_date=start_date, end_date=end_date)
        confidence = _confidence_cn_financial(bundle)

        return CnFinancialStatementsToolResult(
            ticker=ticker,
            statements=bundle,
            evidence=f"Retrieved financial statements for {ticker}",
            confidence=confidence,
        )
    except Exception as e:
        logger.error(f"get_cn_financial_statements failed: {e}")
        return CnFinancialStatementsToolResult(
            ticker=ticker,
            ok=False,
            error=str(e),
            confidence=0.3,
        )


@tool
def get_cn_research_reports(ticker: str, limit: int = 30) -> CnResearchReportsToolResult:
    """获取个股研报."""
    from ..application.services.research.research_report_rag_service import get_research_report_service
    from ..domain.enums import MarketCode

    try:
        market = MarketCode.CN
        service = get_research_report_service()
        reports = service.search_reports(ticker, market=market, limit=limit)

        return CnResearchReportsToolResult(
            ticker=ticker,
            reports=reports[:limit],
            evidence=f"Retrieved {len(reports)} reports for {ticker}",
            confidence=0.8 if reports else 0.4,
        )
    except Exception as e:
        logger.error(f"get_cn_research_reports failed: {e}")
        return CnResearchReportsToolResult(
            ticker=ticker,
            ok=False,
            error=str(e),
            confidence=0.3,
        )


@tool
def get_tdx_financial_data(ticker: str, periods: int = 8) -> TdxFinancialDataToolResult:
    """获取TDX专业财务数据 (gpcw*.dat, 584个具名字段)."""
    from datetime import date

    from ..infrastructure.database.mysql_client import mysql_connect
    from ..infrastructure.repositories.mysql.mysql_tdx_gpcw_repository import MySQLTdxGpcwRepository

    try:
        conn = mysql_connect()
        repo = MySQLTdxGpcwRepository(conn)
        end_date = date.today()
        start_date = date(end_date.year - 2, 1, 1)
        data = repo.get_gpcw(ticker, start_date, end_date)

        if data:
            return TdxFinancialDataToolResult(
                ticker=ticker,
                data={"records": data[:periods], "count": len(data)},
                evidence=f"Retrieved {len(data)} records for {ticker}",
                confidence=0.9,
            )
        return TdxFinancialDataToolResult(
            ticker=ticker,
            ok=False,
            error="No data available",
            confidence=0.3,
        )
    except Exception as e:
        logger.error(f"get_tdx_financial_data failed: {e}")
        return TdxFinancialDataToolResult(
            ticker=ticker,
            ok=False,
            error=str(e),
            confidence=0.3,
        )


@tool
def get_cn_longhu_for_symbol(ticker: str, max_rows: int = 15) -> dict[str, Any]:
    """获取龙虎榜上榜记录."""
    from ..application.services.tool_facade_service import get_tool_facade_service

    try:
        service = get_tool_facade_service()
        data = service.get_longhu_data(ticker, max_rows=max_rows)
        return {
            "ticker": ticker,
            "ok": True,
            "records": data,
            "count": len(data),
        }
    except Exception as e:
        logger.error(f"get_cn_longhu_for_symbol failed: {e}")
        return {
            "ticker": ticker,
            "ok": False,
            "error": str(e),
        }
