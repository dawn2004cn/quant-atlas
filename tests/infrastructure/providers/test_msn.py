import pytest
from app.infrastructure.providers.msn_market_index import MsnMarketIndexProvider

def test_msn_market_index():
    """Test MSN index provider."""
    provider = MsnMarketIndexProvider()
    try:
        data = provider.get_quotes(["sh000001"])
        assert isinstance(data, list)
        if data:
            assert 'price' in data[0] or 'close' in data[0]
    except Exception as e:
        if "404" in str(e):
            pytest.skip("MSN API returned 404 - might be blocked or changed")
        raise e
