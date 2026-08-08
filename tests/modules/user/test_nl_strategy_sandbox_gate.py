"""NL strategy sandbox / tournament candidacy gate (REQ-SRS / C4)."""

from __future__ import annotations

from app.modules.user.services.nl_strategy_service import NLStrategyTemplate, NLToStrategyService


def test_estimated_preview_blocks_candidate():
    svc = NLToStrategyService()
    strategy = svc.parse("RSI 超卖买入", user_id=0)
    out = svc.apply_sandbox_gate(strategy, {"status": "estimated", "warning": "使用估计指标"})
    assert out["candidate_ready"] is False
    assert strategy.candidate_ready is False
    assert strategy.sandbox_status == "blocked_estimated"


def test_successful_preview_marks_candidate_ready():
    svc = NLToStrategyService()
    strategy = svc.parse("MACD 金叉", user_id=0)
    out = svc.apply_sandbox_gate(
        strategy,
        {
            "status": "ok",
            "metrics": {"sharpe_ratio": 1.2, "max_drawdown": "8%", "win_rate": "55%"},
        },
    )
    assert out["candidate_ready"] is True
    assert strategy.candidate_ready is True
    assert strategy.sandbox_status == "passed"
    assert out["bias_passed"] is False  # no bars → bias pending until explicit clearance


def test_render_strategy_source_is_python():
    svc = NLToStrategyService()
    strategy = svc.parse("突破买入", user_id=0)
    src = svc.render_strategy_source(strategy)
    assert "def strategy_signal" in src
    assert strategy.strategy_id in src
