"""Infrastructure adapters."""

from .legacy_tdx_adapter import LegacyTdxAdapter
from .tencent_quote_gateway import TencentQuoteGateway

__all__ = ["LegacyTdxAdapter", "TencentQuoteGateway"]
