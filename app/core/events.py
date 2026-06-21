"""Event bus implementation using blinker."""

from blinker import signal

# Define core events
market_data_synced = signal("market-data-synced")
risk_alert_triggered = signal("risk-alert-triggered")
factor_research_completed = signal("factor-research-completed")
