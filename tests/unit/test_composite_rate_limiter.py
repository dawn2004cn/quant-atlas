"""Unit tests for the composite rate limiter."""

from __future__ import annotations

import time
import unittest

from app.core.composite_rate_limiter import (
    CompositeRateLimiter,
    LimitRule,
)


class TestCompositeRateLimiter(unittest.TestCase):
    """Test thread-safe in-memory composite-key rate limiting."""

    def test_allows_within_limit(self):
        """Requests within the limit should all be allowed."""
        limiter = CompositeRateLimiter()
        rule = LimitRule(max_calls=5, window_seconds=60)
        key = "test:user:endpoint:1.2.3.4"
        now = time.time()
        for _ in range(5):
            self.assertTrue(limiter.is_allowed(key, rule, now))
            now += 0.1

    def test_blocks_over_limit(self):
        """Requests exceeding the limit should be blocked."""
        limiter = CompositeRateLimiter()
        rule = LimitRule(max_calls=3, window_seconds=60)
        key = "test:user:endpoint:1.2.3.4"
        now = time.time()
        for _ in range(3):
            self.assertTrue(limiter.is_allowed(key, rule, now))
            now += 0.1
        # 4th request should be blocked
        self.assertFalse(limiter.is_allowed(key, rule, now))

    def test_different_keys_independent(self):
        """Different composite keys should have independent limits."""
        limiter = CompositeRateLimiter()
        rule = LimitRule(max_calls=1, window_seconds=60)
        key_a = "user_a:api_a:1.1.1.1"
        key_b = "user_b:api_b:2.2.2.2"
        now = time.time()
        self.assertTrue(limiter.is_allowed(key_a, rule, now))
        self.assertFalse(limiter.is_allowed(key_a, rule, now))
        # key_b should still be allowed
        self.assertTrue(limiter.is_allowed(key_b, rule, now))

    def test_window_expiry(self):
        """Requests should be allowed again after the window expires."""
        limiter = CompositeRateLimiter()
        rule = LimitRule(max_calls=2, window_seconds=10)
        key = "test:key"
        now = time.time()
        self.assertTrue(limiter.is_allowed(key, rule, now))
        self.assertTrue(limiter.is_allowed(key, rule, now))
        self.assertFalse(limiter.is_allowed(key, rule, now))
        # After window expires
        self.assertTrue(limiter.is_allowed(key, rule, now + 11))

    def test_remaining_count(self):
        """Remaining calls should decrease as requests are made."""
        limiter = CompositeRateLimiter()
        rule = LimitRule(max_calls=5, window_seconds=60)
        key = "test:key"
        now = time.time()
        self.assertEqual(limiter.get_remaining(key, rule, now), 5)
        limiter.is_allowed(key, rule, now)
        self.assertEqual(limiter.get_remaining(key, rule, now), 4)
        limiter.is_allowed(key, rule, now)
        self.assertEqual(limiter.get_remaining(key, rule, now), 3)


if __name__ == "__main__":
    unittest.main()
