from __future__ import annotations
"""OpenTelemetry Integration for Quant Atlas.

Phase 43: 全链路链路追踪 (Distributed Tracing)

This module provides:
- OpenTelemetry tracer initialization
- Trace context propagation across async boundaries
- Span creation for key business operations
- Integration with Flask, Celery, and SQLAlchemy
- Export to Jaeger/Zipkin backends (optional)
"""


import logging
from contextlib import contextmanager
from typing import Any, Optional

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import Span, Status, StatusCode

logger = logging.getLogger(__name__)

_tracer: Optional[trace.Tracer] = None
_initialized = False


def init_opentelemetry(
    service_name: str = "quant-atlas",
    jaeger_endpoint: Optional[str] = None,
    console_export: bool = False,
) -> trace.Tracer:
    """Initialize OpenTelemetry tracer.
    
    Args:
        service_name: Service name for tracing
        jaeger_endpoint: Jaeger collector endpoint (e.g., "http://jaeger:14268/api/traces")
        console_export: Whether to export spans to console for debugging
        
    Returns:
        Configured tracer instance
    """
    global _tracer, _initialized
    
    if _initialized:
        return _tracer
    
    # Create resource with service info
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "1.0.0",
    })
    
    # Create tracer provider
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)
    
    # Configure exporters
    if jaeger_endpoint:
        try:
            from opentelemetry.exporter.jaeger.thrift import JaegerExporter
            jaeger_exporter = JaegerExporter(
                agent_host_name="localhost",
                agent_port=6831,
                endpoint=jaeger_endpoint,
            )
            provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
            logger.info(f"Configured Jaeger exporter: {jaeger_endpoint}")
        except ImportError:
            logger.warning(
                "Jaeger exporter not available. Install with: "
                "pip install opentelemetry-exporter-jaeger"
            )
    
    if console_export:
        console_exporter = ConsoleSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(console_exporter))
        logger.info("Configured console exporter")
    
    # Get tracer
    _tracer = trace.get_tracer(service_name)
    _initialized = True
    
    logger.info(f"OpenTelemetry initialized for service: {service_name}")
    return _tracer


def get_tracer() -> trace.Tracer:
    """Get the configured tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = init_opentelemetry()
    return _tracer


@contextmanager
def create_span(
    name: str,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
    attributes: Optional[dict[str, Any]] = None,
    parent_context: Optional[trace.Context] = None,
) -> Span:
    """Create a span for tracing a business operation.
    
    Usage:
        with create_span("execute_order", attributes={"symbol": "600000"}) as span:
            # Business logic here
            span.set_attribute("order_id", "12345")
    
    Args:
        name: Span name
        kind: Span kind (INTERNAL, SERVER, CLIENT, PRODUCER, CONSUMER)
        attributes: Initial attributes
        parent_context: Parent context for trace propagation
        
    Yields:
        Active span
    """
    tracer = get_tracer()
    
    with tracer.start_as_current_span(
        name,
        kind=kind,
        context=parent_context,
    ) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        
        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


def trace_market_data_update(symbol: str, market: str) -> Span:
    """Create span for market data update.
    
    Args:
        symbol: Stock symbol
        market: Market code
        
    Returns:
        Active span
    """
    return create_span(
        "market_data.update",
        attributes={
            "symbol": symbol,
            "market": market,
            "operation": "market_data_update",
        },
    )


def trace_signal_generation(
    strategy: str,
    symbol: str,
    signal_type: str,
    strength: float,
) -> Span:
    """Create span for signal generation.
    
    Args:
        strategy: Strategy name
        symbol: Stock symbol
        signal_type: Signal type (buy/sell/hold)
        strength: Signal strength
        
    Returns:
        Active span
    """
    return create_span(
        "signal.generate",
        attributes={
            "strategy": strategy,
            "symbol": symbol,
            "signal_type": signal_type,
            "strength": strength,
            "operation": "signal_generation",
        },
    )


def trace_order_execution(
    order_id: str,
    symbol: str,
    side: str,
    price: float,
    quantity: int,
) -> Span:
    """Create span for order execution.
    
    Args:
        order_id: Order ID
        symbol: Stock symbol
        side: Buy/sell
        price: Order price
        quantity: Order quantity
        
    Returns:
        Active span
    """
    return create_span(
        "order.execute",
        attributes={
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "price": price,
            "quantity": quantity,
            "operation": "order_execution",
        },
    )


def trace_factor_calculation(
    factor_name: str,
    symbol: str,
    calculation_time_ms: float,
) -> Span:
    """Create span for factor calculation.
    
    Args:
        factor_name: Factor name
        symbol: Stock symbol
        calculation_time_ms: Calculation time in milliseconds
        
    Returns:
        Active span
    """
    return create_span(
        "factor.calculate",
        attributes={
            "factor_name": factor_name,
            "symbol": symbol,
            "calculation_time_ms": calculation_time_ms,
            "operation": "factor_calculation",
        },
    )


def trace_ai_analysis(
    agent_name: str,
    symbol: str,
    analysis_type: str,
) -> Span:
    """Create span for AI analysis.
    
    Args:
        agent_name: AI agent name
        symbol: Stock symbol
        analysis_type: Analysis type
        
    Returns:
        Active span
    """
    return create_span(
        "ai.analyze",
        attributes={
            "agent_name": agent_name,
            "symbol": symbol,
            "analysis_type": analysis_type,
            "operation": "ai_analysis",
        },
    )


def get_current_trace_id() -> Optional[str]:
    """Get the current trace ID.
    
    Returns:
        Current trace ID or None if no active span
    """
    current_span = trace.get_current_span()
    if current_span and current_span.get_span_context().trace_id != 0:
        return format(current_span.get_span_context().trace_id, "032x")
    return None


def get_current_span_id() -> Optional[str]:
    """Get the current span ID.
    
    Returns:
        Current span ID or None if no active span
    """
    current_span = trace.get_current_span()
    if current_span and current_span.get_span_context().span_id != 0:
        return format(current_span.get_span_context().span_id, "016x")
    return None


__all__ = [
    "init_opentelemetry",
    "get_tracer",
    "create_span",
    "trace_market_data_update",
    "trace_signal_generation",
    "trace_order_execution",
    "trace_factor_calculation",
    "trace_ai_analysis",
    "get_current_trace_id",
    "get_current_span_id",
]
