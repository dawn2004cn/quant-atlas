from __future__ import annotations

"""Resilient HTTP Client with Circuit Breaker and Fallback.

This module implements the external API protection from midify_plan8.md:
- ResilientHttpClient: Unified client with retry, timeout, circuit breaker
- Fallback strategies for graceful degradation
- Decorator for easy integration

Usage:
    client = ResilientHttpClient("https://api.example.com")
    result = client.get("/data", fallback=lambda: default_data())
"""


from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.core.logger import get_logger

from ...core.resilience import CircuitBreaker, CircuitBreakerConfig

logger = get_logger(__name__)


class HttpMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


@dataclass
class ResilientConfig:
    """Configuration for resilient HTTP client."""
    timeout: float = 30.0
    max_retries: int = 3
    backoff_factor: float = 0.5
    retry_on_status: tuple = (500, 502, 503, 504)
    circuit_breaker_config: CircuitBreakerConfig | None = None


class FallbackStrategy:
    """Base class for fallback strategies."""

    def get_data(self) -> Any:
        """Return fallback data."""
        raise NotImplementedError


class DefaultFallback(FallbackStrategy):
    """Simple default value fallback."""

    def __init__(self, default_value: Any):
        self._default = default_value

    def get_data(self) -> Any:
        return self._default


class CacheFallback(FallbackStrategy):
    """Fallback to cached data."""

    def __init__(self, cache_getter: Callable[[], Any]):
        self._cache_getter = cache_getter

    def get_data(self) -> Any:
        return self._cache_getter()


class EmptyListFallback(FallbackStrategy):
    """Fallback to empty list."""

    def get_data(self) -> Any:
        return []


class EmptyDictFallback(FallbackStrategy):
    """Fallback to empty dict."""

    def get_data(self) -> Any:
        return {}


class ResilientHttpClient:
    """HTTP client with built-in resilience patterns.

    Features:
    - Automatic retry with exponential backoff
    - Request timeout handling
    - Circuit breaker protection
    - Fallback strategies for graceful degradation
    """

    def __init__(
        self,
        base_url: str = "",
        config: ResilientConfig | None = None,
        service_name: str | None = None,
    ):
        self._base_url = base_url.rstrip("/") if base_url else ""
        self._config = config or ResilientConfig()
        self._service_name = service_name or "http_client"

        self._circuit_breaker = CircuitBreaker(
            name=self._service_name,
            config=self._config.circuit_breaker_config or CircuitBreakerConfig(
                failure_threshold=5,
                timeout_seconds=30.0,
            ),
        )

        self._session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create session with retry strategy."""
        session = requests.Session()

        retry_strategy = Retry(
            total=self._config.max_retries,
            backoff_factor=self._config.backoff_factor,
            status_forcelist=self._config.retry_on_status,
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def request(
        self,
        method: HttpMethod,
        path: str,
        fallback: FallbackStrategy | None = None,
        **kwargs,
    ) -> Any:
        """Make HTTP request with resilience patterns."""
        url = f"{self._base_url}{path}" if path.startswith("/") else f"{self._base_url}/{path}"

        kwargs.setdefault("timeout", self._config.timeout)

        def make_request():
            response = self._session.request(
                method=method.value,
                url=url,
                **kwargs,
            )
            response.raise_for_status()
            return response.json()

        try:
            if not self._circuit_breaker.can_execute():
                logger.warning(f"Circuit breaker OPEN for {self._service_name}, using fallback")
                return self._execute_fallback(fallback)

            result = make_request()
            self._circuit_breaker.record_success()
            return result

        except Exception as e:
            self._circuit_breaker.record_failure(e)
            logger.error(f"Request failed for {self._service_name}: {e}")

            if fallback:
                return self._execute_fallback(fallback)

            raise

    def _execute_fallback(self, fallback: FallbackStrategy | None) -> Any:
        """Execute fallback strategy."""
        if fallback:
            try:
                return fallback.get_data()
            except Exception as e:
                logger.error(f"Fallback execution failed: {e}")
        return None

    def get(self, path: str, fallback: FallbackStrategy | None = None, **kwargs) -> Any:
        """GET request."""
        return self.request(HttpMethod.GET, path, fallback, **kwargs)

    def post(self, path: str, fallback: FallbackStrategy | None = None, **kwargs) -> Any:
        """POST request."""
        return self.request(HttpMethod.POST, path, fallback, **kwargs)

    def put(self, path: str, fallback: FallbackStrategy | None = None, **kwargs) -> Any:
        """PUT request."""
        return self.request(HttpMethod.PUT, path, fallback, **kwargs)

    def delete(self, path: str, fallback: FallbackStrategy | None = None, **kwargs) -> Any:
        """DELETE request."""
        return self.request(HttpMethod.DELETE, path, fallback, **kwargs)

    def get_circuit_status(self) -> dict[str, Any]:
        """Get circuit breaker status."""
        return self._circuit_breaker.get_status()


def resilient_http(
    base_url: str,
    service_name: str | None = None,
    config: ResilientConfig | None = None,
) -> Callable:
    """Decorator for adding resilience to HTTP client functions.

    Usage:
        @resilient_http("https://api.example.com", "my_service")
        def fetch_data():
            return requests.get("https://api.example.com/data").json()
    """
    ResilientHttpClient(base_url, config, service_name)

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Resilient wrapper caught error: {e}")
                return None

        return wrapper

    return decorator


_global_clients: dict[str, ResilientHttpClient] = {}


def get_resilient_client(
    name: str,
    base_url: str = "",
    config: ResilientConfig | None = None,
) -> ResilientHttpClient:
    """Get or create a named resilient HTTP client."""
    if name not in _global_clients:
        _global_clients[name] = ResilientHttpClient(base_url, config, name)
    return _global_clients[name]


def create_akshare_client() -> ResilientHttpClient:
    """Create resilient client for AkShare."""
    return get_resilient_client(
        "akshare",
        config=ResilientConfig(
            timeout=15.0,
            max_retries=2,
            circuit_breaker_config=CircuitBreakerConfig(
                failure_threshold=5,
                timeout_seconds=60.0,
            ),
        ),
    )


def create_ollama_client(base_url: str = "http://localhost:11434") -> ResilientHttpClient:
    """Create resilient client for Ollama."""
    return get_resilient_client(
        "ollama",
        base_url=base_url,
        config=ResilientConfig(
            timeout=60.0,
            max_retries=1,
            circuit_breaker_config=CircuitBreakerConfig(
                failure_threshold=3,
                timeout_seconds=30.0,
            ),
        ),
    )


def create_fingpt_client() -> ResilientHttpClient:
    """Create resilient client for FinGPT."""
    return get_resilient_client(
        "fingpt",
        config=ResilientConfig(
            timeout=30.0,
            max_retries=2,
            circuit_breaker_config=CircuitBreakerConfig(
                failure_threshold=5,
                timeout_seconds=60.0,
            ),
        ),
    )
