"""Fee schedule tests (SRS tiered commission)."""

from app.domain.trading.fee_schedule import (
    FeeBreakdown,
    get_fee_schedule,
    list_fee_schedule_ids,
)


def test_list_builtin_schedules():
    ids = list_fee_schedule_ids()
    assert "cn_a_retail_v1" in ids
    assert "crypto_flat_v1" in ids


def test_cn_a_retail_applies_min_commission_and_stamp_on_sell():
    sched = get_fee_schedule("cn_a_retail_v1")
    buy = sched.calculate(notional=1000.0, side="buy")
    assert isinstance(buy, FeeBreakdown)
    assert buy.fee_schedule_id == "cn_a_retail_v1"
    assert buy.commission >= 5.0  # min
    assert buy.stamp_tax == 0.0
    sell = sched.calculate(notional=100_000.0, side="sell")
    assert sell.stamp_tax > 0
    assert sell.total > sell.commission


def test_crypto_flat_no_stamp():
    sched = get_fee_schedule("crypto_flat_v1")
    fee = sched.calculate(notional=10_000.0, side="sell")
    assert fee.stamp_tax == 0.0
    assert fee.total == fee.commission


def test_unknown_schedule_raises():
    import pytest

    with pytest.raises(KeyError):
        get_fee_schedule("no_such_schedule")
