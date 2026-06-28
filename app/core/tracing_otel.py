from __future__ import annotations
"""OpenTelemetry distributed tracing for full request lifecycle."""


import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any
from collections.abc import Callable


from app.core.logger import get_logger

logger = get_logger(__name__)

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    logger.warning("OpenTelemetry not installed. pip install opentelemetry-api opentelemetry-sdk")


@dataclass
class TraceContext:
    """Trace context for passing across service calls."""
    trace_id: str = ""
    span_id: str = ""
    parent_span_id: str | None = None

    def to_dict(self) -> dict[str, str]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id
        }

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> TraceContext:
        return cls(
            trace_id=data.get("trace_id", ""),
            span_id=data.get("span_id", "")
        )


class TracingService:
    """Distributed tracing service."""

    _instance = None
    _tracer = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def initialize(
        self,
        service_name: str = "quant-atlas",
        jaeger_endpoint: str | None = None,
        enable_console: bool = False
    ) -> None:
        """Initialize tracing."""
        if self._initialized:
            return

        if not OTEL_AVAILABLE:
            logger.warning("OpenTelemetry not available, tracing disabled")
            self._initialized = True
            return

        try:
            resource = Resource.create({SERVICE_NAME: service_name})
            provider = TracerProvider(resource=resource)

            if enable_console:
                provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

            if jaeger_endpoint:
                jaeger_exporter = JaegerExporter(endpoint=jaeger_endpoint)
                provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))

            trace.set_tracer_provider(provider)
            self._tracer = trace.get_tracer(__name__)
            self._initialized = True
            logger.info(f"Tracing initialized for {service_name}")

        except Exception as e:
            logger.warning(f"Failed to initialize tracing: {e}")
            self._initialized = True

    @contextmanager
    def start_span(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
        context: TraceContext | None = None
    ):
        """Start a new span.

        Usage:
            with tracing.start_span("process_stock_data", {"symbol": "600519"}):
                # Do work
                pass
        """
        if not self._initialized or not self._tracer:
            yield None
            return

        with self._tracer.start_as_current_span(name) as span:
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, str(value))

            if context and context.trace_id:
                span.set_attribute("trace_id", context.trace_id)

            try:
                yield span
            except Exception as e:
                span.set_attribute("error", str(e))
                span.record_exception(e)
                raise

    def create_context(self) -> TraceContext:
        """Create a new trace context."""
        return TraceContext(
            trace_id=uuid.uuid4().hex[:16],
            span_id=uuid.uuid4().hex[:8]
        )

    def get_current_context(self) -> TraceContext | None:
        """Get current trace context from OpenTelemetry."""
        if not OTEL_AVAILABLE:
            return None

        current_span = trace.get_current_span()
        if current_span:
            return TraceContext(
                trace_id=format(current_span.context.trace_id, '032x')[:16],
                span_id=format(current_span.context.span_id, '016x')[:8]
            )
        return None


# Decorator for automatic tracing
def traced(
    operation_name: str = None,
    attributes: dict[str, Any] | None = None
):
    """Decorator to automatically trace function execution.

    Usage:
        @traced("fetch_stock_data")
        def fetch_stock(symbol):
            return stock_data
    """
    def decorator(func: Callable) -> Callable:
        name = operation_name or func.__name__

        if not OTEL_AVAILABLE:
            return func

        def wrapper(*args, **kwargs):
            tracer = TracingService()
            with tracer.start_span(name, attributes):
                return func(*args, **kwargs)

        return wrapper
    return decorator


# Global tracing service
_tracing_service: TracingService | None = None


def get_tracing_service() -> TracingService:
    """Get the global tracing service."""
    global _tracing_service
    if _tracing_service is None:
        _tracing_service = TracingService()
    return _tracing_service


def init_tracing(
    service_name: str = "quant-atlas",
    jaeger_endpoint: str | None = None,
    enable_console: bool = False
) -> None:
    """Initialize tracing service."""
    service = get_tracing_service()
    service.initialize(service_name, jaeger_endpoint, enable_console)


# Context manager for manual span management
@contextmanager
def trace_operation(name: str, **attributes):
    """Context manager for tracing operations.

    Usage:
        with trace_operation("api_request", method="GET", path="/api/stocks"):
            make_api_call()
    """
    service = get_tracing_service()
    with service.start_span(name, attributes) as span:
        yield span


__all__ = [
    "TracingService",
    "TraceContext",
    "traced",
    "get_tracing_service",
    "init_tracing",
    "trace_operation",
    "OTEL_AVAILABLE"
]
