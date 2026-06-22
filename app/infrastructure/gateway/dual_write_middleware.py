"""Dual-write middleware for gradual microservice extraction.

During Phase 2A-2C, this middleware enables the Strangler Fig pattern by:
1. Routing requests to both monolith and new service
2. Comparing responses for consistency
3. Gradually shifting traffic based on confidence metrics

Usage:
    from app.infrastructure.gateway.dual_write_middleware import DualWriteProxy

    proxy = DualWriteProxy()
    proxy.register_service("market_data", market_data_client)
    
    # In request handler:
    response = proxy.route("market_data", request)
"""

from __future__ import annotations

import logging
import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Protocol
from uuid import uuid4

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class ServiceHealth:
    """Health status of a microservice."""
    name: str
    status: ServiceStatus = ServiceStatus.UNKNOWN
    last_check: float = 0.0
    latency_ms: float = 0.0
    error_count: int = 0
    success_count: int = 0
    
    @property
    def success_rate(self) -> float:
        total = self.success_count + self.error_count
        return self.success_count / total if total > 0 else 0.0


class ServiceClient(Protocol):
    """Protocol for service clients."""
    
    def call(self, method: str, path: str, **kwargs) -> Any:
        """Call the service and return response."""
        ...


@dataclass
class DualWriteConfig:
    """Configuration for dual-write behavior."""
    enabled: bool = True
    comparison_interval: int = 100  # Compare every N requests
    confidence_threshold: float = 0.99  # 99% match rate = ready to cutover
    max_latency_ms: float = 500.0  # Max acceptable service latency
    health_check_interval: float = 30.0  # seconds


