from app.core.logger import get_logger
from app.core.typed_registry import get_registry

logger = get_logger(__name__)

def _make_fast_path_parameter_store(reg, **kwargs):
    from app.modules.execution.services.fast_path_parameter_store import FastPathParameterStore
    # In a real env, we'd inject a Redis client here
    return FastPathParameterStore(redis_client=None)

def _make_fast_path_orchestrator(reg, **kwargs):
    from app.modules.execution.services.fast_path_orchestrator import FastPathOrchestrator
    return FastPathOrchestrator(
        pre_trade_validator=reg.get("pre_trade_validator"),
        risk_guard=reg.get("risk_service"),
        execution_gateway=reg.get("borderless_execution_service"),
        parameter_store=reg.get("fast_path_parameter_store"),
    )

def _make_fast_path_trigger(reg, **kwargs):
    from app.modules.execution.services.fast_path_trigger_service import FastPathTriggerService
    from app.core.event_bus import get_event_bus
    return FastPathTriggerService(
        event_bus=get_event_bus(),
        orchestrator=reg.get("fast_path_orchestrator"),
        parameter_store=reg.get("fast_path_parameter_store"),
    )

def wire_execution_fast_path():
    reg = get_registry()
    reg.register_factory("fast_path_parameter_store", _make_fast_path_parameter_store)
    reg.register_factory("fast_path_orchestrator", _make_fast_path_orchestrator)
    reg.register_factory("fast_path_trigger", _make_fast_path_trigger)
    
    # Eagerly initialize the trigger service so it starts listening to events
    try:
        reg.get("fast_path_trigger")
    except Exception:
        logger.debug("fast_path_trigger not available, will init lazy")
