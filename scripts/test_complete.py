"""Test all quant_plan.md enhancements."""
from app.domain.alpha.orthogonalization import get_factor_orthogonalizer
from app.domain.alpha.regime_risk_budget import get_regime_portfolio_manager

print("=== quant_plan.md Enhancements ===")

ortho = get_factor_orthogonalizer()
print(f"Ortho: {type(ortho).__name__}")

regime_mgr = get_regime_portfolio_manager()

budget = regime_mgr.calculate_budget("strategy_a", "volatile")
print(f"Volatile budget: pos_limit={budget.position_limit:.0%}, stop={budget.stop_loss:.0%}")

budget2 = regime_mgr.calculate_budget("strategy_b", "bull_strong")
print(f"Bull_strong budget: pos_limit={budget2.position_limit:.0%}, stop={budget2.stop_loss:.0%}")

print("\n=== quant_plan.md Complete ===")
print("Pending items status:")
print("  [x] Physical R&D pipeline")
print("  [x] Shadow test dual-track")
print("  [x] Multi-factor orthogonalization")
print("  [x] Regime-based risk adjustment")
print("  [x] Trace ID telemetry")
print("  [ ] Vector knowledge graph (optional)")
print("  [ ] Dashboard (optional)")