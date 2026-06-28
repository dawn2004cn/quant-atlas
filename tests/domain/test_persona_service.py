"""Regression tests for PersonaService (Phase 1.3)."""

from __future__ import annotations

import pytest

from app.domain.services.persona_service import (
    PERSONA_FEATURE_MASKS,
    PersonaService,
    PersonaTier,
    UserPersona,
)


@pytest.fixture
def persona_service() -> PersonaService:
    return PersonaService()


class TestPersonaTiers:
    """Persona tier definitions."""

    def test_tier_enum_values(self):
        assert PersonaTier.NOVICE.value == "novice"
        assert PersonaTier.DAY_TRADER.value == "day_trader"
        assert PersonaTier.STRATEGIST.value == "strategist"
        assert PersonaTier.INSTITUTION.value == "institution"

    def test_all_tiers_have_feature_masks(self):
        for tier in PersonaTier:
            assert tier in PERSONA_FEATURE_MASKS, f"Missing feature mask for {tier}"
            assert len(PERSONA_FEATURE_MASKS[tier]) > 0

    def test_novice_features_limited(self):
        mask = PERSONA_FEATURE_MASKS[PersonaTier.NOVICE]
        assert mask.get("show_alpha_mining") is False
        assert mask.get("show_vectorized_backtest") is False
        assert mask.get("enable_impact_model") is False
        assert mask.get("enable_rbac") is False
        assert mask.get("show_ai_mentor") is True
        assert mask.get("show_strategy_wizard") is True

    def test_strategist_has_advanced_features(self):
        mask = PERSONA_FEATURE_MASKS[PersonaTier.STRATEGIST]
        assert mask.get("show_alpha_mining") is True
        assert mask.get("show_qlib_backtest") is True
        assert mask.get("show_factor_pipeline") is True
        assert mask.get("enable_advanced_order") is True

    def test_institution_most_features_enabled(self):
        mask = PERSONA_FEATURE_MASKS[PersonaTier.INSTITUTION]
        enabled = sum(1 for v in mask.values() if v is True)
        assert enabled >= 25
        assert mask.get("show_nl_strategy") is False
        assert mask.get("show_copy_trading") is False
        assert mask.get("show_psychology_tracker") is False
        assert mask.get("show_strategy_wizard") is False


class TestPersonaService:
    """Persona assignment and feature derivation."""

    def test_assess_novice(self, persona_service):
        persona = persona_service.assess_persona(user_id=1, risk_tolerance=0.2, experience_score=0.1)
        assert persona.tier == PersonaTier.NOVICE
        assert persona.risk_tolerance == 0.2

    def test_assess_day_trader(self, persona_service):
        persona = persona_service.assess_persona(user_id=2, risk_tolerance=0.7, experience_score=0.5, trading_frequency="high")
        assert persona.tier == PersonaTier.DAY_TRADER

    def test_assess_strategist(self, persona_service):
        persona = persona_service.assess_persona(user_id=3, risk_tolerance=0.5, experience_score=0.8)
        assert persona.tier == PersonaTier.STRATEGIST

    def test_assess_high_experience_tier(self, persona_service):
        persona = persona_service.assess_persona(user_id=4, risk_tolerance=0.6, experience_score=0.95)
        assert persona.tier == PersonaTier.STRATEGIST

    def test_get_features_for_novice(self, persona_service):
        persona = persona_service.assess_persona(user_id=1, risk_tolerance=0.2, experience_score=0.1)
        features = persona_service.get_feature_mask(user_id=1)
        assert features.get("show_ai_mentor") is True
        assert features.get("show_alpha_mining") is False

    def test_get_features_for_strategist(self, persona_service):
        persona = persona_service.assess_persona(user_id=3, risk_tolerance=0.5, experience_score=0.8)
        features = persona_service.get_feature_mask(user_id=3)
        assert features.get("show_alpha_mining") is True
        assert features.get("enable_compliance_guardrail") is False

    def test_update_features_override(self, persona_service):
        persona_service.assess_persona(user_id=5, risk_tolerance=0.3, experience_score=0.2)
        updated = persona_service.update_features(user_id=5, overrides={"stranger_industries": ["new_energy", "biotech"]})
        assert updated is not None
        assert "stranger_industries" in updated.features
        assert "new_energy" in updated.features["stranger_industries"]

    def test_self_assessment_updates_risk(self, persona_service):
        persona = persona_service.assess_persona(user_id=6, risk_tolerance=0.5, experience_score=0.5)
        updated = persona_service.assess_persona(user_id=6, risk_tolerance=0.8, experience_score=0.7)
        assert updated.risk_tolerance == 0.8
        assert updated.experience_score == 0.7

    def test_persona_tier_ordering(self):
        """Novice < Retail < Boutique < DayTrader < Investment < Strategist < Fund < Institution"""
        tiers = list(PersonaTier)
        # Just verify it's defined and ordered as expected
        assert tiers.index(PersonaTier.NOVICE) < tiers.index(PersonaTier.INSTITUTION)

    def test_user_persona_dataclass(self):
        persona = UserPersona(user_id=100, tier=PersonaTier.NOVICE, risk_tolerance=0.3, experience_score=0.2)
        assert persona.user_id == 100
        assert persona.preferred_market == "CN"
        assert persona.trading_frequency == "medium"
        assert persona.features == {}
        assert persona.assessed_at is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
