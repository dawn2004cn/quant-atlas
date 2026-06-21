from __future__ import annotations
"""API DTO validation utilities."""


import functools
import inspect
import logging
from typing import Any, Callable, Type

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from app.application.errors import ExternalServiceError, ValidationError as AppValidationError


from app.core.logger import get_logger

logger = get_logger(__name__)


def validate_request(dto_class: Type[BaseModel], source: str = "json"):
    """Decorator to validate request parameters against a Pydantic DTO.

    Usage:
        @blueprint.get("/stocks")
        @validate_request(StockListRequestDTO)
        def list_stocks(request: StockListRequestDTO):
            # request is already validated
            return do_something(request.limit, request.offset)

    Args:
        dto_class: Pydantic BaseModel class for validation
        source: Source of data - "json" (request body) or "args" (query params)
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from flask import request

            try:
                if source == "json":
                    data = request.get_json(silent=True) or {}
                    validated = dto_class.model_validate(data)
                    # Replace the first argument (self) with validated request
                    return func(*args, validated, **kwargs)
                else:
                    # Query parameters — inject as ``req`` kwarg when the handler declares it
                    # (keeps Flask path params like market/symbol in **kwargs).
                    validated = dto_class.model_validate(request.args.to_dict())
                    if "req" in inspect.signature(func).parameters:
                        return func(*args, req=validated, **kwargs)
                    return func(*args, validated, **kwargs)
            except PydanticValidationError as exc:
                logger.warning("Request validation failed for %s: %s", dto_class.__name__, exc)
                raise AppValidationError(
                    "validation_failed",
                    details={"errors": exc.errors()},
                ) from exc
            except AppValidationError:
                raise
            except Exception as exc:
                logger.error("Unexpected validation error: %s", exc)
                raise ExternalServiceError(
                    "request_validation_internal_error",
                    details={"reason": str(exc)},
                ) from exc

        return wrapper
    return decorator


def validate_response(dto_class: Type[BaseModel]):
    """Decorator to validate response data against a Pydantic DTO.

    Usage:
        @validate_response(StockListResponseDTO)
        def get_stocks():
            return some_raw_dict
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if isinstance(result, tuple) and len(result) >= 2:
                data = result[0]
                if isinstance(data, dict):
                    try:
                        validated = dto_class.model_validate(data)
                        return validated.model_dump(), result[1]
                    except PydanticValidationError as exc:
                        logger.warning("Response validation failed: %s", exc)
            return result
        return wrapper
    return decorator


__all__ = ["validate_request", "validate_response"]