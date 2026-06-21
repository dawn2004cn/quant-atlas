from app.application.errors import ValidationError
from app.presentation.api.request_parsers import parse_float_param, parse_int_param


def test_parse_int_param_success_and_default():
    assert parse_int_param("12", name="top_n", default=20, min_value=1) == 12
    assert parse_int_param(None, name="top_n", default=20, min_value=1) == 20


def test_parse_int_param_raises_validation_error():
    try:
        parse_int_param("abc", name="top_n", default=20, min_value=1)
    except ValidationError as exc:
        assert "top_n must be an integer" in str(exc)
    else:
        raise AssertionError("Expected ValidationError for non-integer input")


def test_parse_int_param_min_value():
    try:
        parse_int_param("0", name="top_n", default=20, min_value=1)
    except ValidationError as exc:
        assert "top_n must be >=" in str(exc)
    else:
        raise AssertionError("Expected ValidationError for min-value violation")


def test_parse_float_param_success_and_default():
    assert parse_float_param("1000.5", name="initial_capital", default=100000, min_value=0) == 1000.5
    assert parse_float_param(None, name="initial_capital", default=100000, min_value=0) == 100000.0


def test_parse_float_param_raises_validation_error():
    try:
        parse_float_param("bad", name="initial_capital", default=100000, min_value=0)
    except ValidationError as exc:
        assert "initial_capital must be a number" in str(exc)
    else:
        raise AssertionError("Expected ValidationError for non-float input")
