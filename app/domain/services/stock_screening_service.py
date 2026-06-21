from __future__ import annotations
"""Stock Screening Domain Service.

Pure domain logic for stock filtering and screening.
"""


from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class ScreeningCriteria(str, Enum):
    """Screening criteria types."""
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    VOLUME_ABOVE = "volume_above"
    PE_ABOVE = "pe_above"
    PE_BELOW = "pe_below"
    INDUSTRY = "industry"
    MARKET_CAP_ABOVE = "market_cap_above"
    TURNOVER_RATIO_ABOVE = "turnover_ratio_above"
    CHANGE_PCT_ABOVE = "change_pct_above"
    CHANGE_PCT_BELOW = "change_pct_below"


@dataclass(frozen=True)
class PriceRange:
    """Price range value object."""
    min_price: float = 0.0
    max_price: float = float("inf")
    
    def contains(self, price: float) -> bool:
        return self.min_price <= price <= self.max_price


@dataclass(frozen=True)
class ScreeningRule:
    """A single screening rule."""
    criteria: ScreeningCriteria
    value: Any
    operator: str = "gte"  # gte, lte, eq, ne
    
    def matches(self, stock_data: dict) -> bool:
        """Check if stock data matches this rule."""
        field_map = {
            ScreeningCriteria.PRICE_ABOVE: "price",
            ScreeningCriteria.PRICE_BELOW: "price",
            ScreeningCriteria.VOLUME_ABOVE: "volume",
            ScreeningCriteria.PE_ABOVE: "pe",
            ScreeningCriteria.PE_BELOW: "pe",
            ScreeningCriteria.INDUSTRY: "industry",
            ScreeningCriteria.MARKET_CAP_ABOVE: "total_market_cap",
            ScreeningCriteria.TURNOVER_RATIO_ABOVE: "turnover_ratio",
            ScreeningCriteria.CHANGE_PCT_ABOVE: "change_pct",
            ScreeningCriteria.CHANGE_PCT_BELOW: "change_pct",
        }
        
        field = field_map.get(self.criteria)
        if field is None:
            return True
        
        stock_value = stock_data.get(field, 0)
        
        if self.operator == "gte":
            return stock_value >= self.value
        elif self.operator == "lte":
            return stock_value <= self.value
        elif self.operator == "eq":
            return stock_value == self.value
        elif self.operator == "gt":
            return stock_value > self.value
        elif self.operator == "lt":
            return stock_value < self.value
        
        return True


class StockScreeningService:
    """Domain service for stock screening."""
    
    def __init__(self):
        self._rules: list[ScreeningRule] = []
    
    def add_rule(self, rule: ScreeningRule) -> "StockScreeningService":
        """Add a screening rule (fluent interface)."""
        self._rules.append(rule)
        return self
    
    def with_price_range(self, min_price: float = 0, max_price: float = float("inf")) -> "StockScreeningService":
        """Add price range rule."""
        if min_price > 0:
            self._rules.append(ScreeningRule(ScreeningCriteria.PRICE_ABOVE, min_price, "gte"))
        if max_price < float("inf"):
            self._rules.append(ScreeningRule(ScreeningCriteria.PRICE_BELOW, max_price, "lte"))
        return self
    
    def with_min_volume(self, min_volume: float) -> "StockScreeningService":
        """Add minimum volume rule."""
        self._rules.append(ScreeningRule(ScreeningCriteria.VOLUME_ABOVE, min_volume, "gte"))
        return self
    
    def with_pe_range(self, min_pe: float = 0, max_pe: float = float("inf")) -> "StockScreeningService":
        """Add PE ratio range rule."""
        if min_pe > 0:
            self._rules.append(ScreeningRule(ScreeningCriteria.PE_ABOVE, min_pe, "gte"))
        if max_pe < float("inf"):
            self._rules.append(ScreeningRule(ScreeningCriteria.PE_BELOW, max_pe, "lte"))
        return self
    
    def with_industry(self, industry: str) -> "StockScreeningService":
        """Add industry filter rule."""
        self._rules.append(ScreeningRule(ScreeningCriteria.INDUSTRY, industry, "eq"))
        return self
    
    def with_change_pct_range(self, min_pct: float = float("-inf"), max_pct: float = float("inf")) -> "StockScreeningService":
        """Add change percentage range rule."""
        if min_pct > float("-inf"):
            self._rules.append(ScreeningRule(ScreeningCriteria.CHANGE_PCT_ABOVE, min_pct, "gte"))
        if max_pct < float("inf"):
            self._rules.append(ScreeningRule(ScreeningCriteria.CHANGE_PCT_BELOW, max_pct, "lte"))
        return self
    
    def screen(self, stocks: list[dict]) -> list[dict]:
        """Screen stocks based on rules."""
        if not self._rules:
            return stocks
        
        results = []
        for stock in stocks:
            if self._matches_all_rules(stock):
                results.append(stock)
        return results
    
    def _matches_all_rules(self, stock: dict) -> bool:
        """Check if stock matches all rules."""
        for rule in self._rules:
            if not rule.matches(stock):
                return False
        return True
    
    def count_matches(self, stocks: list[dict]) -> int:
        """Count how many stocks match."""
        return len(self.screen(stocks))
    
    def clear_rules(self) -> "StockScreeningService":
        """Clear all rules."""
        self._rules.clear()
        return self
    
    @property
    def rule_count(self) -> int:
        return len(self._rules)


class ScreeningRuleFactory:
    """Factory for creating screening rules."""
    
    @staticmethod
    def price_between(min_price: float, max_price: float) -> list[ScreeningRule]:
        """Create price range rules."""
        rules = []
        if min_price > 0:
            rules.append(ScreeningRule(ScreeningCriteria.PRICE_ABOVE, min_price, "gte"))
        if max_price < float("inf"):
            rules.append(ScreeningRule(ScreeningCriteria.PRICE_BELOW, max_price, "lte"))
        return rules
    
    @staticmethod
    def popular_stocks(min_volume: float = 100000000) -> list[ScreeningRule]:
        """Create popular stocks rules."""
        return [ScreeningRule(ScreeningCriteria.VOLUME_ABOVE, min_volume, "gte")]
    
    @staticmethod
    def value_stocks(max_pe: float = 20) -> list[ScreeningRule]:
        """Create value stocks rules."""
        return [ScreeningRule(ScreeningCriteria.PE_BELOW, max_pe, "lte")]
    
    @staticmethod
    def growth_stocks(min_pe: float = 20, max_pe: float = 50) -> list[ScreeningRule]:
        """Create growth stocks rules."""
        return [
            ScreeningRule(ScreeningCriteria.PE_ABOVE, min_pe, "gte"),
            ScreeningRule(ScreeningCriteria.PE_BELOW, max_pe, "lte"),
        ]


__all__ = [
    "ScreeningCriteria",
    "PriceRange", 
    "ScreeningRule",
    "StockScreeningService",
    "ScreeningRuleFactory",
]