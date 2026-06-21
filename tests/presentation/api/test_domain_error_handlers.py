"""Domain/Core error handler registration tests."""
from __future__ import annotations

from app.core.exceptions import NotFoundError as CoreNotFoundError
from app.domain.exceptions import EntityNotFoundError
from app.presentation.api.error_handlers import _map_app_error, _map_core_error


def test_core_error_maps_to_http_status():
    payload, status = _map_core_error(CoreNotFoundError("User", "42"))
    assert status == 404
    assert payload["meta"]["code"] == "not_found"
    assert "42" in payload["error"]


def test_app_error_maps_entity_not_found():
    payload, status = _map_app_error(EntityNotFoundError("Order", "99"))
    assert status == 404
    assert payload["meta"]["code"] == "entity_not_found"
    assert "99" in payload["error"]
