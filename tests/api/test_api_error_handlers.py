from flask import Flask

from app.application.errors import (
    AuthorizationError,
    ExternalServiceError,
    NotFoundError,
    ValidationError,
)
from app.presentation.api.error_handlers import (
    map_application_error,
    map_authorization_error,
    map_unexpected_error,
)


def test_application_error_mapped_to_structured_response():
    payload, status_code = map_application_error(
        ValidationError("invalid request", details={"field": "top_n"})
    )
    assert status_code == 400
    assert payload["success"] is False
    assert payload["error"] == "invalid request"
    assert payload["meta"]["code"] == "validation_error"
    assert payload["meta"]["details"]["field"] == "top_n"
    assert payload["request_id"]


def test_authorization_maps_to_403():
    payload, status_code = map_authorization_error(
        AuthorizationError("user_management_forbidden")
    )
    assert status_code == 403
    assert payload["meta"]["code"] == "authorization_error"


def test_not_found_maps_to_404():
    payload, status_code = map_application_error(
        NotFoundError("resource_missing", details={"id": "x"})
    )
    assert status_code == 404
    assert payload["meta"]["code"] == "not_found"


def test_external_service_maps_to_503():
    payload, status_code = map_application_error(
        ExternalServiceError("upstream_down", details={"reason": "timeout"})
    )
    assert status_code == 503
    assert payload["meta"]["code"] == "external_service_error"


def test_unexpected_error_mapped_to_internal_error():
    payload, status_code = map_unexpected_error(RuntimeError("boom"))
    assert status_code == 500
    assert payload["success"] is False
    assert payload["error"] == "Internal server error"
    assert payload["meta"]["code"] == "internal_error"


def test_unexpected_error_includes_request_id():
    app = Flask(__name__)
    with app.test_request_context("/api/test", headers={"X-Request-ID": "req-1"}):
        payload, status_code = map_unexpected_error(RuntimeError("boom"))
    assert status_code == 500
    assert payload["request_id"] == "req-1"


def test_application_error_includes_request_id():
    app = Flask(__name__)
    with app.test_request_context("/api/test", headers={"X-Request-ID": "req-2"}):
        payload, status_code = map_application_error(
            ValidationError("invalid request", details={"field": "top_n"})
        )
    assert status_code == 400
    assert payload["request_id"] == "req-2"
    assert payload["meta"]["details"]["field"] == "top_n"
