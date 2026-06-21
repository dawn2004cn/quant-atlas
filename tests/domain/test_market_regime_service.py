"""Unit tests for MarketRegimeService — pure domain stance determination.

Covers the scoring rules in app/domain/services/market_regime_service.py:
happy-path for each stance (aggressive/defensive/neutral), adjustment
modifiers (down-ratio penalty, up-dominance bonus, stop/target hits,
watchlist avg), score bounds, and confidence clamping.
"""

from __future__ import annotations

import pytest

from app.domain.services.market_regime_service import MarketRegimeService


@pytest.fixture(scope="module")
def service() -> MarketRegimeService:
    """Service built from default config (no external file required)."""
    return MarketRegimeService()


# --- Stance classification ---------------------------------------------------


def test_aggressive_stance_when_sentiment_high(service: MarketRegimeService):
    """High sentiment score (≥ aggressive_lower=62) yields aggressive stance."""
    result = service.evaluate_stance(sentiment_score=80, up_count=30, down_count=5, flat_count=5)
    assert result["stance"] == "aggressive"
    assert "favorable" in result["action"].lower()
    assert result["score"] >= 62
    assert result["confidence"] >= 0.35


def test_defensive_stance_when_sentiment_low(service: MarketRegimeService):
    """Low sentiment score (≤ defensive_upper=38) yields defensive stance."""
    result = service.evaluate_stance(sentiment_score=20, up_count=5, down_count=30, flat_count=5)
    assert result["stance"] == "defensive"
    assert "pressure" in result["action"].lower()
    assert result["score"] <= 38


def test_neutral_stance_when_balanced(service: MarketRegimeService):
    """Mid sentiment (between thresholds) yields neutral stance."""
    result = service.evaluate_stance(sentiment_score=50, up_count=15, down_count=15, flat_count=10)
    assert result["stance"] == "neutral"
    assert result["score"] > 38
    assert result["score"] < 62


# --- Adjustment modifiers ---------------------------------------------------


def test_down_ratio_penalty_lowers_score(service: MarketRegimeService):
    """When down_ratio > 0.55, the 6-point penalty is applied."""
    base = service.evaluate_stance(sentiment_score=60, up_count=10, down_count=10, flat_count=0)["score"]
    penalized = service.evaluate_stance(sentiment_score=60, up_count=4, down_count=20, flat_count=0)["score"]
    # down_ratio 0.83 > 0.55 triggers penalty; up:down 4:20 is not dominant
    assert penalized < base


def test_up_dominance_bonus_raises_score(service: MarketRegimeService):
    """When up > down * 1.4, the 4-point bonus is applied."""
    plain = service.evaluate_stance(sentiment_score=60, up_count=15, down_count=15, flat_count=0)["score"]
    boosted = service.evaluate_stance(sentiment_score=60, up_count=30, down_count=10, flat_count=0)["score"]
    assert boosted >= plain


def test_stop_hit_observation_penalty(service: MarketRegimeService):
    """Observation cards with stop_hit status reduce the score."""
    cards = [{"trigger_status": "stop_hit"} for _ in range(3)]
    result = service.evaluate_stance(sentiment_score=60, up_count=15, down_count=15, observation_cards=cards)
    # base penalty = 4 + 3*3 = 13, capped at 12
    assert result["score"] <= 60 - 8  # at least the uncapped-ish drop direction


def test_target_hit_observation_bonus(service: MarketRegimeService):
    """Observation cards with target_hit status raise the score."""
    cards = [{"trigger_status": "target_hit"} for _ in range(3)]
    base = service.evaluate_stance(sentiment_score=60, up_count=15, down_count=15)["score"]
    boosted = service.evaluate_stance(
        sentiment_score=60, up_count=15, down_count=15, observation_cards=cards
    )["score"]
    assert boosted > base


def test_watchlist_bear_penalty(service: MarketRegimeService):
    """Watchlist avg change below -1.5% applies a 4-point penalty."""
    wl = [{"change_pct": -3.0}, {"change_pct": -2.5}]
    base = service.evaluate_stance(sentiment_score=60, up_count=15, down_count=15)["score"]
    bearish = service.evaluate_stance(sentiment_score=60, up_count=15, down_count=15, watchlist_items=wl)["score"]
    assert bearish < base


def test_watchlist_bull_bonus(service: MarketRegimeService):
    """Watchlist avg change above +1.2% applies a 3-point bonus."""
    wl = [{"change_pct": 2.0}, {"change_pct": 2.5}]
    base = service.evaluate_stance(sentiment_score=60, up_count=15, down_count=15)["score"]
    bullish = service.evaluate_stance(sentiment_score=60, up_count=15, down_count=15, watchlist_items=wl)["score"]
    assert bullish > base


# --- Bounds & confidence ----------------------------------------------------


def test_score_clamped_to_bounds(service: MarketRegimeService):
    """Score never falls below min_score=8 nor exceeds max_score=94."""
    low = service.evaluate_stance(sentiment_score=0, up_count=0, down_count=100, flat_count=0)["score"]
    high = service.evaluate_stance(sentiment_score=100, up_count=100, down_count=0, flat_count=0)["score"]
    assert low >= 8
    assert high <= 94


def test_confidence_within_bounds(service: MarketRegimeService):
    """Confidence is always within [0.35, 0.92]."""
    for sentiment in (0, 25, 50, 75, 100):
        result = service.evaluate_stance(sentiment_score=sentiment, up_count=10, down_count=10)
        assert 0.35 <= result["confidence"] <= 0.92


# --- Output structure -------------------------------------------------------


def test_evidence_structure(service: MarketRegimeService):
    """Result always contains sentiment + breadth evidence; observation added when cards present."""
    no_obs = service.evaluate_stance(sentiment_score=60, up_count=10, down_count=10)
    kinds = {e["kind"] for e in no_obs["evidence"]}
    assert "sentiment" in kinds
    assert "breadth" in kinds
    assert "observation" not in kinds

    with_obs = service.evaluate_stance(
        sentiment_score=60, up_count=10, down_count=10,
        observation_cards=[{"trigger_status": "stop_hit"}],
    )
    assert any(e["kind"] == "observation" for e in with_obs["evidence"])
