from __future__ import annotations
"""Concrete ACL implementation for AkShare Market Data."""

from typing import Any, List
from app.infrastructure.external.acl.market_data_acl import IMarketDataACL
import akshare as ak

class AkShareMarketDataACL(IMarketDataACL):
    """Translates AkShare response to Quant Atlas Domain Schema."""

    def fetch_standardized_data(self, symbol: str, start_date: str, end_date: str) -> List[dict[str, Any]]:
        # Fetch raw data
        df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date)
        
        # Mapping raw data to Domain DTO format
        standardized = []
        for _, row in df.iterrows():
            standardized.append({
                "trade_date": str(row["日期"]),
                "code": symbol,
                "price": float(row["收盘"]),
                "volume": float(row["成交量"]),
                "raw": row.to_dict()
            })
        return standardized
