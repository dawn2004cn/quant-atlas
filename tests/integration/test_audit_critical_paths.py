"""Integration tests for audit-critical paths (backtest limits, panorama cache, trade pipeline)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.core.risk_controls import RiskControlParams
from app.domain.enums import MarketCode
from app.infrastructure.providers.backtest_engine import BacktestEngine
from app.modules.execution.services.trade_execution_pipeline_service import TradeExecutionPipelineService
from app.modules.portfolio_risk.services.fund_tier_service import ComplianceCheckResult


class _AlwaysBuy:
    """Signals BUY once enough history exists (matches BacktestEngine day-30 gate)."""

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out["Signal"] = 0
        if len(out) > 30:
            out.iloc[30, out.columns.get_loc("Signal")] = 1
        return out


def _limit_up_history(days: int = 65) -> pd.DataFrame:
    dates = pd.date_range("2024-01-02", periods=days, freq="B")
    rows: list[dict[str, float | str]] = []
    for index, dt in enumerate(dates):
        if index < 30:
            close, open_, high, low = 10.0, 10.0, 10.2, 9.8
        elif index == 30:
            close, open_, high, low = 11.0, 11.0, 11.0, 10.9
        else:
            close, open_, high, low = 11.0, 11.0, 11.1, 10.9
        rows.append(
            {
                "Date": dt.strftime("%Y-%m-%d"),
                "Open": open_,
                "High": high,
                "Low": low,
                "Close": close,
                "Volume": 1_000_000,
            }
        )
    return pd.DataFrame(rows)


def test_backtest_e2e_skips_buy_on_limit_up_day() -> None:
    engine = BacktestEngine()
    initial = 100_000.0
    result = engine.simulate_single_backtest(
        _limit_up_history(),
        _AlwaysBuy(),
        initial,
    )
    assert result["metrics"]["total_trades"] == 0
    assert result["metrics"]["final_value"] == pytest.approx(initial)


def test_backtest_e2e_allows_buy_when_cn_limits_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.risk_controls import load_default_risk_params

    def _risk_without_limits() -> RiskControlParams:
        return replace(load_default_risk_params(), apply_cn_price_limits=False)

    monkeypatch.setattr(
        "app.infrastructure.providers.backtest_engine.load_default_risk_params",
        _risk_without_limits,
    )
    engine = BacktestEngine()
    initial = 100_000.0
    result = engine.simulate_single_backtest(
        _limit_up_history(),
        _AlwaysBuy(),
        initial,
    )
    assert result["metrics"]["total_trades"] >= 1
    assert result["metrics"]["final_value"] != pytest.approx(initial)


@patch("app.infrastructure.cache.cache_manager.get_cache_manager")
@patch("app.modules.market_data.services.market_service.get_quote_cache_port")
def test_panorama_cache_single_provider_hit(mock_quote_cache, mock_get_cache_manager) -> None:
    from app.modules.market_data.services.market_service import MarketApplicationService

    mock_quote_cache.return_value = MagicMock()
    provider = MagicMock()
    provider.get_market_overview.return_value = {
        "market_status": "open",
        "sentiment_score": 42.0,
    }
    provider.get_market_rankings.return_value = {
        "gainers": [{"code": "600519", "name": "Moutai", "change_pct": 2.1}],
        "losers": [],
        "amounts": [],
        "turnovers": [],
    }
    stored: dict[str, object] = {}
    cache = MagicMock()

    def _get_or_set(key: str, factory, *, ttl=None):
        if key in stored:
            return stored[key]
        value = factory()
        stored[key] = value
        return value

    cache.get_or_set.side_effect = _get_or_set
    mock_get_cache_manager.return_value = cache

    svc = MarketApplicationService(
        market_provider=provider,
        industry_provider=MagicMock(),
        stock_cache=None,
    )
    svc.get_panorama(MarketCode.CN)
    svc.get_panorama(MarketCode.CN)

    assert provider.get_market_rankings.call_count == 1
    assert provider.get_market_overview.call_count == 1


@dataclass
class _StageRecorder:
    compliance: dict | None = None
    pre_trade: dict | None = None
    snapshot_id: str | None = None


def test_trade_pipeline_happy_path_populates_all_stages() -> None:
    recorder = _StageRecorder()

    class _PassValidator:
        def validate(self, signal) -> bool:
            return True

    compliance = SimpleNamespace(
        check_order=lambda **kwargs: ComplianceCheckResult(
            passed=True,
            violations=[],
            checks=[{"name": "position_limit", "passed": True}],
        )
    )

    def _record_snapshot(**kwargs):
        recorder.snapshot_id = "snap-integration-1"
        return SimpleNamespace(snapshot_id=recorder.snapshot_id)

    audit = SimpleNamespace(record_snapshot=_record_snapshot)
    pipeline = TradeExecutionPipelineService(
        compliance_guardrail=compliance,
        audit_trail=audit,
        impact_model=SimpleNamespace(),
        validator=_PassValidator(),
    )

    result = pipeline.execute(
        user_id=1,
        symbol="600519",
        action="buy",
        quantity=100,
        price=1800.0,
        skip_rbac=True,
        skip_impact=True,
    )

    assert result.ok is True
    assert result.stage == "completed"
    assert result.snapshot_id == "snap-integration-1"
    assert result.compliance.get("passed") is True
    assert result.pre_trade.get("valid") is True
    assert result.execution.get("status") == "accepted"
    assert result.violations == []


def test_trade_pipeline_compliance_blocks_before_pre_trade() -> None:
    calls: list[str] = []

    class _TrackingValidator:
        def validate(self, signal) -> bool:
            calls.append("pre_trade")
            return True

    compliance = SimpleNamespace(
        check_order=lambda **kwargs: ComplianceCheckResult(
            passed=False,
            violations=["sector concentration"],
            checks=[],
        )
    )
    pipeline = TradeExecutionPipelineService(
        compliance_guardrail=compliance,
        audit_trail=SimpleNamespace(record_snapshot=lambda **k: SimpleNamespace(snapshot_id="x")),
        impact_model=SimpleNamespace(),
        validator=_TrackingValidator(),
    )

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
    assert calls == []
