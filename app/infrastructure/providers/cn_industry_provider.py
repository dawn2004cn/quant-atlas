from __future__ import annotations
"""Industry provider implementation using Eastmoney industry map."""


from app.domain.ports import IndustryProvider
from app.infrastructure.providers.cn_em_industry_map import get_cn_industry_map_cached


class CnIndustryProvider(IndustryProvider):
    """Industry provider implementation for Chinese A-shares."""

    def get_industry_map(self, allow_fetch: bool = True) -> dict[str, str]:
        """Get industry mapping for stocks (code6 -> industry name)."""
        return get_cn_industry_map_cached(allow_fetch=allow_fetch)
