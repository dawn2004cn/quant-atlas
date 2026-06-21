"""Contract tests for MarketDataFacade."""

import pytest
from unittest.mock import MagicMock
from app.application.facades.market_data_facade import MarketDataFacade
from app.presentation.dto.response import ResponseEnvelope

def test_get_market_intelligence_contract():
    # Mock services
    mock_basic = MagicMock()
    mock_market = MagicMock()
    
    # Setup mock behavior
    mock_market.get_quotes.return_value = {"price": 10.0}
    mock_basic.longhu_for_stock.return_value = []
    mock_basic.get_tdx_local_cn_snapshot.return_value = {"ok": True}
    
    facade = MarketDataFacade(mock_basic, mock_market)
    result = facade.get_market_intelligence("600519")
    
    # Contract validation
    assert "quotes" in result
    assert "longhu" in result
    assert "fundamentals" in result
    assert "intelligence_summary" in result
    
    # Ensure standard envelope format
    envelope = ResponseEnvelope.success(result)
    assert envelope.code == 200
    assert envelope.data == result
