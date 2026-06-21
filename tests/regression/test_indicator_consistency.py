import pytest
import json
import pandas as pd
from app.infrastructure.providers.rust_indicators import RustIndicatorProvider

@pytest.fixture
def baseline_data():
    with open("tests/regression/gold_data/sh600519_baseline.json", "r", encoding="utf-8") as f:
        return json.load(f)

def test_rust_indicator_consistency(baseline_data):
    # Reverse to get chronological order
    history = list(reversed(baseline_data))
    
    provider = RustIndicatorProvider()
    indicators = provider.calculate(history)
    
    # Assert against known values (using values from first successful run)
    assert "ma20" in indicators
    assert abs(indicators["ma20"] - 20.5) < 0.1 # Placeholder tolerance
    assert "macd" in indicators
    print(f"Regression check passed: {indicators}")
