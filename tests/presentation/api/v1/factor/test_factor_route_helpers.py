"""Tests for factor route helpers."""

from __future__ import annotations

import pytest

from app.application.errors import ValidationError
from app.presentation.api.v1.factor._helpers import factors_dataframe


def test_factors_dataframe_parses_list():
    df = factors_dataframe({"factors": [{"a": 1, "b": 2}]})
    assert list(df.columns) == ["a", "b"]


def test_factors_dataframe_required_raises():
    with pytest.raises(ValidationError, match="factors_required"):
        factors_dataframe({"factors": []}, required=True)


def test_factors_dataframe_optional_empty():
    df = factors_dataframe({"factors": []}, required=False)
    assert df.empty
