from __future__ import annotations

from app.core.base_service import BaseApplicationService


class DummyRegimeService(BaseApplicationService):
    """Fallback regime service when no real market regime logic is present.
    Always reports a neutral regime.
    """

    def get_current_regime(self, symbol: str) -> str:
        return "neutral"
