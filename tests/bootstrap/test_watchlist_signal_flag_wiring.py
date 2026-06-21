from __future__ import annotations

from app.bootstrap_components.wiring_market import (
    _make_signal_flag_service,
    _make_watchlist_agent_service,
    _make_watchlist_experience_service,
)


class _Registry:
    def __init__(self, *, agent: object | None = None) -> None:
        self.agent = agent
        self.review_service = object()

    def get(self, name: str) -> object:
        if name == "watchlist_agent_service":
            return self.agent or object()
        if name == "review_tracking_service":
            return self.review_service
        return object()

    def get_or_none(self, name: str) -> object | None:
        return self.get(name)


def test_watchlist_agent_factory_registers_expected_methods() -> None:
    service = _make_watchlist_agent_service(_Registry())

    assert service.build_snapshot is not None
    assert service.subscribe_to_events is not None


def test_watchlist_experience_factory_uses_registered_agent() -> None:
    agent = object()
    service = _make_watchlist_experience_service(_Registry(agent=agent))

    assert service._agent is agent


def test_watchlist_experience_factory_allows_missing_review_service() -> None:
    class RegistryWithoutReview:
        def get(self, name: str) -> object:
            if name == "watchlist_agent_service":
                return object()
            return object()

        def get_or_none(self, name: str) -> None:
            return None

    service = _make_watchlist_experience_service(RegistryWithoutReview())

    assert service._review is None


def test_signal_flag_factory_registers_expected_methods(monkeypatch) -> None:
    repository = object()
    monkeypatch.setattr(
        "app.infrastructure.repositories.deps.create_signal_flag_pool_repository",
        lambda _settings, session_factory=None: repository,
    )

    service = _make_signal_flag_service(_Registry())

    assert service.run_scan is not None
    assert service.list_dates is not None
    assert service.get_pool is not None


def test_signal_flag_pool_facade_importable() -> None:
    from app.infrastructure.repositories.common.facades.signal_flag_pool_repository import (
        SignalFlagPoolRepository,
    )

    assert SignalFlagPoolRepository is not None
