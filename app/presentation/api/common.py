from __future__ import annotations

"""API v1 共享：权限校验、统一 JSON 成功体、市场枚举解析、服务检查装饰器。"""


import functools
from collections.abc import Callable
from typing import Any

from flask_login import current_user

from ...application.errors import ValidationError
from ...domain.enums import MarketCode
from .responses import serialize, success_response


def get_service(service_name: str) -> Any:
    """Get service instance by name.

    This is a simple service locator for dependency injection.
    In production, consider using a proper DI container.
    """
    from ...application.services.quant_agent_service import QuantAgentService

    service_map = {
        "quant_agent": QuantAgentService,
    }

    service_class = service_map.get(service_name.lower())
    if service_class:
        return service_class()
    raise ValueError(f"Unknown service: {service_name}")


def require_service(service_attr: str, service_name: str = None) -> Callable:
    """Decorator to check if a service is available before executing endpoint.

    Usage:
        @blueprint.get("/example")
        @login_required
        @require_service("signal_observation_service")
        def example_endpoint():
            # service is guaranteed to be available
            return ctx.signal_observation_service.do_something()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get ctx from function globals (injected by register_X_routes)
            ctx = func.__globals__.get('ctx')
            if ctx is None:
                raise ValidationError("context_unavailable")
            service = getattr(ctx, service_attr, None)
            if service is None:
                error_name = service_name or service_attr.replace('_service', '').replace('_', ' ')
                raise ValidationError(f"{error_name}_service_unavailable")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def ensure_service(ctx: Any, service_attr: str, service_name: str | None = None) -> Any:
    """Raise ``ValidationError`` (400) if optional service is missing.

    Prefer this over returning ``ok_response(..., error=...)`` so ``register_api_error_handlers``
    emits a consistent JSON error body.
    """
    service = getattr(ctx, service_attr, None)
    if service is None:
        error_name = service_name or service_attr.replace("_service", "").replace("_", " ")
        raise ValidationError(
            f"{error_name}_service_unavailable",
            details={"service": service_attr},
        )
    return service


# Alias for readability in route modules
require_ctx_service = ensure_service


def validate_required(value: Any, name: str) -> Any:
    """Validate that a required parameter is provided."""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError(f"{name}_required")
    return value


def validate_symbol(symbol: str) -> str:
    """Validate stock symbol parameter."""
    return validate_required(symbol, "symbol")


def validate_market(market: str) -> str:
    """Validate market parameter."""
    return validate_required(market, "market")


def require_research_write_role(fn=None):
    def _check():
        checker = getattr(current_user, "can_run_research_writes", None)
        if not callable(checker) or not checker():
            raise ValidationError("当前账号无权执行该研究型写操作（需管理员、开发者或研究员）")

    if fn is not None:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            _check()
            return fn(*args, **kwargs)
        return wrapper

    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            _check()
            return f(*args, **kwargs)
        return wrapper
    return decorator


def require_data_ingestion_role(fn=None):
    def _check():
        checker = getattr(current_user, "may_trigger_server_data_ingestion", None)
        if not callable(checker) or not checker():
            raise ValidationError("当前账号无权触发服务器侧数据入库（需管理员、开发者或研究员）")

    if fn is not None:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            _check()
            return fn(*args, **kwargs)
        return wrapper

    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            _check()
            return f(*args, **kwargs)
        return wrapper
    return decorator


def require_expensive_ai_role() -> None:
    fn = getattr(current_user, "may_run_expensive_ai_pipeline", None)
    if not callable(fn) or not fn():
        raise ValidationError("当前账号无权发起该 AI 操作（需管理员、开发者或研究员）")


def ok_response(*, legacy_alias_key: str | None = None, enable_legacy_alias: bool = False, **payload):
    """Canonical success response. Delegates to ``success_response``."""
    data = serialize(payload.pop("data", payload))
    return success_response(data=data, meta=payload or None)


def ok_collection(*, items, item_key: str = None, enable_legacy_alias: bool = False, **extra):
    return ok_response(data=items, **extra)


def ok_resource(*, resource, resource_key: str = None, enable_legacy_alias: bool = False, **extra):
    return ok_response(data=resource, **extra)


def parse_market(raw_value: str) -> MarketCode:
    try:
        return MarketCode(raw_value.upper())
    except ValueError:
        return MarketCode.CN
