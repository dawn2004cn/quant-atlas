from __future__ import annotations

from dataclasses import dataclass
import dataclasses
from typing import Any, Generic, TypeVar

from flask import jsonify, Response

T = TypeVar("T")


@dataclass
class ApiResponse(Generic[T]):
    success: bool
    data: T | None = None
    meta: dict[str, Any] | None = None

    def to_response(self) -> Response:
        return jsonify({"success": self.success, "data": serialize(self.data), "error": None, "meta": self.meta})


def serialize(obj: Any) -> Any:
    """Serialize Pydantic/dataclass/dict objects to JSON-safe structures.

    IMPORTANT: This function explicitly excludes sensitive fields from
    serialization to prevent accidental leakage of password hashes,
    API keys, tokens, and other secrets in API responses.
    """
    SENSITIVE_FIELDS = frozenset({
        'password_hash', 'password', 'secret', 'api_key', 'apikey',
        'access_token', 'refresh_token', 'token', 'private_key',
        'secret_key', 'credential', 'auth_token', 'session_key',
    })

    def _serialize_safe(obj: Any, depth: int = 0) -> Any:
        if depth > 10:  # Prevent infinite recursion
            return "[MAX_DEPTH_REACHED]"

        # Pydantic v2
        if hasattr(obj, "model_dump"):
            dumped = obj.model_dump()
            return {k: _serialize_safe(v) for k, v in dumped.items() if k not in SENSITIVE_FIELDS}

        # Pydantic v1
        if hasattr(obj, "dict"):
            dumped = obj.dict()
            return {k: _serialize_safe(v) for k, v in dumped.items() if k not in SENSITIVE_FIELDS}

        # Dataclass
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            dumped = dataclasses.asdict(obj)
            return {k: _serialize_safe(v) for k, v in dumped.items() if k not in SENSITIVE_FIELDS}

        if isinstance(obj, dict):
            return {k: _serialize_safe(v) for k, v in obj.items() if k not in SENSITIVE_FIELDS}

        if isinstance(obj, list):
            return [_serialize_safe(item) for item in obj]

        if isinstance(obj, tuple):
            return tuple(_serialize_safe(item) for item in obj)

        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj

        # Generic object — only serialize safe attributes
        if hasattr(obj, "__dict__") and not isinstance(obj, (str, int, float, bool)):
            filtered = {
                k: _serialize_safe(v)
                for k, v in obj.__dict__.items()
                if k not in SENSITIVE_FIELDS and not k.startswith("_")
            }
            return filtered if filtered else repr(obj)

        return obj

    return _serialize_safe(obj)


def success_response(data: Any = None, meta: dict[str, Any] | None = None, code: int = 200) -> Response:
    return jsonify({"success": True, "ok": True, "status": "success", "data": serialize(data) if data is not None else None, "error": None, "meta": meta}), code


def error_response(error: str, code: int = 400, meta: dict[str, Any] | None = None) -> Response:
    return jsonify({"success": False, "data": None, "error": error, "meta": meta}), code


def paginated_response(items: list[Any], total: int, page: int, page_size: int, meta: dict[str, Any] | None = None) -> Response:
    return jsonify({
        "success": True,
        "data": serialize(items),
        "error": None,
        "meta": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
            **(meta or {}),
        },
    }), 200
