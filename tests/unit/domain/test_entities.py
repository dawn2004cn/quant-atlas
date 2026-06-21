"""Tests for domain/entities.py — frozen dataclass domain entities."""

from __future__ import annotations

from datetime import datetime

from app.domain.entities import (
    BacktestReport,
    ChipDistribution,
    DecisionContext,
    EvidenceNote,
    Experiment,
    FinGPTPrediction,
    MarketSnapshot,
    NewsItem,
    PerformanceMetrics,
    StrategyConfig,
    StrategySelection,
    TrendAnalysisResult,
)
from app.domain.enums import MarketCode


# ======================================================================
# MarketSnapshot tests
# ======================================================================


class TestMarketSnapshot:
    """Tests for the MarketSnapshot entity."""

    def test_top_gainers(self):
        snap = MarketSnapshot(
            market=MarketCode.CN,
            generated_at=datetime.now(),
            summary={},
            rankings={"gainers": [{"code": "001"}, {"code": "002"}, {"code": "003"}]},
        )
        assert len(snap.top_gainers(2)) == 2
        assert snap.top_gainers(2)[0]["code"] == "001"

    def test_top_losers(self):
        snap = MarketSnapshot(
            market=MarketCode.CN,
            generated_at=datetime.now(),
            summary={},
            rankings={"losers": [{"code": "101"}, {"code": "102"}]},
        )
        assert len(snap.top_losers(1)) == 1

    def test_is_stale_old(self):
        from datetime import timedelta

        old = datetime.now() - timedelta(hours=1)
        snap = MarketSnapshot(
            market=MarketCode.CN,
            generated_at=old,
            summary={},
        )
        # 1 hour old → stale within 5 minute window
        assert snap.is_stale(max_age_minutes=5) is True

    def test_is_stale_fresh(self):
        snap = MarketSnapshot(
            market=MarketCode.CN,
            generated_at=datetime.now(),
            summary={},
        )
        assert snap.is_stale(max_age_minutes=5) is False

    def test_total_trading_volume(self):
        snap = MarketSnapshot(
            market=MarketCode.CN,
            generated_at=datetime.now(),
            summary={},
            sectors=[{"volume": 1000}, {"volume": 2000}],
        )
        assert snap.total_trading_volume() == 3000

    def test_total_trading_volume_empty_sectors(self):
        snap = MarketSnapshot(
            market=MarketCode.CN,
            generated_at=datetime.now(),
            summary={},
            sectors=[],
        )
        assert snap.total_trading_volume() == 0


# ======================================================================
# NewsItem tests
# ======================================================================


class TestNewsItem:
    """Tests for the NewsItem entity."""

    def test_defaults(self):
        item = NewsItem(
            title="Test",
            published_at="2024-01-01",
            source="Reuters",
        )
        assert item.url == ""
        assert item.summary == ""


# ======================================================================
# StrategySelection tests
# ======================================================================


class TestStrategySelection:
    """Tests for the StrategySelection entity."""

    def test_defaults(self):
        sel = StrategySelection(
            strategy="macd_cross",
            market=MarketCode.CN,
            generated_at=datetime.now(),
            candidates=[],
        )
        assert len(sel.candidates) == 0


# ======================================================================
# PerformanceMetrics tests
# ======================================================================


class TestPerformanceMetrics:
    """Tests for the PerformanceMetrics entity."""

    def test_is_profitable_positive(self):
        m = PerformanceMetrics(final_value=1100, total_return=100, annual_return=0.1, max_drawdown=-0.05, sharpe_ratio=1.5, volatility=0.2)
        assert m.is_profitable() is True

    def test_is_profitable_negative(self):
        m = PerformanceMetrics(final_value=900, total_return=-100, annual_return=-0.1, max_drawdown=-0.15, sharpe_ratio=-1.5, volatility=0.2)
        assert m.is_profitable() is False

    def test_risk_adjusted_score(self):
        m = PerformanceMetrics(
            final_value=1100,
            total_return=100,
            annual_return=0.1,
            max_drawdown=-0.05,
            sharpe_ratio=1.5,
            volatility=0.2,
            win_rate=60.0,
        )
        score = m.risk_adjusted_score()
        assert score > 0

    def test_risk_adjusted_score_zero_vol(self):
        m = PerformanceMetrics(
            final_value=1100,
            total_return=100,
            annual_return=0.1,
            max_drawdown=-0.05,
            sharpe_ratio=1.5,
            volatility=0.0,
            win_rate=60.0,
        )
        assert m.risk_adjusted_score() == 0.0

    def test_summary_dict(self):
        m = PerformanceMetrics(
            final_value=1100,
            total_return=100,
            annual_return=0.1,
            max_drawdown=-0.05,
            sharpe_ratio=1.5,
            volatility=0.2,
            win_rate=60.0,
        )
        d = m.summary_dict()
        assert d["return_pct"] == 100.0
        assert d["annual_return_pct"] == 0.1
        assert d["max_drawdown_pct"] == -0.05
        assert d["sharpe"] == 1.5
        assert d["win_rate_pct"] == 60.0


# ======================================================================
# BacktestReport tests
# ======================================================================


