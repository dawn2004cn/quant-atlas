"""Tournament hard gates (REQ-SRS-04)."""

from app.modules.strategy.services.tournament.gates import passes_tournament_gates


def test_passes_when_sharpe_and_mdd_ok():
    assert passes_tournament_gates(sharpe=1.81, max_drawdown=0.11) is True


def test_fails_when_sharpe_too_low():
    assert passes_tournament_gates(sharpe=1.8, max_drawdown=0.05) is False


def test_fails_when_mdd_too_high():
    assert passes_tournament_gates(sharpe=2.0, max_drawdown=0.12) is False
