from __future__ import annotations

"""Stock profile probe capability."""


from typing import Any

from app.domain.capabilities.base import BaseCapability
from app.domain.enums import MarketCode
from app.infrastructure.capabilities.registry import capability


@capability("fetch_profile")
class ProfileCapability(BaseCapability):
    """Lightweight ticker validation via stock profile lookup."""

    capability_name = "fetch_profile"

    def __init__(self, **services: Any) -> None:
        self._market_provider = services.get("market_provider")

    def execute(
        self, symbol: str, market: MarketCode
    ) -> tuple[dict | None, str]:
        try:
            prof = self._market_provider.get_stock_profile(symbol, market)
        except Exception as exc:
            return None, f"get_stock_profile 失败: {exc!s}."
        if not prof:
            return None, "get_stock_profile 返回空。"
        return prof, "档案拉取成功。"