class TestBacktestReport:
    """Tests for the BacktestReport entity."""

    def test_get_metrics_from_dataclass(self):
        pm = PerformanceMetrics(final_value=1100, total_return=100, annual_return=0.1, max_drawdown=-0.05, sharpe_ratio=1.5, volatility=0.2)
        report = BacktestReport(
            strategy="macd_cross",
            symbol="600519",
            period={"start": "2024-01-01", "end": "2024-12-31"},
            metrics=pm,
            trades=[],
        )
        assert report.get_metrics() is pm

    def test_get_metrics_from_dict(self):
        report = BacktestReport(
            strategy="macd_cross",
            symbol="600519",
            period={"start": "2024-01-01", "end": "2024-12-31"},
            metrics={
                "final_value": 1100,
                "total_return": 100,
                "annual_return": 0.1,
                "max_drawdown": -0.05,
                "sharpe_ratio": 1.5,
                "volatility": 0.2,
                "win_rate": 60.0,
                "sortino_ratio": 0.0,
                "turnover_rate": 0.0,
                "slippage_cost_bps": 0.0,
                "total_fee": 0.0,
                "total_tax": 0.0,
                "profit_factor": 0.0,
                "calmar_ratio": 0.0,
                "stock_data": {},
                "diagnostics": {},
            },
            trades=[],
        )
        metrics = report.get_metrics()
        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.final_value == 1100
        assert metrics.win_rate == 60.0


# ======================================================================
# ChipDistribution tests
# ======================================================================


class TestChipDistribution:
    """Tests for the ChipDistribution entity."""

    def test_is_concentrated(self):
        chip = ChipDistribution(
            profit_ratio=60.0, avg_cost=100.0,
            concentration_90=10.0, concentration_70=8.0,
        )
        assert chip.is_concentrated(threshold=15.0) is True

    def test_not_concentrated(self):
        chip = ChipDistribution(
            profit_ratio=60.0, avg_cost=100.0,
            concentration_90=20.0, concentration_70=15.0,
        )
        assert chip.is_concentrated(threshold=15.0) is False

    def test_majority_profitable(self):
        chip = ChipDistribution(
            profit_ratio=60.0, avg_cost=100.0,
            concentration_90=15.0, concentration_70=10.0,
        )
        assert chip.majority_profitable() is True

    def test_majority_unprofitable(self):
        chip = ChipDistribution(
            profit_ratio=40.0, avg_cost=100.0,
            concentration_90=15.0, concentration_70=10.0,
        )
        assert chip.majority_profitable() is False


# ======================================================================
# TrendAnalysisResult tests
# ======================================================================


class TestTrendAnalysisResult:
    """Tests for the TrendAnalysisResult entity."""

    def test_is_bullish(self):
        result = TrendAnalysisResult(
            code="600519",
            current_price=1800.0,
            ma5=1780.0,
            ma10=1750.0,
            ma20=1700.0,
            bias_ma5=1.12,
            trend_status="多头排列",
            support_levels=[1700, 1650],
            resistance_levels=[1850, 1900],
            signals=["MA金叉"],
        )
        assert result.is_bullish() is True

    def test_is_bearish(self):
        result = TrendAnalysisResult(
            code="600519",
            current_price=1600.0,
            ma5=1780.0,
            ma10=1750.0,
            ma20=1700.0,
            bias_ma5=-0.09,
            trend_status="空头排列",
            support_levels=[1550, 1500],
            resistance_levels=[1700, 1750],
            signals=["MA死叉"],
        )
        assert result.is_bearish() is True

    def test_nearest_support(self):
        result = TrendAnalysisResult(
            code="600519", current_price=1800.0, ma5=1780.0, ma10=1750.0,
            ma20=1700.0, bias_ma5=1.12, trend_status="多头排列",
            support_levels=[1650, 1700], resistance_levels=[],
        )
        assert result.nearest_support() == 1700

    def test_nearest_resistance(self):
        result = TrendAnalysisResult(
            code="600519", current_price=1800.0, ma5=1780.0, ma10=1750.0,
            ma20=1700.0, bias_ma5=1.12, trend_status="多头排列",
            support_levels=[], resistance_levels=[1850, 1900],
        )
        assert result.nearest_resistance() == 1850


# ======================================================================
# Experiment tests
# ======================================================================


class TestExperiment:
    """Tests for the Experiment entity."""

    def test_is_complete(self):
        exp = Experiment(id="e1", name="test", swarm_run_id="r1", preset_name="base", status="completed")
        assert exp.is_complete() is True

    def test_is_not_complete(self):
        exp = Experiment(id="e1", name="test", swarm_run_id="r1", preset_name="base", status="running")
        assert exp.is_complete() is False

    def test_mark_as_failed_increments_version(self):
        exp = Experiment(id="e1", name="test", swarm_run_id="r1", preset_name="base", status="running", version=1)
        failed = exp.mark_as_failed()
        assert failed.status == "failed"
        assert failed.version == 2
        assert failed.id == "e1"  # ID preserved


# ======================================================================
# EvidenceNote tests
# ======================================================================


class TestEvidenceNote:
    """Tests for the EvidenceNote entity."""

    def test_defaults(self):
        note = EvidenceNote(source="test")
        assert note.title == ""
        assert note.confidence is None
        assert note.observed_at is None
        assert note.payload == {}


# ======================================================================
# DecisionContext tests
# ======================================================================


class TestDecisionContext:
    """Tests for the DecisionContext entity."""

    def test_defaults(self):
        ctx = DecisionContext(decision_id="d1", subject="AAPL analysis")
        assert ctx.input_snapshot == {}
        assert ctx.model_version == "unknown"
        assert ctx.reasoning_trace == []
        assert ctx.evidence == []
