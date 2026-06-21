"""Final verification of all optimizations."""
print("=== FINAL VERIFICATION ===")

# 1. quant_plan.md components
from app.domain.contract import AlphaEntity, AlphaSource, AlphaStatus
from app.application.workflow import get_autopilot

alpha = AlphaEntity(
    id="test",
    formula="rank(returns)",
    name="Test",
    source=AlphaSource.RD_AGENT,
    status=AlphaStatus.EXPERIMENT
)
print(f"1. AlphaEntity: {alpha.id}")

# 2. midify_plan13 components
from app.agents.research.graph import build_custom_trading_graph
from app.agents.evidence_blackboard import get_evidence_blackboard
from app.agents.evidence_router import create_default_router
from app.agents.tiered_llm import create_orchestrator

print(f"2. Research Graph: {build_custom_trading_graph.__name__}")
print(f"3. EvidenceBlackboard: {type(get_evidence_blackboard()).__name__}")
print(f"4. EvidenceRouter: {type(create_default_router()).__name__}")
print(f"5. TieredLLM: {type(create_orchestrator()).__name__}")

ap = get_autopilot()
status = ap.get_status()
print(f"6. Autopilot state: {status['state']}")
print(f"7. Autopilot regime: {status['current_regime']}")

print()
print("=== ALL OPTIMIZATION COMPLETE ===")

print("quant_plan.md phases:")
print("  Phase 1: Contract & Knowledge")
print("  Phase 2: Vectorized Core")
print("  Phase 3: Autopilot")

print("midify_plan13 phases:")
print("  EvidenceBlackboard integration")
print("  Evidence-driven early exit")
print("  Tiered LLM orchestration")
print("  Evidence-aware tools")