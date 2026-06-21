"""Hybrid rate limiter tests."""

from __future__ import annotations

import time

from app.core.hybrid_rate_limiter import HybridRateLimiter


def test_memory_fallback_blocks_after_max_attempts(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.core.hybrid_rate_limiter.HybridRateLimiter._record_redis",
        lambda self, key: None,
    )
    limiter = HybridRateLimiter("test_ns", window=60, max_attempts=2)
    assert limiter.allow("1.2.3.4") is True
    assert limiter.allow("1.2.3.4") is True
    assert limiter.allow("1.2.3.4") is False


def test_redis_path_used_when_available(monkeypatch) -> None:
    calls: list[str] = []

    def fake_redis(self, key: str) -> bool:
        calls.append(key)
        return True

    monkeypatch.setattr(
        "app.core.hybrid_rate_limiter.HybridRateLimiter._record_redis",
        fake_redis,
    )
    limiter = HybridRateLimiter("auth_login", window=60, max_attempts=5)
    assert limiter.allow("10.0.0.1") is True
    assert calls == ["10.0.0.1"]


def test_is_blocked_without_recording(monkeypatch) -> None:
    monkeypatch.setattr(
        HybridRateLimiter,
        "_redis_url",
        lambda self: "",
    )
    limiter = HybridRateLimiter("test_ns", window=60, max_attempts=2)
    limiter.record("127.0.0.1")
    limiter.record("127.0.0.1")
    assert limiter.is_blocked("127.0.0.1") is True
    assert limiter.is_blocked("127.0.0.1") is True


def test_retry_after_counts_down(monkeypatch) -> None:
    monkeypatch.setattr(
        HybridRateLimiter,
        "_redis_url",
        lambda self: "",
    )
    limiter = HybridRateLimiter("test_ns", window=2, max_attempts=1)
    limiter.record("127.0.0.1")
    assert limiter.is_blocked("127.0.0.1") is True
    first = limiter.retry_after("127.0.0.1")
    assert 1 <= first <= 2
    time.sleep(1.1)
    assert limiter.retry_after("127.0.0.1") <= first


def test_reset_clears_block(monkeypatch) -> None:
    monkeypatch.setattr(
        HybridRateLimiter,
        "_redis_url",
        lambda self: "",
    )
    limiter = HybridRateLimiter("test_ns", window=60, max_attempts=1)
    limiter.record("127.0.0.1")
    assert limiter.is_blocked("127.0.0.1") is True
    limiter.reset("127.0.0.1")
    assert limiter.is_blocked("127.0.0.1") is False
