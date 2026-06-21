"""Test quant_plan.md components."""
from datetime import datetime
from app.domain.contract import AlphaEntity, AlphaSource, AlphaStatus, Signal, SignalType, SignalStrength
from app.infrastructure.persistence import get_knowledge_store, ExperimentRecord
from app.application.workflow import get_autopilot, AutopilotConfig

print('=== Phase 1: Contract Layer ===')
alpha = AlphaEntity(
    id='test-001',
    formula='rank(returns_0_1)',
    name='Test Alpha',
    source=AlphaSource.RD_AGENT,
    status=AlphaStatus.EXPERIMENT,
)
print(f'  Alpha: {alpha.name}')
print(f'  Production ready: {alpha.is_production_ready()}')

signal = Signal(
    id='sig-001',
    symbol='600519',
    signal_type=SignalType.LONG,
    strength=SignalStrength.STRONG,
    timestamp=datetime.now(),
    source_agent='quant_team',
    confidence=0.8,
    reasoning='Strong momentum'
)
print(f'  Signal: {signal.signal_type.value} {signal.symbol}')

print('\n=== Phase 1: Knowledge Store ===')
store = get_knowledge_store()
print(f'  Store: {type(store).__name__}')

record = ExperimentRecord(
    run_id='test-run-001',
    formula='rank(TS_MEAN(close, 20))',
    goal='alpha_discovery',
    status='completed',
    metrics={'ic': 0.05, 'sharpe': 1.2},
    tags=['momentum', '20d']
)
store.store_experiment(record)
print(f'  Stored: {record.run_id}')

print('\n=== Phase 3: Autopilot ===')
config = AutopilotConfig(drift_threshold=0.15, auto_deploy_enabled=True)
ap = get_autopilot(config)
status = ap.get_status()
print(f'  State: {status["state"]}')
print(f'  Regime: {status["current_regime"]}')

report = ap.check_drift('strategy_a', backtest_return=0.20, live_return=0.05)
if report:
    print(f'  Drift: {report.severity.value} ({report.drift_percentage:.1%})')

print('\n=== quant_plan.md Refactoring Complete ===')