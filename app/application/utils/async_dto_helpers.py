from __future__ import annotations
"""Convenience utilities for using new async and DTO patterns.

This module provides easy-to-use helpers for migrating existing code
to use the new architecture.
"""


from typing import Any, TypeVar, Generic
from collections.abc import Callable

T = TypeVar('T')

from app.domain.dto import (
    QuoteDTO,
    SignalDTO,
    PositionDTO,
    RiskAssessmentDTO,
    APIResponse,
    MarketSentimentDTO,
)

# Type alias for callable that returns dict (old style)
DictFunc = Callable[..., dict]

# Type alias for callable that returns DTO (new style)
DTOFunc = Callable[..., Any]


class DTOWrapper(Generic[T]):
    """Wrapper to convert dict-returning functions to return DTOs.

    Usage:
        @DTOWrapper(QuoteDTO)
        def get_quote(code: str) -> dict:
            return service.get_quote(code)

        # Now returns QuoteDTO instead of dict
        quote = await get_quote('600519')
    """

    def __init__(self, dto_class: type[T], wrapper_name: str = ""):
        self._dto_class = dto_class
        self._name = wrapper_name or dto_class.__name__

    def __call__(self, func: DictFunc) -> DTOFunc:
        """Wrap the function."""
        async def async_wrapper(*args, **kwargs) -> T:
            result = await func(*args, **kwargs) if hasattr(func, '__call__') else func(*args, **kwargs)
            if isinstance(result, self._dto_class):
                return result
            return self._dto_class(**result) if result else None

        def sync_wrapper(*args, **kwargs) -> T:
            result = func(*args, **kwargs)
            if isinstance(result, self._dto_class):
                return result
            return self._dto_class(**result) if result else None

        # Return async or sync based on whether func is async
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper


def convert_to_dto(dto_class: type[T], data: dict | None) -> T | None:
    """Convert dict data to DTO instance."""
    if data is None:
        return None
    if isinstance(data, dto_class):
        return data
    return dto_class(**data)


def convert_list_to_dto(dto_class: type[T], items: list[dict]) -> list[T]:
    """Convert list of dicts to list of DTOs."""
    return [convert_to_dto(dto_class, item) for item in items if item]


def wrap_response(data: Any = None, error: str | None = None) -> APIResponse:
    """Create standardized API response."""
    if error:
        return APIResponse.error_response(error, data)
    return APIResponse.ok(data)


# ==================== Quick conversion helpers ====================

def dict_to_quote(data: dict) -> QuoteDTO | None:
    """Convert dict to QuoteDTO."""
    return convert_to_dto(QuoteDTO, data)


def dict_to_signal(data: dict) -> SignalDTO | None:
    """Convert dict to SignalDTO."""
    return convert_to_dto(SignalDTO, data)


def dict_to_position(data: dict) -> PositionDTO | None:
    """Convert dict to PositionDTO."""
    return convert_to_dto(PositionDTO, data)


def dict_to_risk(data: dict) -> RiskAssessmentDTO | None:
    """Convert dict to RiskAssessmentDTO."""
    return convert_to_dto(RiskAssessmentDTO, data)


def dict_to_sentiment(data: dict) -> MarketSentimentDTO | None:
    """Convert dict to MarketSentimentDTO."""
    return convert_to_dto(MarketSentimentDTO, data)


# ==================== Service enhancement decorator ====================

def add_async_methods(cls):
    """Class decorator to add async versions of sync methods.

    Usage:
        @add_async_methods
        class MyService:
            def get_data(self, key):
                return self._cache.get(key)

            # Now also has:
            # async def get_data_async(self, key)
    """
    import asyncio
    from functools import wraps

    original_methods = {}
    for name in dir(cls):
        attr = getattr(cls, name)
        if callable(attr) and not name.startswith('_') and not name.endswith('_async'):
            original_methods[name] = attr

    for name, method in original_methods.items():
        async_name = f"{name}_async"

        @wraps(method)
        async def async_wrapper(self, *args, **kwargs):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                lambda: method(self, *args, **kwargs)
            )

        setattr(cls, async_name, async_wrapper)

    return cls


# ==================== Event publishing shortcuts ====================

def emit_signal(code: str, signal_type: str, strength: int, **kwargs):
    """Quick emit a signal event."""
    from app.application.events import publish_event, EventType

    publish_event(
        EventType.SIGNAL_GENERATED,
        payload={
            'code': code,
            'type': signal_type,
            'strength': strength,
            **kwargs
        },
        source='quick_emit'
    )


def emit_alert(code: str, level: str, message: str, **kwargs):
    """Quick emit a risk alert event."""
    from app.application.events import publish_event, EventType

    publish_event(
        EventType.RISK_ALERT,
        payload={
            'code': code,
            'level': level,
            'message': message,
            **kwargs
        },
        source='quick_emit'
    )


def emit_task_status(task_id: str, status: str, **kwargs):
    """Quick emit a task status event."""
    from app.application.events import publish_event, EventType

    event_type = EventType.TASK_COMPLETED if status == 'success' else EventType.TASK_FAILED
    publish_event(
        event_type,
        payload={
            'task_id': task_id,
            'status': status,
            **kwargs
        },
        source='quick_emit'
    )
