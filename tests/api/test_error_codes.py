"""Tests for the canonical ErrorCode enum."""

from __future__ import annotations

from app.presentation.api.error_codes import ErrorCode, error_payload


class TestErrorCode:
    def test_enum_values(self):
        assert ErrorCode.UNAUTHORIZED.value == "unauthorized"
        assert ErrorCode.VALIDATION_ERROR.value == "validation_error"
        assert ErrorCode.INTERNAL_ERROR.value == "internal_error"

    def test_http_status_mapping(self):
        assert ErrorCode.UNAUTHORIZED.http_status == 401
        assert ErrorCode.FORBIDDEN.http_status == 403
        assert ErrorCode.NOT_FOUND.http_status == 404
        assert ErrorCode.VALIDATION_ERROR.http_status == 400
        assert ErrorCode.INTERNAL_ERROR.http_status == 500
        assert ErrorCode.EXTERNAL_SERVICE_ERROR.http_status == 503
        assert ErrorCode.SERVICE_ERROR.http_status == 400  # default

    def test_all_codes_are_strings(self):
        for code in ErrorCode:
            assert isinstance(code.value, str)
            assert len(code.value) > 0

    def test_error_payload_format(self):
        payload = error_payload(ErrorCode.VALIDATION_ERROR, "Invalid input", {"field": "name"})
        assert payload["status"] == "error"
        assert payload["error"]["code"] == "validation_error"
        assert payload["error"]["message"] == "Invalid input"
        assert payload["error"]["details"]["field"] == "name"

    def test_error_payload_no_details(self):
        payload = error_payload(ErrorCode.NOT_FOUND, "Not found")
        assert payload["error"]["details"] == {}