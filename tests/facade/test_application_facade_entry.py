"""Application facade re-exports."""

from app.application.facade import AIFacade, BacktestFacade, MarketFacade


def test_application_facade_exports() -> None:
    assert MarketFacade is not None
    assert BacktestFacade is not None
    assert AIFacade is not None
