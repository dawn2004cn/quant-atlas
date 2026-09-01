"""MySQL signal observation repository uses scoped sessions per operation."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.infrastructure.repositories.mysql.mysql_signal_observation_repository import (
    MySQLSignalObservationRepository,
)


def test_list_observations_uses_fresh_session_per_call():
    session = MagicMock()
    session.execute.return_value.fetchall.return_value = []
    factory = MagicMock(return_value=session)
    factory.remove = MagicMock()

    repo = MySQLSignalObservationRepository(factory)
    assert repo.list_observations(user_id=1, status="open", limit=10) == []

    factory.assert_called_once()
    session.close.assert_called_once()
    factory.remove.assert_called_once()


def test_create_observation_commits_and_closes_session():
    session = MagicMock()
    factory = MagicMock(return_value=session)
    factory.remove = MagicMock()

    repo = MySQLSignalObservationRepository(factory)
    payload = {
        "id": "abc",
        "user_id": 1,
        "symbol": "600519",
        "market": "CN",
        "name": "Moutai",
        "entry_price": 1.0,
        "current_price": 1.0,
        "stop_loss": 0.9,
        "target_price": 1.1,
        "source": "test",
        "reason": "",
        "ai_summary": "",
        "status": "open",
        "trigger_status": "watching",
        "created_at": "2026-01-01 00:00:00",
        "updated_at": "2026-01-01 00:00:00",
        "closed_at": None,
        "close_reason": "",
        "peak_price": 1.0,
        "trough_price": 1.0,
        "max_gain_pct": 0.0,
        "max_drawdown_pct": 0.0,
        "notes": "",
    }
    repo.create_observation(payload)

    session.commit.assert_called_once()
    session.close.assert_called_once()
    factory.remove.assert_called_once()
