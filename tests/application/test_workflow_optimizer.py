"""Regression tests for WorkflowOptimizer (Phase 4, auto-healing optimizer)."""

from __future__ import annotations

import pytest

from app.application.workflows.optimizer import (
    StepMetrics,
    WorkflowOptimizer,
)


@pytest.fixture
def optimizer() -> WorkflowOptimizer:
    return WorkflowOptimizer()


class TestStepMetrics:
    """Per-step metrics tracking."""

    def test_record_stores_duration(self):
        sm = StepMetrics()
        sm.record(5.0, success=True)
        assert sm.last_duration_s == 5.0
        assert sm.success_count == 1
        assert sm.failure_count == 0

    def test_record_failure(self):
        sm = StepMetrics()
        sm.record(3.0, success=False)
        assert sm.failure_count == 1
        assert sm.success_count == 0

    def test_success_rate(self):
        sm = StepMetrics()
        sm.record(1.0, True)
        sm.record(1.0, True)
        sm.record(1.0, False)
        assert sm.success_rate == pytest.approx(2 / 3)

    def test_p95_with_few_samples(self):
        sm = StepMetrics()
        sm.record(10.0, True)
        assert sm.p95_duration_s == 10.0

    def test_p95_with_many_samples(self):
        sm = StepMetrics()
        for i in range(1, 21):
            sm.record(float(i), True)
        # sorted: 1..20. p95 index = int(20*0.95)=19 → value=20
        assert sm.p95_duration_s == pytest.approx(20.0, rel=0.1)

    def test_adaptive_timeout_minimum(self):
        sm = StepMetrics()
        sm.record(5.0, True)
        timeout = sm.adaptive_timeout()
        assert timeout >= 60

    def test_adaptive_timeout_calculation(self):
        sm = StepMetrics()
        sm.durations_s = [100.0] * 20
        sm.last_duration_s = 100.0
        timeout = sm.adaptive_timeout()
        # p95=100, *1.2=120, +10=130
        assert timeout == 130

    def test_sliding_window(self):
        sm = StepMetrics()
        for i in range(60):
            sm.record(float(i), True)
        assert len(sm.durations_s) <= 50


class TestWorkflowOptimizer:
    """Workflow-level metrics and adaptive timeouts."""

    def test_record_step_creates_metrics(self, optimizer):
        optimizer.record_step("wf_type", "step_1", 5.0, True)
        metrics = optimizer.get_metrics("wf_type")
        assert metrics is not None
        assert metrics.total_runs == 0  # step only, not whole workflow

    def test_record_workflow(self, optimizer):
        optimizer.record_workflow("wf_type", True)
        metrics = optimizer.get_metrics("wf_type")
        assert metrics.total_runs == 1
        assert metrics.total_success == 1

    def test_record_workflow_failure(self, optimizer):
        optimizer.record_workflow("wf_type", False)
        metrics = optimizer.get_metrics("wf_type")
        assert metrics.total_failure == 1
        assert metrics.total_success == 0

    def test_get_step_metrics(self, optimizer):
        optimizer.record_step("wf", "step1", 3.0, True)
        sm = optimizer.get_step_metrics("wf", "step1")
        assert sm is not None
        assert sm.last_duration_s == 3.0

    def test_get_step_metrics_nonexistent(self, optimizer):
        assert optimizer.get_step_metrics("nonexistent", "step1") is None

    def test_suggest_timeout_uses_default(self, optimizer):
        timeout = optimizer.suggest_timeout("unknown", "step", default=120)
        assert timeout == 120

    def test_suggest_timeout_adaptive(self, optimizer):
        for _ in range(10):
            optimizer.record_step("wf", "step", 200.0, True)
        timeout = optimizer.suggest_timeout("wf", "step", default=300)
        assert timeout > 200  # should be adaptive

    def test_summary_returns_structured_data(self, optimizer):
        optimizer.record_step("wf", "s1", 2.0, True)
        optimizer.record_step("wf", "s1", 3.0, False)
        optimizer.record_workflow("wf", True)
        summary = optimizer.summary()
        assert "wf" in summary
        assert summary["wf"]["total_runs"] == 1
        assert "steps" in summary["wf"]

    def test_thread_safety(self, optimizer):
        import threading
        errors = []

        def record_steps():
            try:
                for i in range(20):
                    optimizer.record_step("wf", f"step_{i}", float(i), True)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_steps) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_multiple_workflows_independent(self, optimizer):
        optimizer.record_step("wf_a", "step", 1.0, True)
        optimizer.record_step("wf_b", "step", 2.0, True)
        assert optimizer.get_metrics("wf_a") is not None
        assert optimizer.get_metrics("wf_b") is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
