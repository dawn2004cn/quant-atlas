from app.core.event_bus import get_event_bus, enable_websocket_broadcast, TradeExecutedEvent
import logging

logging.basicConfig(level=logging.DEBUG)

def mock_broadcast(room, event_name, data):
    print(f'  [WS Broadcast] {room}: {event_name}')

enable_websocket_broadcast(mock_broadcast)

bus = get_event_bus()

# Add subscriber
def on_trade(event):
    print(f'  Handler received: {event.action}')

bus.subscribe(TradeExecutedEvent, on_trade)

# Publish
event = TradeExecutedEvent(
    user_id='user123',
    symbol='600519',
    action='buy',
    quantity=100,
    price=1500.0
)
print('Publishing...')
bus.publish(event)
print('Done')