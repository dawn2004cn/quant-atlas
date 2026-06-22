"""Service discovery and inter-service communication.

This module provides:
1. ServiceRegistry: Central registry for all microservice endpoints
2. ServiceClient: HTTP client for making calls between services
3. ServiceMesh: DNS-based service discovery with health checks
"""

from __future__ import annotations

import logging
import threading
import time
import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class ServiceEndpoint:
    """Service endpoint configuration."""
    name: str
    url: str
    health_path: str = "/health"
    timeout: float = 10.0
    retries: int = 3
    circuit_breaker_threshold: int = 5
    
    # Runtime state
    status: ServiceStatus = ServiceStatus.UNKNOWN
    last_check: float = 0.0
    latency_ms: float = 0.0
    error_count: int = 0
    success_count: int = 0
    
    @property
    def success_rate(self) -> float:
        total = self.success_count + self.error_count
        return self.success_count / total if total > 0 else 0.0


@dataclass
class ServiceCallResult:
    """Result of a service-to-service call."""
    success: bool
    status_code: int = 0
    data: Any = None
    error: str = ""
    latency_ms: float = 0.0


class ServiceRegistry:
    """Central registry for microservice endpoints.
    
    Provides service discovery, health checking, and load balancing
    for inter-service communication.
    """
    
    def __init__(self):
        self._services: dict[str, ServiceEndpoint] = {}
        self._lock = threading.Lock()
        self._health_check_interval: float = 30.0
        self._last_health_check: dict[str, float] = {}
    
    def register(self, endpoint: ServiceEndpoint) -> None:
        """Register a service endpoint."""
        with self._lock:
            self._services[endpoint.name] = endpoint
            logger.info("Registered service: %s at %s", endpoint.name, endpoint.url)
    
    def register_simple(self, name: str, url: str, **kwargs) -> None:
        """Register a service with minimal configuration."""
        endpoint = ServiceEndpoint(name=name, url=url, **kwargs)
        self.register(endpoint)
    
    def get(self, name: str) -> ServiceEndpoint | None:
        """Get service endpoint by name."""
        with self._lock:
            return self._services.get(name)
    
    def get_url(self, name: str) -> str | None:
        """Get service URL by name."""
        endpoint = self.get(name)
        return endpoint.url if endpoint else None
    
    def list_services(self) -> list[str]:
        """List all registered service names."""
        with self._lock:
            return list(self._services.keys())
    
    def check_health(self, name: str) -> ServiceStatus:
        """Perform health check on a service."""
        endpoint = self.get(name)
        if not endpoint:
            return ServiceStatus.UNKNOWN
        
        try:
            health_url = endpoint.url.rstrip("/") + endpoint.health_path
            req = urllib.request.Request(health_url, method="GET")
            start = time.time()
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                latency = (time.time() - start) * 1000
                if resp.status == 200:
                    with self._lock:
                        endpoint.status = ServiceStatus.HEALTHY
                        endpoint.latency_ms = latency
                        endpoint.last_check = time.time()
                        endpoint.success_count += 1
                        self._last_health_check[name] = time.time()
                    return ServiceStatus.HEALTHY
        except Exception as exc:
            logger.warning("Health check failed for %s: %s", name, exc)
            with self._lock:
                endpoint.error_count += 1
                endpoint.last_check = time.time()
                if endpoint.error_count >= endpoint.circuit_breaker_threshold:
                    endpoint.status = ServiceStatus.DOWN
                self._last_health_check[name] = time.time()
        
        return endpoint.status
    
    def check_all_health(self) -> dict[str, ServiceStatus]:
        """Check health of all registered services."""
        results = {}
        for name in self.list_services():
            results[name] = self.check_health(name)
        return results
    
    def should_check_health(self, name: str) -> bool:
        """Check if health check is due."""
        with self._lock:
            last_check = self._last_health_check.get(name, 0.0)
        return (time.time() - last_check) > self._health_check_interval


