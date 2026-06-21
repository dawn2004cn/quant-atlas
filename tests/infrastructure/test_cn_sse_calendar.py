from app.infrastructure.calendar.cn_sse_calendar import is_cn_equity_trading_day, is_weekday_calendar


def test_is_weekday_calendar_excludes_weekend():
    assert is_weekday_calendar("2024-01-06") is False
    assert is_weekday_calendar("2024-01-08") is True


def test_is_cn_equity_trading_day_known_weekend():
    assert is_cn_equity_trading_day("2024-01-06") is False
