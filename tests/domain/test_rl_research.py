"""Offline RL research sidecar tests."""

from __future__ import annotations

import pytest

from app.domain.alpha.rl_research import (
    RlLiveForbiddenError,
    assert_rl_research_only,
    infer_action,
    run_rl_research,
    state_index,
    train_q_policy,
)
from app.modules.data.services.feature_pipeline_bars import synthetic_day_bars
from app.modules.strategy.services.rl_research_service import (
    infer_rl_action,
    refuse_live_execution,
    rl_research_status,
    run_rl_research_tick,
)


def test_state_index_bins():
    assert state_index(-0.05, 0.0) != state_index(0.05, 0.0)
    assert 0 <= state_index(0.0, 0.0) < 9


def test_train_q_policy_on_synthetic():
    bars = synthetic_day_bars(periods=180)
    q, frame, metrics = train_q_policy(bars, episodes=3, seed=1)
    assert q.shape == (9, 2)
    assert len(frame) >= 40
    assert "valid_return" in metrics


def test_run_rl_research_persists(tmp_path, monkeypatch):
    monkeypatch.setattr("app.domain.alpha.rl_research._models_dir", lambda: tmp_path)
    result = run_rl_research(synthetic_day_bars(periods=160), spec_name="cn_day_v0", synthetic_bars=True)
    assert result.ok
    assert result.live_enabled is False
    assert result.policy_path
    assert (tmp_path / "cn_day_v0_latest.json").exists()
    inferred = infer_action(ret_1=0.02, ma_bias_5=0.01, spec_name="cn_day_v0")
    assert inferred["ok"] is True
    assert inferred["action"] in {"flat", "long"}
    assert inferred["live_enabled"] is False


def test_research_tick_never_live(monkeypatch, tmp_path):
    monkeypatch.setattr("app.domain.alpha.rl_research._models_dir", lambda: tmp_path)
    payload = run_rl_research_tick(prefer_live_bars=False, episodes=2, symbol="600519")
    assert payload["ok"] is True
    assert payload["live_enabled"] is False
    assert payload["synthetic_bars"] is True
    status = rl_research_status()
    assert status["live_enabled"] is False
    assert status["has_policy"] is True


def test_infer_via_service(monkeypatch, tmp_path):
    monkeypatch.setattr("app.domain.alpha.rl_research._models_dir", lambda: tmp_path)
    run_rl_research_tick(prefer_live_bars=False, episodes=2)
    out = infer_rl_action(ret_1=0.0, ma_bias_5=0.0)
    assert out["ok"] is True


def test_live_always_forbidden():
    with pytest.raises(RlLiveForbiddenError, match="rl_live"):
        refuse_live_execution()
    with pytest.raises(RlLiveForbiddenError):
        assert_rl_research_only()
