import pytest
from app.infrastructure.providers.cn_tdx_provider import create_tdx_provider
from app.domain.enums import MarketCode

def test_cn_tdx_provider():
    """Test TDX provider (requires local TDX files)."""
    provider = create_tdx_provider()
    if provider is None:
        pytest.skip("TDX_ROOT_PATH not configured or TDX not available")
        
    symbols = provider.get_all_symbols(MarketCode.CN)
    assert isinstance(symbols, list)
    if symbols:
        test_code = symbols[0][-6:]
        history = provider.get_stock_history(test_code, limit=5)
        assert isinstance(history, list)
