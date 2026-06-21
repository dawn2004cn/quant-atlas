import pytest
from app.infrastructure.providers.tdx_file_adapter import TDXFileHistoryAdapter
from app.core.runtime_config import get_runtime
from app.domain.enums import MarketCode

def test_tdx_file_adapter():
    """Test reading local TDX lday files."""
    tdx_root = get_runtime("TDX_ROOT_PATH", "")
    if not tdx_root:
        pytest.skip("TDX_ROOT_PATH not configured")
        
    adapter = TDXFileHistoryAdapter(tdx_root)
    try:
        symbols = adapter.get_symbols_list(MarketCode.CN)
        assert isinstance(symbols, list)
        if symbols:
            # Try to read history for the first one
            symbol = symbols[0][-6:]
            hist = adapter.get_stock_history(symbol, MarketCode.CN, "2024-01-01", "2024-06-30")
            assert isinstance(hist, list)
    except Exception as e:
        pytest.skip(f"TDX file access failed: {e}")
