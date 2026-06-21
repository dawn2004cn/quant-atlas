"""User persona service.

Maps user risk profile and trading experience to a persona tier.
Controls UI complexity exposure (plan 1.3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class PersonaTier(str, Enum):
    NOVICE = "novice"             # Tier 0: 新手散户
    RETAIL = "retail"             # Tier 1: 散户
    BOUTIQUE = "boutique"         # Tier 2: 量化小团队
    DAY_TRADER = "day_trader"     # Tier 2.5: 日内交易者
    INVESTMENT = "investment"     # Tier 3: 投资公司/家族办公室
    STRATEGIST = "strategist"     # Tier 3.5: 策略师
    FUND = "fund"                 # Tier 4: 基金公司
    INSTITUTION = "institution"   # Tier 5: 大型机构

@dataclass(frozen=True)
class UserPersona:
    user_id: int
    tier: PersonaTier
    risk_tolerance: float        # 0.0 (conservative) - 1.0 (aggressive)
    experience_score: float      # 0.0 - 1.0
    preferred_market: str = "CN"
    trading_frequency: str = "medium"  # low / medium / high
    features: dict[str, Any] = field(default_factory=dict)
    assessed_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


# Feature masks per tier: what UI components to show/hide
PERSONA_FEATURE_MASKS: dict[PersonaTier, dict[str, bool]] = {
    PersonaTier.NOVICE: {
        "show_nl_strategy": True,
        "show_ai_mentor": True,
        "show_copy_trading": True,
        "show_psychology_tracker": True,
        "show_strategy_wizard": True,
        "show_fast_backtest": True,
        "show_preflight_card": True,
        "show_stop_confirm": True,
        "show_review_card": True,
        "show_ai_hit_rate": True,
        "show_risk_banner": True,
        "show_alpha_mining": False,
        "show_vectorized_backtest": False,
        "show_qlib_backtest": False,
        "show_factor_pipeline": False,
        "show_agent_topology": False,
        "show_zk_proof": False,
        "show_mesh_graph": False,
        "show_macro_indices": True,
        "show_signal_flags": True,
        "show_observation_cards": True,
        "enable_advanced_order": False,
        "enable_algo_trading": False,
        "enable_compliance_guardrail": False,
        "enable_brinson_attribution": False,
        "enable_audit_trail": False,
        "enable_master_slave": False,
        "enable_impact_model": False,
        "enable_rbac": False,
    },
    PersonaTier.DAY_TRADER: {
        "show_nl_strategy": True,
        "show_ai_mentor": True,
        "show_copy_trading": True,
        "show_psychology_tracker": True,
        "show_strategy_wizard": True,
        "show_fast_backtest": True,
        "show_preflight_card": True,
        "show_stop_confirm": True,
        "show_review_card": True,
        "show_ai_hit_rate": True,
        "show_risk_banner": True,
        "show_alpha_mining": False,
        "show_vectorized_backtest": False,
        "show_qlib_backtest": False,
        "show_factor_pipeline": False,
        "show_agent_topology": False,
        "show_zk_proof": False,
        "show_mesh_graph": False,
        "show_macro_indices": True,
        "show_signal_flags": True,
        "show_observation_cards": True,
        "enable_advanced_order": True,
        "enable_algo_trading": False,
        "enable_compliance_guardrail": False,
        "enable_brinson_attribution": False,
        "enable_audit_trail": False,
        "enable_master_slave": False,
        "enable_impact_model": False,
        "enable_rbac": False,
    },
    PersonaTier.STRATEGIST: {
        "show_nl_strategy": True,
        "show_ai_mentor": True,
        "show_copy_trading": False,
        "show_psychology_tracker": True,
        "show_strategy_wizard": True,
        "show_fast_backtest": True,
        "show_preflight_card": True,
        "show_stop_confirm": True,
        "show_review_card": True,
        "show_ai_hit_rate": True,
        "show_risk_banner": True,
        "show_alpha_mining": True,
        "show_vectorized_backtest": True,
        "show_qlib_backtest": True,
        "show_factor_pipeline": True,
        "show_agent_topology": True,
        "show_zk_proof": False,
        "show_mesh_graph": False,
        "show_macro_indices": True,
        "show_signal_flags": True,
        "show_observation_cards": True,
        "enable_advanced_order": True,
        "enable_algo_trading": True,
        "enable_compliance_guardrail": False,
        "enable_brinson_attribution": False,
        "enable_audit_trail": False,
        "enable_master_slave": False,
        "enable_impact_model": False,
        "enable_rbac": False,
    },
    PersonaTier.RETAIL: {
        "show_nl_strategy": True,
        "show_ai_mentor": True,
        "show_copy_trading": True,
        "show_psychology_tracker": True,
        "show_strategy_wizard": True,
        "show_fast_backtest": True,
        "show_preflight_card": True,
        "show_stop_confirm": True,
        "show_review_card": True,
        "show_ai_hit_rate": True,
        "show_risk_banner": True,
        "show_alpha_mining": False,
        "show_vectorized_backtest": False,
        "show_qlib_backtest": False,
        "show_factor_pipeline": False,
        "show_agent_topology": False,
        "show_zk_proof": False,
        "show_mesh_graph": False,
        "show_macro_indices": True,
        "show_signal_flags": True,
        "show_observation_cards": True,
        "enable_advanced_order": False,
        "enable_algo_trading": False,
        "enable_compliance_guardrail": False,
        "enable_brinson_attribution": False,
        "enable_audit_trail": False,
        "enable_master_slave": False,
        "enable_impact_model": False,
        "enable_rbac": False,
    },
    PersonaTier.BOUTIQUE: {
        "show_nl_strategy": True,
        "show_ai_mentor": True,
        "show_copy_trading": False,
        "show_psychology_tracker": False,
        "show_strategy_wizard": True,
        "show_fast_backtest": True,
        "show_preflight_card": True,
        "show_stop_confirm": True,
        "show_review_card": True,
        "show_ai_hit_rate": True,
        "show_risk_banner": True,
        "show_alpha_mining": True,
        "show_vectorized_backtest": True,
        "show_qlib_backtest": True,
        "show_factor_pipeline": True,
        "show_agent_topology": False,
        "show_zk_proof": False,
        "show_mesh_graph": False,
        "show_macro_indices": True,
        "show_signal_flags": True,
        "show_observation_cards": True,
        "enable_advanced_order": True,
        "enable_algo_trading": False,
        "enable_compliance_guardrail": False,
        "enable_brinson_attribution": False,
        "enable_audit_trail": False,
        "enable_master_slave": False,
        "enable_impact_model": False,
        "enable_rbac": False,
    },
    PersonaTier.INVESTMENT: {
        "show_nl_strategy": True,
        "show_ai_mentor": True,
        "show_copy_trading": False,
        "show_psychology_tracker": False,
        "show_strategy_wizard": True,
        "show_fast_backtest": True,
        "show_preflight_card": True,
        "show_stop_confirm": True,
        "show_review_card": True,
        "show_ai_hit_rate": True,
        "show_risk_banner": True,
        "show_alpha_mining": True,
        "show_vectorized_backtest": True,
        "show_qlib_backtest": True,
        "show_factor_pipeline": True,
        "show_agent_topology": True,
        "show_zk_proof": False,
        "show_mesh_graph": False,
        "show_macro_indices": True,
        "show_signal_flags": True,
        "show_observation_cards": True,
        "enable_advanced_order": True,
        "enable_algo_trading": True,
        "enable_compliance_guardrail": False,
        "enable_brinson_attribution": False,
        "enable_audit_trail": False,
        "enable_master_slave": False,
        "enable_impact_model": False,
        "enable_rbac": False,
    },
    PersonaTier.FUND: {
        "show_nl_strategy": False,
        "show_ai_mentor": True,
        "show_copy_trading": False,
        "show_psychology_tracker": False,
        "show_strategy_wizard": True,
        "show_fast_backtest": True,
        "show_preflight_card": True,
        "show_stop_confirm": True,
        "show_review_card": True,
        "show_ai_hit_rate": True,
        "show_risk_banner": True,
        "show_alpha_mining": True,
        "show_vectorized_backtest": True,
        "show_qlib_backtest": True,
        "show_factor_pipeline": True,
        "show_agent_topology": True,
        "show_zk_proof": True,
        "show_mesh_graph": True,
        "show_macro_indices": True,
        "show_signal_flags": True,
        "show_observation_cards": True,
        "enable_advanced_order": True,
        "enable_algo_trading": True,
        "enable_compliance_guardrail": True,
        "enable_brinson_attribution": True,
        "enable_audit_trail": True,
        "enable_master_slave": True,
        "enable_impact_model": False,
        "enable_rbac": False,
    },
    PersonaTier.INSTITUTION: {
        "show_nl_strategy": False,
        "show_ai_mentor": True,
        "show_copy_trading": False,
        "show_psychology_tracker": False,
        "show_strategy_wizard": False,
        "show_fast_backtest": True,
        "show_preflight_card": True,
        "show_stop_confirm": True,
        "show_review_card": True,
        "show_ai_hit_rate": True,
        "show_risk_banner": True,
        "show_alpha_mining": True,
        "show_vectorized_backtest": True,
        "show_qlib_backtest": True,
        "show_factor_pipeline": True,
        "show_agent_topology": True,
        "show_zk_proof": True,
        "show_mesh_graph": True,
        "show_macro_indices": True,
        "show_signal_flags": True,
        "show_observation_cards": True,
        "enable_advanced_order": True,
        "enable_algo_trading": True,
        "enable_compliance_guardrail": True,
        "enable_brinson_attribution": True,
        "enable_audit_trail": True,
        "enable_master_slave": True,
        "enable_impact_model": True,
        "enable_rbac": True,
    },
}
class PersonaService:
    """Determine and serve user persona for UI adaptation."""

    def __init__(self) -> None:
        self._personas: dict[int, UserPersona] = {}

    def assess_persona(
        self,
        user_id: int,
        *,
        risk_tolerance: float | None = None,
        experience_score: float | None = None,
        trading_frequency: str | None = None,
    ) -> UserPersona:
        """Assess (or reassess) a user's persona tier based on inputs.

        Risk tolerance and experience score are 0-1 floats.
        Trading frequency: low / medium / high.
        """
        rt = max(0.0, min(1.0, risk_tolerance if risk_tolerance is not None else 0.3))
        es = max(0.0, min(1.0, experience_score if experience_score is not None else 0.1))
        tf = (trading_frequency or "medium").strip().lower()
        if tf not in ("low", "medium", "high"):
            tf = "medium"

        # Simple heuristic to determine tier
        if es >= 0.7 and rt >= 0.5:
            tier = PersonaTier.STRATEGIST
        elif tf == "high" or (rt >= 0.5 and es >= 0.3):
            tier = PersonaTier.DAY_TRADER
        else:
            tier = PersonaTier.NOVICE

        persona = UserPersona(
            user_id=user_id,
            tier=tier,
            risk_tolerance=rt,
            experience_score=es,
            trading_frequency=tf,
            features=PERSONA_FEATURE_MASKS[tier].copy(),
        )
        self._personas[user_id] = persona
        return persona

    def get_persona(self, user_id: int) -> UserPersona | None:
        """Get cached persona, or return None if not yet assessed."""
        return self._personas.get(user_id)

    def get_or_assess_default(self, user_id: int) -> UserPersona:
        """Get persona or create a default Novice assessment."""
        p = self.get_persona(user_id)
        if p is not None:
            return p
        return self.assess_persona(user_id)

    def get_feature_mask(self, user_id: int) -> dict[str, bool]:
        """Get UI feature mask for the user's persona tier."""
        p = self.get_or_assess_default(user_id)
        return p.features

    def get_persona_tier(self, user_id: int) -> PersonaTier:
        """Get just the tier label."""
        p = self.get_or_assess_default(user_id)
        return p.tier

    def update_features(self, user_id: int, overrides: dict[str, bool]) -> UserPersona | None:
        """Allow user to manually override specific features."""
        p = self.get_persona(user_id)
        if p is None:
            return None
        merged = {**p.features, **overrides}
        persona = UserPersona(
            user_id=p.user_id,
            tier=p.tier,
            risk_tolerance=p.risk_tolerance,
            experience_score=p.experience_score,
            preferred_market=p.preferred_market,
            trading_frequency=p.trading_frequency,
            features=merged,
        )
        self._personas[user_id] = persona
        return persona


_persona_service: PersonaService | None = None


def get_persona_service() -> PersonaService:
    global _persona_service
    if _persona_service is None:
        _persona_service = PersonaService()
    return _persona_service


__all__ = [
    "PersonaService",
    "UserPersona",
    "PersonaTier",
    "PERSONA_FEATURE_MASKS",
    "get_persona_service",
]
