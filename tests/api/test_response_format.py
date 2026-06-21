"""Tests for the canonical API response format (responses.py)."""

from __future__ import annotations

import json

import pytest

from tests.helpers import ApiTestMixin


class TestApiResponse(ApiTestMixin):
    def test_success_response_format(self, flask_app):
        from app.presentation.api.responses import success_response

        with flask_app.app_context():
            resp = success_response(data={"key": "value"}, meta={"count": 1})
        payload = json.loads(resp[0].data.decode())
        assert payload["success"] is True
        assert payload["data"] == {"key": "value"}
        assert payload["error"] is None
        assert payload["meta"] == {"count": 1}

    def test_error_response_format(self, flask_app):
        from app.presentation.api.responses import error_response

        with flask_app.app_context():
            resp = error_response("something went wrong", code=400)
        payload = json.loads(resp[0].data.decode())
        assert payload["success"] is False
        assert payload["data"] is None
        assert payload["error"] == "something went wrong"

    def test_paginated_response_format(self, flask_app):
        from app.presentation.api.responses import paginated_response

        with flask_app.app_context():
            resp = paginated_response(items=[1, 2, 3], total=30, page=2, page_size=10)
        payload = json.loads(resp[0].data.decode())
        assert payload["success"] is True
        assert payload["data"] == [1, 2, 3]
        assert payload["meta"]["total"] == 30
        assert payload["meta"]["page"] == 2
        assert payload["meta"]["page_size"] == 10
        assert payload["meta"]["total_pages"] == 3

    def test_serialize_dataclass(self):
        from dataclasses import dataclass
        from app.presentation.api.responses import serialize

        @dataclass
        class Item:
            name: str
            value: int

        result = serialize(Item(name="foo", value=42))
        assert result == {"name": "foo", "value": 42}

    def test_serialize_pydantic_v2(self):
        from pydantic import BaseModel
        from app.presentation.api.responses import serialize

        class Item(BaseModel):
            name: str
            value: int

        result = serialize(Item(name="foo", value=42))
        assert result == {"name": "foo", "value": 42}

    def test_serialize_list(self):
        from app.presentation.api.responses import serialize
        assert serialize([1, 2, 3]) == [1, 2, 3]

    def test_success_response_no_data(self, flask_app):
        from app.presentation.api.responses import success_response

        with flask_app.app_context():
            resp = success_response()
        payload = json.loads(resp[0].data.decode())
        assert payload["success"] is True
        assert payload["data"] is None