"""Rate limiter unit tests — TokenBucket and RateLimiter."""

from __future__ import annotations

import time

import pytest

from app.core.rate_limiter import RateLimitConfig, RateLimiter, TokenBucket


def test_token_bucket_consume_when_tokens_available():
    bucket = TokenBucket(capacity=2, refill_rate=1.0)
    assert bucket.consume(1) is True
    assert bucket.consume(1) is True
    assert bucket.consume(1) is False


def test_token_bucket_refills_over_time():
    bucket = TokenBucket(capacity=1, refill_rate=10.0)
    assert bucket.consume(1) is True
    assert bucket.consume(1) is False
    time.sleep(0.15)
    assert bucket.consume(1) is True


def test_rate_limit_config_defaults():
    cfg = RateLimitConfig()
    assert cfg.max_calls == 100
    assert cfg.window_seconds == 60
    assert cfg.block_duration == 0


def test_rate_limiter_blocks_after_capacity_exhausted():
    limiter = RateLimiter(RateLimitConfig(max_calls=2, window_seconds=60, block_duration=1))
    key = "user-1"
    assert limiter.is_allowed(key)[0] is True
    assert limiter.is_allowed(key)[0] is True
    allowed, info = limiter.is_allowed(key)
    assert allowed is False
    assert info.get("tokens") == pytest.approx(0.0)
    # block_duration applies on the next request
    allowed_blocked, info_blocked = limiter.is_allowed(key)
    assert allowed_blocked is False
    assert info_blocked.get("blocked") is True
