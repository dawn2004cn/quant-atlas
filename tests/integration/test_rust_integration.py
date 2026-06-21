from app.core.container import Container
from app.domain.enums import MarketCode

def test_rust_integration():
    print("Testing Rust Indicator Integration...")
    container = Container()
    
    # Get the stock service (which now has RustIndicatorProvider injected)
    stock_service = container.stock_service()
    
    # Create some mock history
    history = [
        {"date": f"2023-01-{i:02d}", "close": float(i)} for i in range(1, 31)
    ]
    
    # Calculate indicators
    print("Calculating indicators via Rust...")
    indicators = stock_service.get_indicators(history)
    
    print(f"Indicators calculated: {indicators.keys()}")
    for k, v in indicators.items():
        print(f"  {k}: {v}")
    
    assert "ma20" in indicators
    assert "macd" in indicators
    assert "rsi14" in indicators
    print("Test PASSED: Rust integration verified in StockApplicationService.")

if __name__ == "__main__":
    test_rust_integration()
