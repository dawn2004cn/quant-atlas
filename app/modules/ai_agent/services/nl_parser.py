from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Advanced Natural Language Understanding for Jarvis."""


import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any


from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TimeRange:
    """Parsed time range."""
    start: datetime | None
    end: datetime | None
    description: str


@dataclass
class FactorCondition:
    """Factor condition for stock screening."""
    factor_name: str
    operator: str  # ">", "<", ">=", "<=", "=="
    value: float
    logical: str = "AND"  # "AND", "OR"


@dataclass
class NLQuery:
    """Parsed natural language query."""
    intent: str
    factors: list[FactorCondition] = None
    time_range: TimeRange | None = None
    sort_by: str = ""
    limit: int = 20
    metadata: dict[str, Any] = None


class AdvancedNLParser:
    """Advanced NLP parser for complex stock queries."""

    # Factor synonyms mapping
    FACTOR_SYNONYMS = {
        "roe": ["ROE", "净资产收益率", "return on equity"],
        "roa": ["ROA", "资产收益率"],
        "pe": ["市盈率", "PE", "估值"],
        "pb": ["PB", "市净率"],
        "gross_margin": ["毛利率", "gross margin"],
        "revenue_growth": ["营收增长", "revenue growth", "收入增长"],
        "profit_growth": ["净利润增长", "profit growth"],
        "dividend_yield": ["股息", "dividend", "分红"],
        "market_cap": ["市值", "market cap"],
        "volume": ["成交量", "volume"],
        "turnover": ["换手率", "turnover"],
    }

    # Operator mappings
    OPERATOR_MAP = {
        "超过": ">",
        "高于": ">",
        "大于": ">",
        "不超过": "<",
        "低于": "<",
        "小于": "<",
        "在...之间": "between",
        "等于": "==",
        "约为": "==",
    }

    # Trend patterns
    TREND_PATTERNS = {
        "上涨趋势": {"trend": "up", "period": 20},
        "下跌趋势": {"trend": "down", "period": 20},
        "突破": {"pattern": "breakout"},
        "均线多头": {"ma": "golden_cross"},
    }

    # Time patterns
    TIME_PATTERNS = {
        r"过去(\d+)天": lambda m: TimeRange(
            start=datetime.now() - timedelta(days=int(m.group(1))),
            end=datetime.now(),
            description=f"过去{m.group(1)}天"
        ),
        r"过去(\d+)周": lambda m: TimeRange(
            start=datetime.now() - timedelta(weeks=int(m.group(1))),
            end=datetime.now(),
            description=f"过去{m.group(1)}周"
        ),
        r"过去(\d+)个月": lambda m: TimeRange(
            start=datetime.now() - timedelta(days=int(m.group(1)) * 30),
            end=datetime.now(),
            description=f"过去{m.group(1)}个月"
        ),
        r"过去(\d+)年": lambda m: TimeRange(
            start=datetime.now() - timedelta(days=int(m.group(1)) * 365),
            end=datetime.now(),
            description=f"过去{m.group(1)}年"
        ),
        r"上周": lambda m: TimeRange(
            start=datetime.now() - timedelta(days=7),
            end=datetime.now(),
            description="上周"
        ),
        r"上月": lambda m: TimeRange(
            start=datetime.now() - timedelta(days=30),
            end=datetime.now(),
            description="上月"
        ),
        r"今年": lambda m: TimeRange(
            start=datetime.now().replace(month=1, day=1),
            end=datetime.now(),
            description="今年"
        ),
    }

    def parse(self, query: str) -> NLQuery:
        """Parse complex natural language query."""
        query = query.strip()

        # Initialize result
        result = NLQuery(
            intent="screen",
            factors=[],
            time_range=None,
            metadata={"original": query}
        )

        # Extract time range
        result.time_range = self._extract_time_range(query)

        # Extract factor conditions
        result.factors = self._extract_factors(query)

        # Extract sort order
        result.sort_by = self._extract_sort(query)

        # Extract limit
        result.limit = self._extract_limit(query)

        # Detect special patterns
        self._detect_patterns(query, result)

        return result

    def _extract_time_range(self, query: str) -> TimeRange | None:
        """Extract time range from query."""
        for pattern, extractor in self.TIME_PATTERNS.items():
            match = re.search(pattern, query)
            if match:
                return extractor(match)
        return None

    def _extract_factors(self, query: str) -> list[FactorCondition]:
        """Extract factor conditions from query."""
        factors = []

        # Find all factor mentions
        for factor_key, synonyms in self.FACTOR_SYNONYMS.items():
            for synonym in synonyms:
                if synonym in query:
                    # Find operator and value near this factor
                    condition = self._extract_operator_and_value(query, synonym)
                    if condition:
                        factors.append(FactorCondition(
                            factor_name=factor_key,
                            **condition
                        ))

        return factors

    def _extract_operator_and_value(
        self,
        query: str,
        factor: str
    ) -> dict | None:
        """Extract operator and value for a factor."""
        # Find position of factor in query
        pos = query.find(factor)
        if pos == -1:
            return None

        # Look for operator and value after factor
        after = query[pos:]

        # Check for operators
        for op_text, operator in self.OPERATOR_MAP.items():
            if op_text in after:
                # Extract value after operator
                value_match = re.search(r"(\d+\.?\d*)", after.split(op_text)[1][:20])
                if value_match:
                    return {
                        "operator": operator,
                        "value": float(value_match.group(1)),
                        "logical": "AND"
                    }

        return None

    def _extract_sort(self, query: str) -> str:
        """Extract sort order from query."""
        sort_map = {
            "涨跌幅": "change_pct",
            "涨幅": "change_pct",
            "跌幅": "change_pct",
            "市值": "market_cap",
            "成交量": "volume",
            "换手率": "turnover",
            "roe": "roe",
            "pe": "pe",
        }

        for key, field in sort_map.items():
            if key in query:
                if "跌幅" in query:
                    return f"-{field}"
                return field

        return ""

    def _extract_limit(self, query: str) -> int:
        """Extract result limit."""
        # Pattern like "前10只", "前20只", "显示20个"
        match = re.search(r"前?(\d+)[只个]", query)
        if match:
            return int(match.group(1))

        return 20  # Default

    def _detect_patterns(self, query: str, result: NLQuery) -> None:
        """Detect special patterns like trend, patterns."""
        for pattern_name, pattern_config in self.TREND_PATTERNS.items():
            if pattern_name in query:
                if result.metadata is None:
                    result.metadata = {}
                result.metadata["patterns"] = result.metadata.get("patterns", [])
                result.metadata["patterns"].append(pattern_config)


def convert_to_screening_criteria(nl_query: NLQuery) -> GenericResponseDTO:
    """Convert parsed NL query to screening criteria."""
    criteria = {
        "conditions": [],
        "time_range": None,
        "sort_by": "",
        "limit": 20
    }

    # Convert factors
    for factor in nl_query.factors:
        criteria["conditions"].append({
            factor.factor_name: {
                "operator": factor.operator,
                "value": factor.value
            }
        })

    # Convert time range
    if nl_query.time_range:
        criteria["time_range"] = {
            "start": nl_query.time_range.start.isoformat() if nl_query.time_range.start else None,
            "end": nl_query.time_range.end.isoformat() if nl_query.time_range.end else None
        }

    # Convert sort
    if nl_query.sort_by:
        criteria["sort_by"] = nl_query.sort_by

    criteria["limit"] = nl_query.limit

    return criteria


# Example usage
EXAMPLE_QUERIES = [
    "给我看看过去一年里，ROE 超过 15% 且处于上涨趋势的股票",
    "过去6个月涨幅超过20%的股票有哪些",
    "找市盈率低于15且股息率大于3%的股票",
    "过去一个月成交量放大的股票",
    "显示ROE最高的10只股票",
]


__all__ = [
    "TimeRange",
    "FactorCondition",
    "NLQuery",
    "AdvancedNLParser",
    "convert_to_screening_criteria"
]
