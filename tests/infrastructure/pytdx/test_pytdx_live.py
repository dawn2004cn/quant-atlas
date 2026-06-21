"""Pytdx 联网冒烟测试（需可访问通达信行情服务器）。"""

from __future__ import annotations

import pytest

from app.infrastructure.pytdx.runtime import pytdx_available


@pytest.mark.skipif(not pytdx_available(), reason="pytdx not installed")
def test_pytdx_hq_quotes_and_bars():
    from app.modules.data.services.pytdx_market_data_service import (
        get_pytdx_market_data_service,
    )

    svc = get_pytdx_market_data_service()
    status = svc.connection_status()
    assert status.get("hq", {}).get("connected") is True

    quotes = svc.get_quotes(["600519", "000001"])
    assert len(quotes) >= 1
    assert quotes[0].get("code")

    bars = svc.get_daily_bars("600519", count=5)
    assert isinstance(bars, list)
    if bars:
        assert "datetime" in bars[0] or "open" in bars[0]


@pytest.mark.skipif(not pytdx_available(), reason="pytdx not installed")
def test_pytdx_finance_info():
    from app.modules.data.services.pytdx_market_data_service import (
        get_pytdx_market_data_service,
    )

    fin = get_pytdx_market_data_service().get_finance_info("600519")
    assert fin is None or isinstance(fin, dict)
