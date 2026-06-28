
"""Auto-discovery of Go trade gateway via gRPC health check."""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)
_GATEWAY_GRPC_TARGET: str | None = None
_GATEWAY_ACTIVE: bool = False

def probe_gateway(target: str | None = None) -> bool:
    global _GATEWAY_GRPC_TARGET, _GATEWAY_ACTIVE
    target = target or os.getenv("GATEWAY_GRPC_TARGET", "localhost:9090")
    _GATEWAY_GRPC_TARGET = target
    try:
        import grpc
        from grpc_health.v1 import health_pb2, health_pb2_grpc
        channel = grpc.insecure_channel(target)
        stub = health_pb2_grpc.HealthStub(channel)
        resp = stub.Check(health_pb2.HealthCheckRequest(service=""), timeout=2.0)
        if resp.status == 1:
            _GATEWAY_ACTIVE = True
            logger.info("Go trade gateway detected at %s", target)
            return True
    except ImportError:
        logger.debug("grpc_health probe unavailable")
    except Exception as exc:
        logger.debug("Go trade gateway not reachable at %s: %s", target, exc)
    _GATEWAY_ACTIVE = False
    return False

def is_gateway_active() -> bool:
    return _GATEWAY_ACTIVE

def get_gateway_target() -> str:
    return _GATEWAY_GRPC_TARGET or os.getenv("GATEWAY_GRPC_TARGET", "localhost:9090")

def create_gateway_client() -> object:
    from app.infrastructure.trading.gateway_client import TradeExecutionStub
    return TradeExecutionStub(use_grpc=is_gateway_active(), grpc_target=get_gateway_target())
