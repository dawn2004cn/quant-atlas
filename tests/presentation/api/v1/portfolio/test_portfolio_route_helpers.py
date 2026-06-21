"""Tests for portfolio route helpers."""

from __future__ import annotations

import pytest

from app.application.errors import ValidationError
from app.presentation.api.v1.portfolio._helpers import parse_symbols_param, require_symbols


def test_parse_symbols_param_trims_and_splits():
    assert parse_symbols_param("600519, 000001 ,") == ["600519", "000001"]


def test_parse_symbols_param_empty():
    assert parse_symbols_param("") == []
    assert parse_symbols_param("  ,  ") == []


def test_require_symbols_raises_when_empty():
    with pytest.raises(ValidationError, match="symbols_required"):
        require_symbols([])
