from app.core.typed_registry import get_registry


def _make_market_regime_service(reg, **kwargs):
    # Try to locate an existing regime service; fallback to dummy.
    try:
        # If a proper service exists, it would be registered under this name.
        return reg.get("market_regime_service")
    except Exception:
        from app.modules.strategy.services.market_regime.dummy_regime_service import DummyRegimeService
        return DummyRegimeService()

def _make_strategy_sop_service(reg, **kwargs):
    from app.modules.strategy.services.strategy_sop_service import StrategySOPService
    regime_service = reg.get("market_regime_service") or _make_market_regime_service(reg)
    return StrategySOPService(market_regime_service=regime_service)

def wire_strategy_sop():
    reg = get_registry()
    # Register the dummy regime service if not already present.
    if reg.get_or_none("market_regime_service") is None:
        reg.register_factory("market_regime_service", _make_market_regime_service)
    # Register the SOP service.
    reg.register_factory("strategy_sop_service", _make_strategy_sop_service)
    # Eagerly instantiate SOP service so it can be injected elsewhere.
    reg.get("strategy_sop_service")
