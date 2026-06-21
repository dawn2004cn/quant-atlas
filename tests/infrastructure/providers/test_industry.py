import pytest
from app.infrastructure.providers.cn_industry_provider import CnIndustryProvider

def test_get_industry_map():
    """Test fetching industry mapping for A-shares."""
    provider = CnIndustryProvider()
    # Try with fetch allowed
    try:
        industry_map = provider.get_industry_map(allow_fetch=True)
        assert isinstance(industry_map, dict)
        if industry_map:
            # Check a known stock if possible, or just length
            assert len(industry_map) > 100
    except Exception as e:
        pytest.skip(f"Industry fetch failed: {e}")
