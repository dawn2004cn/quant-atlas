from __future__ import annotations
"""Example usage of new architecture services.

This module demonstrates how to use the new domain-model-based services,
DTOs, and event-driven architecture.

Usage:
    from app.examples.new_architecture_example import run_examples
    run_examples()
"""


import asyncio
from datetime import datetime


async def signal_generation_example():
    """Example: Generate trading signals using domain models."""
    print("\n=== Signal Generation Example ===")

    from app.modules.system.services.architecture_integration import get_signal_service

    signal_service = get_signal_service()

    signal = await signal_service.generate_breakout_signal(
        code="600519",
        name="贵州茅台",
        price=1800.0,
        volume=1000000,
        high=1820.0,
        low=1780.0,
        open_price=1790.0,
        prev_close=1795.0,
        avg_volume_20d=800000,
    )

    print(f"Generated signal: {signal.code} - {signal.signal_type}")
    print(f"  Strength: {signal.strength}")
    print(f"  Confidence: {signal.confidence}%")
    print(f"  Reason: {signal.reason}")

    return signal


async def portfolio_management_example():
    """Example: Manage portfolio using domain models."""
    print("\n=== Portfolio Management Example ===")

    from app.modules.system.services.architecture_integration import get_portfolio_service

    portfolio_service = await get_portfolio_service()

    position = await portfolio_service.add_position(
        code="600519",
        name="贵州茅台",
        quantity=100,
        price=1700.0,
        side="long",
        tags=["白酒", "龙头"],
    )
    print(f"Added position: {position.code} - {position.quantity} shares")

    await portfolio_service.update_position_price("600519", 1800.0)

    summary = portfolio_service.get_summary()
    print(f"Portfolio value: {summary.total_value:.2f}")
    print(f"Total PnL: {summary.total_pnl:.2f} ({summary.pnl_pct:.2f}%)")
    print(f"Positions: {summary.position_count}")

    metrics = portfolio_service.get_metrics()
    print(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
    print(f"Win Rate: {metrics.win_rate*100:.1f}%")

    return portfolio_service


async def risk_assessment_example():
    """Example: Assess risk using domain models."""
    print("\n=== Risk Assessment Example ===")

    from app.modules.system.services.architecture_integration import get_risk_service

    risk_service = await get_risk_service()

    position_risk = await risk_service.assess_position_risk(
        code="600519",
        name="贵州茅台",
        quantity=100,
        price=1800.0,
        total_portfolio_value=100000.0,
        sector="consumer",
    )

    print(f"Position risk: {position_risk.code}")
    print(f"  Risk Level: {position_risk.risk_level}")
    print(f"  Risk Score: {position_risk.risk_score:.1f}")
    print(f"  VaR (95%): {position_risk.var_95:.2f}")

    portfolio_risk = await risk_service.assess_portfolio_risk(
        positions=[
            {"code": "600519", "value": 180000, "volatility": 0.25, "sector": "consumer"},
            {"code": "000001", "value": 120000, "volatility": 0.30, "sector": "finance"},
        ],
        total_value=300000.0,
    )

    print(f"Portfolio risk: {portfolio_risk.risk_level}")
    print(f"  VaR (95%): {portfolio_risk.var_95:.2f}")
    print(f"  Warnings: {len(portfolio_risk.warnings)}")

    return risk_service


async def stock_scanner_example():
    """Example: Scan stocks using domain models."""
    print("\n=== Stock Scanner Example ===")

    from app.modules.system.services.architecture_integration import get_scanner_service

    scanner = get_scanner_service()

    stocks = [
        {"code": "600519", "name": "贵州茅台", "price": 1800, "volume": 1000000, "high": 1820, "low": 1780, "open": 1790, "prev_close": 1795, "avg_volume_20d": 800000},
        {"code": "000001", "name": "平安银行", "price": 12.5, "volume": 50000000, "high": 12.8, "low": 12.2, "open": 12.3, "prev_close": 12.1, "avg_volume_20d": 30000000},
        {"code": "600036", "name": "招商银行", "price": 35.0, "volume": 20000000, "high": 35.5, "low": 34.5, "open": 34.8, "prev_close": 34.2, "avg_volume_20d": 15000000},
    ]

    result = await scanner.scan_breakout_stocks(
        stocks=stocks,
        min_volume_ratio=1.5,
        min_price_change=3.0,
    )

    print(f"Scanned {result.total_scanned} stocks, found {result.matched} signals")
    for signal in result.signals:
        print(f"  {signal.code}: {signal.signal_type} - {signal.strength}")

    return scanner


async def event_driven_example():
    """Example: Using events to decouple services."""
    print("\n=== Event-Driven Example ===")

    from app.application.events import get_event_bus, EventType, publish_event

    event_bus = get_event_bus()

    @event_bus.subscribe(EventType.SIGNAL_GENERATED)
    def handle_signal(event):
        print(f"  Event handler: Received signal for {event.payload.get('code')}")

    @event_bus.subscribe(EventType.POSITION_OPENED)
    def handle_position(event):
        print(f"  Event handler: Position opened - {event.payload.get('code')}")

    await publish_event(
        EventType.SIGNAL_GENERATED,
        {"code": "600519", "signal_type": "breakout"},
        source="example"
    )

    await publish_event(
        EventType.POSITION_OPENED,
        {"code": "600519", "quantity": 100},
        source="example"
    )

    print("Events published and handled")


async def run_examples():
    """Run all examples."""
    print("=" * 60)
    print("New Architecture Services Examples")
    print("=" * 60)

    await signal_generation_example()
    await portfolio_management_example()
    await risk_assessment_example()
    await stock_scanner_example()
    await event_driven_example()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_examples())