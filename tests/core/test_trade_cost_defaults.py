"""Trade cost default alignment with A-share fee schedule."""

from __future__ import annotations

from app.core.risk_controls import TradeCostParams


def test_trade_cost_dataclass_defaults():
    costs = TradeCostParams()
    assert costs.stamp_duty == 0.00025
    assert costs.stamp_tax_rate == 0.00025
    assert costs.transfer_fee == 0.00002
