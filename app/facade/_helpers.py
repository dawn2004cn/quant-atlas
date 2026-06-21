from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Iterator

from app.application.errors import ValidationError
from app.domain.enums import MarketCode


def parse_market(market: str | MarketCode) -> MarketCode:
    if isinstance(market, MarketCode):
        return market
    try:
        return MarketCode(str(market).upper())
    except ValueError as exc:
        raise ValidationError(f"Invalid market: {market}") from exc


def validation_error_from_pydantic(exc: Exception) -> ValidationError:
    """Map Pydantic validation failures to application ValidationError."""
    return ValidationError(str(exc))


@contextmanager
def observe_facade(facade: str, method: str) -> Iterator[None]:
    """Record facade call duration and error counts (no-op without Prometheus)."""
    from app.core.metrics import FACADE_CALL_DURATION, FACADE_ERRORS

    started = time.perf_counter()
    try:
        yield
    except Exception as exc:
        if FACADE_ERRORS is not None:
            FACADE_ERRORS.labels(
                facade=facade,
                method=method,
                error_type=type(exc).__name__,
            ).inc()
        raise
    finally:
        if FACADE_CALL_DURATION is not None:
            FACADE_CALL_DURATION.labels(facade=facade, method=method).observe(
                time.perf_counter() - started
            )
