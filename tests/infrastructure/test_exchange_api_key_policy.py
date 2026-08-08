"""Tests for exchange API key withdraw policy."""

import pytest

from app.infrastructure.security.exchange_api_key_policy import (
    ExchangeApiKeyPolicyError,
    assert_no_withdraw,
)


def test_assert_no_withdraw_allows_clean_config():
    policy = assert_no_withdraw({"apiKey": "x", "secret": "y"}, exchange_id="binance")
    assert policy.allow_withdraw is False
    assert policy.allow_trade is True


def test_assert_no_withdraw_rejects_enable_withdraw():
    with pytest.raises(ExchangeApiKeyPolicyError, match="withdraw_forbidden"):
        assert_no_withdraw({"enable_withdraw": True}, exchange_id="okx")


def test_assert_no_withdraw_rejects_allow_withdraw_true():
    with pytest.raises(ExchangeApiKeyPolicyError):
        assert_no_withdraw({"allow_withdraw": 1}, exchange_id="binance")
