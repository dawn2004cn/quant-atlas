from __future__ import annotations

from typing import Any

from .responses import serialize


def build_success_payload(*, data: Any, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"success": True, "data": serialize(data) if data is not None else None, "error": None, "meta": meta}


def with_legacy_aliases(payload: dict[str, Any], *, alias_key: str | None, enabled: bool) -> dict[str, Any]:
    if not enabled or not alias_key or payload.get("data") is None:
        return payload
    if isinstance(payload["data"], dict):
        payload = dict(payload)
        payload["data"] = dict(payload["data"])
        payload["data"][alias_key] = payload["data"].get("data", payload["data"])
    return payload
