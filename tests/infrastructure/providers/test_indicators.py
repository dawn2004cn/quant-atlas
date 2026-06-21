import pytest
from app.infrastructure.providers.indicators import TaIndicatorProvider
from app.infrastructure.providers.rust_indicators import RustIndicatorProvider

@pytest.fixture
def sample_history():
    return [
        {"date": f"2024-01-{i+1:02d}", "open": 10+i, "high": 12+i, "low": 9+i, "close": 11+i, "volume": 1000}
        for i in range(30)
    ]

def test_ta_indicator_provider(sample_history):
    """Test TA-Lib based indicators."""
    provider = TaIndicatorProvider()
    result = provider.calculate(sample_history)
    assert isinstance(result, dict)
    assert 'ma20' in result
    assert 'macd' in result

def test_rust_indicator_provider(sample_history):
    """Test Rust based indicators."""
    try:
        provider = RustIndicatorProvider()
        result = provider.calculate(sample_history)
        assert isinstance(result, dict)
        assert 'ma20' in result
    except ImportError:
        pytest.skip("Rust extensions not available")
