"""Quant LangGraph tools wiring (mocked services)."""

from unittest.mock import MagicMock

import app.tools.quant_tools as qt
from app.application.services.watchlist_service import WatchlistApplicationService
from app.domain.enums import MarketCode
from app.tools.quant_tools import QuantToolRuntime, configure_quant_tools


def _stub_tool_facade():
    m = MagicMock()
    m.fetch_bars.return_value = (
        [{"date": "2024-01-02", "open": 10, "high": 11, "low": 9, "close": 10.5, "volume": 1000}],
        "mock evidence",
    )
    m.fetch_profile.return_value = {"symbol": "600519"}, "mock profile"
    m.cn_financial_bundle.return_value = {
        "symbol": "600519",
        "em_symbol": "SH600519",
        "financial_abstract": [{"item": "每股收益", "value": 1.0}],
        "balance_sheet": [],
        "profit_sheet": [],
        "cash_flow_sheet": [],
        "errors": {},
        "source": "mock",
    }
    m.cn_research_reports.return_value = ([{"title": "mock"}], None)
    m.news_bundle.return_value = {
        "news": [
            {
                "title": "贵州茅台600519发布业绩预告",
                "published_at": "2024-01-01",
                "source": "mock",
                "url": "https://example.com",
                "summary": "",
            }
        ],
        "industry_news": [],
        "company_name_hint": "贵州茅台",
        "industry_hint": "白酒",
        "archive_total_rows": 1,
        "remote_refreshed": False,
    }
    m.run_backtest.return_value = {"ok": True}, "mock backtest"
    m.run_selector.return_value = {"ok": True, "candidates": []}, "mock selector"
    return m


def test_infer_market_and_symbol():
    assert qt.infer_market_and_symbol("600519")[0] == MarketCode.CN
    assert qt.infer_market_and_symbol("AAPL")[0] == MarketCode.US
    assert qt.infer_market_and_symbol("0700.HK")[0] == MarketCode.HK
    assert qt.infer_market_and_symbol("BTCUSDT")[0] == MarketCode.CRYPTO


def test_get_market_data_tool_invocation():
    facade = _stub_tool_facade()
    wl_repo = MagicMock()
    wl_repo.list_symbols.return_value = []
    wl = WatchlistApplicationService(wl_repo)
    users = MagicMock()
    configure_quant_tools(
        QuantToolRuntime(
            tool_facade_service=facade,
            watchlist_service=wl,
            user_repository=users,
        )
    )
    try:
        out = qt.get_market_data.invoke({"ticker": "600519", "period": "1y", "interval": "1d"})
    finally:
        qt.reset_quant_tools_runtime()
    assert out.bar_count == 1
    assert out.confidence > 0.5
    assert out.evidence  # Should have evidence


def test_get_market_data_empty_ticker():
    facade = _stub_tool_facade()
    wl_repo = MagicMock()
    wl = WatchlistApplicationService(wl_repo)
    users = MagicMock()
    configure_quant_tools(
        QuantToolRuntime(
            tool_facade_service=facade,
            watchlist_service=wl,
            user_repository=users,
        )
    )
    try:
        out = qt.get_market_data.invoke({"ticker": "", "period": "1y"})
    finally:
        qt.reset_quant_tools_runtime()
    assert out.ok is False


def test_get_cn_financial_statements_cn_stub():
    facade = _stub_tool_facade()
    wl_repo = MagicMock()
    wl = WatchlistApplicationService(wl_repo)
    users = MagicMock()
    configure_quant_tools(
        QuantToolRuntime(
            tool_facade_service=facade,
            watchlist_service=wl,
            user_repository=users,
        )
    )
    try:
        out = qt.get_cn_financial_statements.invoke({"ticker": "600519.SH"})
    finally:
        qt.reset_quant_tools_runtime()
    assert out.ok is True
    assert "600519" in out.evidence


def test_get_cn_financial_statements_us_rejected():
    facade = _stub_tool_facade()
    wl_repo = MagicMock()
    wl = WatchlistApplicationService(wl_repo)
    users = MagicMock()
    configure_quant_tools(
        QuantToolRuntime(
            tool_facade_service=facade,
            watchlist_service=wl,
            user_repository=users,
        )
    )
    try:
        out = qt.get_cn_financial_statements.invoke({"ticker": "AAPL"})
    finally:
        qt.reset_quant_tools_runtime()
    assert out.ok is False
    assert "A 股" in out.evidence or "US" in out.evidence  # Should mention not supported for US


def test_probe_ticker_stub():
    facade = _stub_tool_facade()
    wl_repo = MagicMock()
    wl = WatchlistApplicationService(wl_repo)
    users = MagicMock()
    configure_quant_tools(
        QuantToolRuntime(
            tool_facade_service=facade,
            watchlist_service=wl,
            user_repository=users,
        )
    )
    try:
        out = qt.probe_ticker.invoke({"ticker": "600519"})
    finally:
        qt.reset_quant_tools_runtime()
    assert out.ok is True


def test_get_stock_news_stub():
    facade = _stub_tool_facade()
    wl_repo = MagicMock()
    wl = WatchlistApplicationService(wl_repo)
    users = MagicMock()
    configure_quant_tools(
        QuantToolRuntime(
            tool_facade_service=facade,
            watchlist_service=wl,
            user_repository=users,
        )
    )
    try:
        out = qt.get_stock_news.invoke({"ticker": "600519"})
    finally:
        qt.reset_quant_tools_runtime()
    assert out.evidence


def test_get_user_watchlist_user_missing():
    facade = _stub_tool_facade()
    wl_repo = MagicMock()
    wl = WatchlistApplicationService(wl_repo)
    users = MagicMock()
    configure_quant_tools(
        QuantToolRuntime(
            tool_facade_service=facade,
            watchlist_service=wl,
            user_repository=users,
        )
    )
    try:
        out = qt.get_user_watchlist.invoke({"user_id": 999})
    finally:
        qt.reset_quant_tools_runtime()
    assert out.ok is False