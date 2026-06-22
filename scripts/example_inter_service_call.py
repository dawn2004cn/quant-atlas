#!/usr/bin/env python3
"""Example: Inter-service communication in quant-atlas microservices.

This example demonstrates how services call each other using:
1. ServiceClient (HTTP) - for synchronous calls
2. Event Bus - for async event-driven communication
3. DualWriteProxy - for gradual traffic migration

Example flow:
  1. Strategy Service needs market data to run backtest
  2. Strategy calls Market Data Service via ServiceClient
  3. Market Data Service publishes QuoteUpdatedEvent
  4. Strategy Service subscribes to QuoteUpdatedEvent
  5. DualWriteProxy gradually shifts traffic from monolith to service
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")

from app.core.service_discovery import (
    get_service_registry,
    get_service_client,
    register_service,
)


def example_http_service_call():
    """Example: Strategy service calls Market Data service via HTTP."""
    print("=" * 60)
    print("Example 1: HTTP Service-to-Service Call")
    print("=" * 60)
    
    # 1. Register services (normally done at app startup)
    register_service(
        name="market_data",
        url="http://localhost:5101",
        health_path="/health",
        timeout=10.0,
    )
    
    # 2. Get client for Market Data service
    client = get_service_client("market_data")
    if not client:
        print("  [ERROR] market_data service not registered")
        return
    
    print(f"  Client created for: {client.service_name}")
    print(f"  Endpoint: {client.endpoint.url}")
    
    # 3. Make a call to Market Data service
    # In real code, this would be:
    #   result = client.get("/api/v1/market/quotes/SH000001")
    #   if result.success:
    #       quote = result.data
    #       ...
    print("  Example call: client.get('/api/v1/market/quotes/SH000001')")
    print("  (Service would need to be running for actual call)")


def example_event_driven():
    """Example: Async event-driven communication via Event Bus."""
    print("\n" + "=" * 60)
    print("Example 2: Event-Driven Communication")
    print("=" * 60)
    
    from app.core.event_bus import get_event_bus, Event
    from dataclasses import dataclass

    @dataclass
    class QuoteUpdatedEvent(Event):
        """Published when a quote is updated."""
        symbol: str = ""
        price: float = 0.0

    @dataclass
    class StrategyCalculatedEvent(Event):
        """Published when strategy finishes calculation."""
        strategy_id: str = ""
        signal: str = ""
        confidence: float = 0.0
    
    bus = get_event_bus()
    
    # Subscribe to quote updates
    def on_quote_updated(event):
        print(f"  [EVENT] Quote updated: {event.symbol} = {event.price}")
    
    bus.subscribe(QuoteUpdatedEvent, on_quote_updated)
    print("  Subscribed to QuoteUpdatedEvent")
    
    # Create and publish event
    event = QuoteUpdatedEvent(symbol="SH000001", price=3500.0)
    bus.publish(event)
    print(f"  Published: {event.symbol} = {event.price}")


def example_dual_write_migration():
    """Example: Gradual traffic migration using DualWriteProxy."""
    print("\n" + "=" * 60)
    print("Example 3: Gradual Traffic Migration (Strangler Fig)")
    print("=" * 60)
    
    from app.infrastructure.gateway.dual_write_middleware import DualWriteProxy
    
    proxy = DualWriteProxy()
    
    # Register market data service
    proxy.register_service(
        "market_data",
        "http://localhost:5101",
        traffic_split=0.0,  # Start: 100% monolith
    )
    
    print("  Phase 1: 100% monolith, 0% service")
    print(f"    Traffic split: {proxy._traffic_split['market_data']}")
    
    # Gradually increase traffic to service
    proxy.set_traffic_split("market_data", 0.1)
    print("\n  Phase 2: 90% monolith, 10% service (validation)")
    print(f"    Traffic split: {proxy._traffic_split['market_data']}")
    
    proxy.set_traffic_split("market_data", 0.5)
    print("\n  Phase 3: 50% monolith, 50% service (canary)")
    print(f"    Traffic split: {proxy._traffic_split['market_data']}")
    
    # Check if ready for full cutover
    # In real code, this would check confidence metrics:
    #   if proxy.should_cutover("market_data"):
    #       proxy.set_traffic_split("market_data", 1.0)
    print("\n  Phase 4: Full cutover (when confidence > 99%)")
    print("    proxy.should_cutover('market_data') -> False (no comparisons yet)")


def example_service_discovery():
    """Example: Using service discovery for dynamic endpoint resolution."""
    print("\n" + "=" * 60)
    print("Example 4: Service Discovery")
    print("=" * 60)
    
    registry = get_service_registry()
    
    # List all registered services
    services = registry.list_services()
    print(f"  Registered services: {services}")
    
    # Get URL and health for each service
    for svc_name in services:
        url = registry.get_url(svc_name)
        health_status = registry.check_health(svc_name)
        print(f"  {svc_name}: {url} (status: {health_status.value})")


def main():
    """Run all examples."""
    print("quant-atlas Microservices Communication Examples")
    print("=" * 60)
    
    example_http_service_call()
    example_event_driven()
    example_dual_write_migration()
    example_service_discovery()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
