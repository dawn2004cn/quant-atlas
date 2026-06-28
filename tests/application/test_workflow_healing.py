"""Regression tests for the RetryPolicy and CircuitBreaker workflow healing (Phase 4)."""

from __future__ import annotations

import time

import pytest

from app.application.workflows.healing import (
    CircuitBreaker as WorkflowCircuitBreaker,
)
from app.application.workflows.healing import (
    RetryPolicy,
    with_retry,
)


class TestRetryPolicy:
    """Exponential backoff configuration."""

    def test_default_retries(self):
        p = RetryPolicy()
        assert p.max_retries == 3

    def test_delay_exponential(self):
        p = RetryPolicy(base_delay_s=1.0, backoff_factor=2.0)
        assert p.delay(0) == 1.0  # 1 * 2^0
        assert p.delay(1) == 2.0  # 1 * 2^1
        assert p.delay(2) == 4.0  # 1 * 2^2
        assert p.delay(3) == 8.0  # 1 * 2^3

    def test_delay_capped(self):
        p = RetryPolicy(base_delay_s=10.0, backoff_factor=10.0, max_delay_s=50.0)
        assert p.delay(2) == 50.0  # would be 1000, capped to 50

    def test_base_delay_zero(self):
        p = RetryPolicy(base_delay_s=0.0)
        assert p.delay(0) == 0.0
        assert p.delay(1) == 0.0


class TestWorkflowCircuitBreaker:
    """Circuit breaker for workflow step recovery."""

    @pytest.fixture
    def cb(self):
        return WorkflowCircuitBreaker(threshold=3, window=300, cooldown=0.05)

    def test_starts_closed(self, cb):
        assert cb.allow_request("step1") is True

    def test_opens_after_threshold(self, cb):
        for _ in range(3):
            cb.record_failure("step1")
        assert cb.allow_request("step1") is False

    def test_stays_closed_below_threshold(self, cb):
        cb.record_failure("step1")
        cb.record_failure("step1")
        assert cb.allow_request("step1") is True

    def test_half_open_after_cooldown(self, cb):
        for _ in range(3):
            cb.record_failure("step1")
        assert cb.allow_request("step1") is False
        time.sleep(0.06)
        assert cb.allow_request("step1") is True  # HALF_OPEN

    def test_success_resets(self, cb):
        cb.record_failure("step1")
        cb.record_failure("step1")
        cb.record_success("step1")
        assert cb.allow_request("step1") is True
        assert cb._state["step1"] == WorkflowCircuitBreaker.CLOSED

    def test_key_isolation(self, cb):
        cb.record_failure("step_a")
        cb.record_failure("step_a")
        cb.record_failure("step_a")
        assert cb.allow_request("step_a") is False
        assert cb.allow_request("step_b") is True  # different key, unaffected

    def test_window_prunes_old_failures(self):
        cb = WorkflowCircuitBreaker(threshold=2, window=0.01, cooldown=0.05)
        cb.record_failure("step1")
        time.sleep(0.02)
        cb.record_failure("step1")
        # old failure should be pruned, only 1 recent failure left → still closed
        assert cb.allow_request("step1") is True


class TestWithRetry:
    """Retry wrapper for step handlers."""

    def test_success_immediately(self):
        def handler():
            return "ok"

        wrapped = with_retry(handler)
        assert wrapped() == "ok"

    def test_retry_then_success(self):
        call_count = [0]

        def handler():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("transient")
            return "recovered"

        wrapped = with_retry(handler, RetryPolicy(max_retries=3, base_delay_s=0.01))
        assert wrapped() == "recovered"
        assert call_count[0] == 3

    def test_all_retries_exhausted(self):
        call_count = [0]

        def handler():
            call_count[0] += 1
            raise ValueError("persistent")

        wrapped = with_retry(handler, RetryPolicy(max_retries=2, base_delay_s=0.01))
        with pytest.raises(ValueError, match="persistent"):
            wrapped()
        assert call_count[0] == 3  # initial + 2 retries

    def test_circuit_breaker_blocks(self):
        cb = WorkflowCircuitBreaker(threshold=2, cooldown=60)
        cb.record_failure("test_key")
        cb.record_failure("test_key")

        def handler():
            return "should_not_run"

        wrapped = with_retry(handler, circuit_breaker=cb, breaker_key="test_key")
        with pytest.raises(RuntimeError, match="Circuit breaker OPEN"):
            wrapped()

    def test_success_resets_circuit_breaker(self):
        cb = WorkflowCircuitBreaker(threshold=3, cooldown=60)
        call_count = [0]

        def handler():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("transient")
            return "ok"

        wrapped = with_retry(handler, RetryPolicy(max_retries=3, base_delay_s=0.01), cb, "step")
        wrapped()
        assert cb.allow_request("step") is True  # CLOSED again


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