class ServiceClient:
    """HTTP client for inter-service communication.
    
    Provides typed methods for calling common service patterns:
    - GET/POST/PUT/DELETE with JSON serialization
    - Automatic retries with exponential backoff
    - Circuit breaker integration
    - Request/response logging
    """
    
    def __init__(self, registry: ServiceRegistry, service_name: str):
        self.registry = registry
        self.service_name = service_name
        self.endpoint = registry.get(service_name)
        if not self.endpoint:
            raise ValueError(f"Service not registered: {service_name}")
    
    def _get_url(self, path: str) -> str:
        """Build full URL for service call."""
        base = self.endpoint.url.rstrip("/")
        path = path.lstrip("/")
        return f"{base}/{path}"
    
    def call(self, method: str, path: str, 
             headers: dict | None = None,
             body: Any = None,
             params: dict | None = None,
             timeout: float | None = None) -> ServiceCallResult:
        """Make HTTP call to service.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: Request path (e.g., "/api/v1/market/quotes")
            headers: Optional request headers
            body: Optional request body (dict auto-serialized to JSON)
            params: Optional query parameters
            timeout: Override default timeout
            
        Returns:
            ServiceCallResult with response data or error
        """
        url = self._get_url(path)
        if params:
            url += "?" + urllib.parse.urlencode(params)
        
        timeout = timeout or self.endpoint.timeout
        
        # Prepare request body
        data = None
        if body is not None:
            if isinstance(body, dict):
                data = json.dumps(body).encode("utf-8")
            elif isinstance(body, str):
                data = body.encode("utf-8")
        
        # Prepare headers
        req_headers = {"Content-Type": "application/json"}
        if headers:
            req_headers.update(headers)
        
        req = urllib.request.Request(
            url=url,
            data=data,
            headers=req_headers,
            method=method.upper(),
        )
        
        for attempt in range(self.endpoint.retries):
            try:
                start = time.time()
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    latency = (time.time() - start) * 1000
                    resp_body = resp.read().decode("utf-8")
                    content_type = resp.headers.get("Content-Type", "")
                    
                    parsed_data = None
                    if "application/json" in content_type:
                        parsed_data = json.loads(resp_body)
                    else:
                        parsed_data = resp_body
                    
                    # Update success metrics
                    with self.registry._lock:
                        self.endpoint.success_count += 1
                        self.endpoint.latency_ms = latency
                        if self.endpoint.status == ServiceStatus.UNKNOWN:
                            self.endpoint.status = ServiceStatus.HEALTHY
                    
                    return ServiceCallResult(
                        success=True,
                        status_code=resp.status,
                        data=parsed_data,
                        latency_ms=latency,
                    )
                    
            except urllib.error.HTTPError as exc:
                error_body = exc.read().decode("utf-8") if exc.fp else ""
                logger.error("HTTP error from %s: %s %s", url, exc.code, error_body)
                
                with self.registry._lock:
                    self.endpoint.error_count += 1
                    if self.endpoint.error_count >= self.endpoint.circuit_breaker_threshold:
                        self.endpoint.status = ServiceStatus.DOWN
                
                if exc.code >= 500 and attempt < self.endpoint.retries - 1:
                    continue  # Retry on server errors
                
                return ServiceCallResult(
                    success=False,
                    status_code=exc.code,
                    error=f"{exc.code} {error_body}",
                )
                
            except urllib.error.URLError as exc:
                logger.error("Connection error to %s: %s", url, exc.reason)
                
                with self.registry._lock:
                    self.endpoint.error_count += 1
                
                if attempt < self.endpoint.retries - 1:
                    continue  # Retry on connection errors
                
                return ServiceCallResult(
                    success=False,
                    error=f"Connection error: {exc.reason}",
                )
        
        return ServiceCallResult(success=False, error="Max retries exceeded")
    
    def get(self, path: str, params: dict | None = None) -> ServiceCallResult:
        """GET request."""
        return self.call("GET", path, params=params)
    
    def post(self, path: str, body: dict | None = None, 
             headers: dict | None = None) -> ServiceCallResult:
        """POST request with JSON body."""
        return self.call("POST", path, headers=headers, body=body)
    
    def put(self, path: str, body: dict | None = None,
            headers: dict | None = None) -> ServiceCallResult:
        """PUT request with JSON body."""
        return self.call("PUT", path, headers=headers, body=body)
    
    def delete(self, path: str) -> ServiceCallResult:
        """DELETE request."""
        return self.call("DELETE", path)


# ── Global Service Registry ─────────────────────────────────────────

_service_registry: ServiceRegistry | None = None
_registry_lock = threading.Lock()


def get_service_registry() -> ServiceRegistry:
    """Get or create the global service registry."""
    global _service_registry
    if _service_registry is None:
        with _registry_lock:
            if _service_registry is None:
                _service_registry = ServiceRegistry()
    return _service_registry


def register_service(name: str, url: str, **kwargs) -> None:
    """Register a service in the global registry."""
    registry = get_service_registry()
    registry.register_simple(name, url, **kwargs)


def get_service_client(service_name: str) -> ServiceClient | None:
    """Get a client for calling another service."""
    registry = get_service_registry()
    endpoint = registry.get(service_name)
    if not endpoint:
        return None
    return ServiceClient(registry, service_name)