class DualWriteProxy:
    """Proxy that routes requests to monolith and/or microservices.

    This implements the Strangler Fig pattern for gradual service extraction:
    1. Start: 100% monolith, 0% service
    2. Dual-write: 100% monolith + X% service (validation)
    3. Canary: X% monolith, (100-X)% service
    4. Full cutover: 0% monolith, 100% service

    The proxy tracks:
    - Response consistency (monolith vs service)
    - Service health and latency
    - Confidence metrics for cutover decision
    """

    def __init__(self, config: DualWriteConfig | None = None):
        self.config = config or DualWriteConfig()
        self._services: dict[str, ServiceClient] = {}
        self._health: dict[str, ServiceHealth] = {}
        self._traffic_split: dict[str, float] = {}  # 0.0 = monolith only, 1.0 = service only
        self._comparison_history: dict[str, deque] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=4)

    def register_service(self, name: str, client: ServiceClient, traffic_split: float = 0.0) -> None:
        """Register a microservice client.
        
        Args:
            name: Service identifier (e.g., "market_data")
            client: Service client implementing ServiceClient protocol
            traffic_split: 0.0 = monolith only, 1.0 = service only
        """
        with self._lock:
            self._services[name] = client
            self._traffic_split[name] = traffic_split
            self._health[name] = ServiceHealth(name=name)
            self._comparison_history[name] = deque(maxlen=1000)
            logger.info("Registered service: %s (traffic_split=%.2f)", name, traffic_split)

    def route(self, service_name: str, request: Any, monolith_handler: Callable) -> Any:
        """Route request according to traffic split and dual-write config.
        
        Args:
            service_name: Target service (e.g., "market_data")
            request: Flask request object
            monolith_handler: Callable that handles request in monolith
            
        Returns:
            Response from monolith or service
        """
        import random
        
        with self._lock:
            split = self._traffic_split.get(service_name, 0.0)
            health = self._health.get(service_name)
            client = self._services.get(service_name)
        
        # Check service health
        if health and health.status == ServiceStatus.DOWN:
            logger.warning("Service %s is DOWN, routing to monolith", service_name)
            return monolith_handler()
        
        # Decide routing based on traffic split
        if random.random() < split:
            # Route to service
            return self._route_to_service(service_name, request, monolith_handler)
        else:
            # Route to monolith
            return monolith_handler()

    def _route_to_service(self, service_name: str, request: Any, fallback: Callable) -> Any:
        """Route request to microservice with fallback to monolith."""
        client = self._services.get(service_name)
        if client is None:
            logger.warning("Service %s not registered, using monolith", service_name)
            return fallback()
        
        try:
            start = time.time()
            response = client.call(request.method, request.path)
            latency = (time.time() - start) * 1000
            
            # Update health
            with self._lock:
                health = self._health[service_name]
                health.success_count += 1
                health.latency_ms = latency
                health.last_check = time.time()
                if health.status == ServiceStatus.UNKNOWN:
                    health.status = ServiceStatus.HEALTHY
            
            return response
        except Exception as exc:
            logger.error("Service %s call failed: %s", service_name, exc)
            with self._lock:
                health = self._health[service_name]
                health.error_count += 1
                if health.error_count > 5:
                    health.status = ServiceStatus.DOWN
            return fallback()

    def compare_responses(self, service_name: str, monolith_resp: Any, service_resp: Any) -> bool:
        """Compare monolith and service responses for consistency.
        
        Returns:
            True if responses match within tolerance
        """
        try:
            # Normalize responses for comparison
            m_resp = self._normalize(monolith_resp)
            s_resp = self._normalize(service_resp)
            
            match = m_resp == s_resp
            with self._lock:
                history = self._comparison_history[service_name]
                history.append(1 if match else 0)
            
            return match
        except Exception as exc:
            logger.warning("Response comparison failed: %s", exc)
            return False

    def _normalize(self, response: Any) -> Any:
        """Normalize response for comparison (strip timestamps, etc.)."""
        if isinstance(response, dict):
            normalized = {}
            for k, v in response.items():
                if k in ("timestamp", "ts", "server_time", "latency_ms"):
                    continue
                normalized[k] = self._normalize(v)
            return normalized
        elif isinstance(response, list):
            return [self._normalize(item) for item in response]
        return response

    def get_confidence(self, service_name: str) -> float:
        """Get confidence score (0.0-1.0) for service cutover.
        
        Based on response consistency over recent comparisons.
        """
        with self._lock:
            history = self._comparison_history.get(service_name)
            if not history:
                return 0.0
            return sum(history) / len(history)

    def get_health(self, service_name: str) -> ServiceHealth | None:
        """Get health status for a service."""
        with self._lock:
            return self._health.get(service_name)

    def set_traffic_split(self, service_name: str, split: float) -> None:
        """Set traffic split for a service (0.0 = monolith, 1.0 = service)."""
        with self._lock:
            self._traffic_split[service_name] = max(0.0, min(1.0, split))
            logger.info("Traffic split for %s set to %.2f", service_name, split)

    def should_cutover(self, service_name: str) -> bool:
        """Check if service is ready for full cutover."""
        confidence = self.get_confidence(service_name)
        health = self.get_health(service_name)
        
        if health is None:
            return False
        
        ready = (
            confidence >= self.config.confidence_threshold
            and health.status == ServiceStatus.HEALTHY
            and health.success_rate >= 0.99
            and health.latency_ms <= self.config.max_latency_ms
        )
        
        if ready:
            logger.info("Service %s READY for cutover (confidence=%.3f, health=%s)", 
                       service_name, confidence, health.status.value)
        return ready

    def shutdown(self) -> None:
        """Shutdown the proxy and release resources."""
        self._executor.shutdown(wait=False)
        logger.info("DualWriteProxy shutdown complete")


# ── Global Proxy Instance ──────────────────────────────────────────

# Global dual-write proxy instance
_dual_write_proxy: DualWriteProxy | None = None


def get_dual_write_proxy() -> DualWriteProxy:
    """Get or create the global dual-write proxy instance."""
    global _dual_write_proxy
    if _dual_write_proxy is None:
        _dual_write_proxy = DualWriteProxy()
    return _dual_write_proxy


def init_dual_write(config: DualWriteConfig | None = None) -> DualWriteProxy:
    """Initialize the global dual-write proxy with optional config."""
    global _dual_write_proxy
    _dual_write_proxy = DualWriteProxy(config or DualWriteConfig())
    return _dual_write_proxy
