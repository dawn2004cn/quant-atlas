"""Mesh gateway unavailable response helper."""

from __future__ import annotations

from flask import Response

from app.presentation.api.common import ok_response
from app.presentation.api.v1.mesh.runtime import MeshRuntime


def unavailable_response(runtime: MeshRuntime) -> Response:
    return ok_response(
        data={"available": False, "summary": "Service unavailable"},
        legacy_alias_key=None,
        enable_legacy_alias=runtime.legacy,
    )
