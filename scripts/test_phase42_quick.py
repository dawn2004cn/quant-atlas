"""Quick test for Phase 42."""
from app.domain.market_data.data_bus import MarketDataBus, Observable, Subscriber, Tick
from app.domain.market_data.stream_processor import MarketStreamProcessor
from app.domain.market_data.tick_handler import TickValidator, TickAnomalyDetector

class TestSub(Subscriber):
    def __init__(self):
        self.received = []
    def on_tick(self, tick):
        self.received.append(tick)
    def on_error(self, e):
        pass

# Test Observable
obs = Observable('test')
sub = TestSub()
obs.subscribe(sub)
tick = Tick(symbol='BTC', price=50000.0, volume=1.0, amount=50000.0)
count = obs.push(tick)
assert count == 1
assert len(sub.received) == 1
print('Observable test passed')

# Test MarketDataBus
bus = MarketDataBus()
bus.publish(tick)
stats = bus.get_stats()
assert stats['total_ticks'] == 1
print('Bus test passed')

# Test StreamProcessor
proc = MarketStreamProcessor('BTC', window_size=10)
for i in range(5):
    proc.on_tick(Tick(symbol='BTC', price=100.0+i, volume=1.0, amount=100.0+i))
stats = proc.get_stats()
assert stats.tick_count == 5
print('StreamProcessor test passed')

# Test Validator
valid, msg = TickValidator.validate(tick)
assert valid is True
print('Validator test passed')

# Test AnomalyDetector
detector = TickAnomalyDetector(threshold_pct=5.0)
tick1 = Tick(symbol='BTC', price=100.0, volume=1.0, amount=100.0)
tick2 = Tick(symbol='BTC', price=120.0, volume=1.0, amount=120.0)
assert detector.detect(tick1) is False
assert detector.detect(tick2) is True
print('Anomaly test passed')

print('All Phase 42 tests passed!')