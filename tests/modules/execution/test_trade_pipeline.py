"""TradeExecutionPipelineService fast-path tests."""

from __future__ import annotations

from types import SimpleNamespace

from app.modules.execution.services.trade_execution_pipeline_service import TradeExecutionPipelineService
from app.modules.portfolio_risk.services.fund_tier_service import ComplianceCheckResult


class _PassValidator:
    def validate(self, signal) -> bool:
        return True


class _FailValidator:
    def validate(self, signal) -> bool:
        return False


def _pipeline(*, compliance_passed: bool = True, validator=None) -> TradeExecutionPipelineService:
    compliance = SimpleNamespace(
        check_order=lambda **kwargs: ComplianceCheckResult(
            passed=compliance_passed,
            violations=[] if compliance_passed else ["position limit exceeded"],
            checks=[],
        )
    )
    audit = SimpleNamespace(
        record_snapshot=lambda **kwargs: SimpleNamespace(snapshot_id="snap-test-1")
    )
    return TradeExecutionPipelineService(
        compliance_guardrail=compliance,
        audit_trail=audit,
        impact_model=SimpleNamespace(),
        validator=validator or _PassValidator(),
    )


def test_execute_happy_path_with_skip_rbac():
    pipeline = _pipeline()
    result = pipeline.execute(
        user_id=1,
        symbol="600519",
        action="buy",
        quantity=100,
        price=10.0,
        skip_rbac=True,
        skip_impact=True,
    )
    assert result.ok is True
    assert result.stage == "completed"
    assert result.snapshot_id == "snap-test-1"
    assert result.execution["status"] == "accepted"


def test_execute_blocks_on_compliance_failure():
    pipeline = _pipeline(compliance_passed=False)
    result = pipeline.execute(
        user_id=1,
        symbol="600519",
        action="buy",
        quantity=100,
        price=10.0,
        skip_rbac=True,
        skip_impact=True,
    )
    assert result.ok is False
    assert result.stage == "compliance"
    assert "position limit exceeded" in result.violations


def test_execute_blocks_on_pre_trade_validation():
    pipeline = _pipeline(validator=_FailValidator())
    result = pipeline.execute(
        user_id=1,
        symbol="600519",
        action="buy",
        quantity=100,
        price=10.0,
        skip_rbac=True,
        skip_impact=True,
    )
    assert result.ok is False
    assert result.stage == "pre_trade"
    assert result.pre_trade["valid"] is False
