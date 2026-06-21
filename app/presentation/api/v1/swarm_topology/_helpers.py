"""Helpers for swarm topology HTTP routes."""

from __future__ import annotations

from typing import Any

from flask import Response

from app.presentation.api.common import ok_response
from app.presentation.api.v1.swarm_topology.runtime import SwarmTopologyRuntime


def unavailable_response(runtime: SwarmTopologyRuntime) -> Response:
    return ok_response(
        data={"available": False, "summary": "Service unavailable"},
        legacy_alias_key=None,
        enable_legacy_alias=runtime.legacy,
    )


def topology_service(runtime: SwarmTopologyRuntime) -> Any | None:
    return runtime.topology_service


def adaptive_service(runtime: SwarmTopologyRuntime) -> Any | None:
    return runtime.adaptive_service
