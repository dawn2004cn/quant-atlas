import pytest
from app.infrastructure.providers.cn_akshare_fundamentals import CnAkShareFundamentalsProvider

@pytest.fixture
def provider():
    return CnAkShareFundamentalsProvider()

def test_fetch_financial_bundle(provider):
    """Test fetching financial bundle for a stock."""
    # Ping An
    data = provider.fetch_financial_bundle('000001')
    assert isinstance(data, dict)
    assert data.get('symbol') == '000001'
    # Check for core statements
    assert 'balance_sheet' in data or 'income_statement' in data

def test_fetch_stock_industry(provider):
    """Test fetching industry for a stock."""
    industry = provider.fetch_stock_industry('600519')
    assert isinstance(industry, str)
    # Even if unknown, it shouldn't crash
    assert len(industry) > 0

def test_fetch_research_reports(provider):
    """Test fetching research reports."""
    reports, error = provider.fetch_research_reports('000001', limit=5)
    assert isinstance(reports, list)
    assert error is None or isinstance(error, str)
