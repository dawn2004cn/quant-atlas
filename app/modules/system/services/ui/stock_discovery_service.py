from __future__ import annotations

"""Intent-aware stock discovery built on top of the existing stock search."""

from dataclasses import dataclass
from typing import Any

from app.domain.enums import MarketCode


@dataclass(frozen=True)
class DiscoveryTag:
    key: str
    label: str
    kind: str
    aliases: tuple[str, ...]


DISCOVERY_TAGS: tuple[DiscoveryTag, ...] = (
    DiscoveryTag("power", "power", "industry", ("power", "electric", "utility", "dianli", "电力")),
    DiscoveryTag("bank", "bank", "industry", ("bank", "银行")),
    DiscoveryTag("semiconductor", "semiconductor", "industry", ("semiconductor", "chip", "半导体", "芯片")),
    DiscoveryTag("new_energy", "new energy", "industry", ("new energy", "新能源", "光伏", "锂电")),
    DiscoveryTag("limit_up", "limit up", "event", ("limit up", "涨停", "封板")),
    DiscoveryTag("volume_spike", "volume spike", "event", ("volume spike", "放量", "大单", "异动")),
    DiscoveryTag("low_pb", "low P/B", "factor", ("low p/b", "low pb", "pb<1", "破净", "低p/b", "低pb")),
    DiscoveryTag("blue_chip", "blue chip", "style", ("blue chip", "蓝筹", "白马")),
    DiscoveryTag("breakdown", "breakdown", "technical", ("breakdown", "破位", "跌破")),
)


class StockDiscoveryService:
    """Parse fuzzy discovery intent, delegate exact lookup, then annotate results."""

    def __init__(self, stock_service: Any) -> None:
        self._stock_service = stock_service

    def discover(
        self,
        query: str,
        *,
        tags: list[str] | None = None,
        market: MarketCode = MarketCode.CN,
        limit: int = 20,
        strict: bool = False,
    ) -> dict[str, Any]:
        parsed = self.parse_intent(query, tags=tags)
        delegate_queries = self._delegate_queries(parsed)
        rows = self._search(delegate_queries, market=market, limit=limit)
        annotated = [self._annotate(row, parsed["filters"]) for row in rows]
        if strict and parsed["filters"]:
            annotated = [row for row in annotated if row.get("matched_tags")]

        return {
            "stocks": annotated[:limit],
            "discovery": {
                "query": query,
                "intent": parsed["intent"],
                "filters": parsed["filters"],
                "residual_query": parsed["residual_query"],
                "strict": strict,
                "suggestions": self._suggestions(parsed),
            },
        }

    @staticmethod
    def parse_intent(query: str, *, tags: list[str] | None = None) -> dict[str, Any]:
        raw = (query or "").strip()
        haystack = raw.lower()
        matched: list[dict[str, str]] = []
        residual = raw

        explicit_tags = [str(tag).strip() for tag in tags or [] if str(tag).strip()]
        explicit_haystack = " ".join(explicit_tags).lower()

        for tag in DISCOVERY_TAGS:
            aliases = sorted(tag.aliases, key=len, reverse=True)
            if any(alias.lower() in haystack or alias.lower() in explicit_haystack for alias in aliases):
                matched.append({"key": tag.key, "label": tag.label, "kind": tag.kind})
                for alias in aliases:
                    residual = residual.replace(alias, " ")

        residual_terms = [term for term in residual.replace("+", " ").replace(",", " ").split() if term]
        return {
            "intent": "discovery" if matched else "lookup",
            "filters": matched,
            "residual_query": " ".join(residual_terms).strip(),
        }

    def _delegate_queries(self, parsed: dict[str, Any]) -> list[str]:
        residual = parsed.get("residual_query") or ""
        if residual:
            return [residual]
        queries: list[str] = []
        for item in parsed.get("filters") or []:
            label = item.get("label")
            if label:
                queries.append(label)
        return queries

    def _search(self, queries: list[str], *, market: MarketCode, limit: int) -> list[dict[str, Any]]:
        seen: set[str] = set()
        rows: list[dict[str, Any]] = []
        for query in queries:
            if not query:
                continue
            found = self._stock_service.search_stocks(query, limit=limit, market=market)
            for item in found or []:
                row = self._to_dict(item)
                key = str(row.get("symbol") or row.get("code") or row.get("ts_code") or row)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(row)
                if len(rows) >= limit:
                    return rows
        return rows

    @staticmethod
    def _to_dict(item: Any) -> dict[str, Any]:
        if isinstance(item, dict):
            return dict(item)
        if hasattr(item, "model_dump"):
            return item.model_dump()
        if hasattr(item, "dict"):
            return item.dict()
        return dict(getattr(item, "__dict__", {}) or {})

    def _annotate(self, row: dict[str, Any], filters: list[dict[str, str]]) -> dict[str, Any]:
        matched: list[str] = []
        reasons: list[str] = []
        searchable = self._searchable_text(row)
        for tag in filters:
            key = tag["key"]
            if self._row_matches_tag(row, searchable, key):
                matched.append(key)
                reasons.append(f"matched {tag['label']}")
        enriched = dict(row)
        enriched["matched_tags"] = matched
        enriched["rank_reasons"] = reasons
        return enriched

    @staticmethod
    def _searchable_text(row: dict[str, Any]) -> str:
        parts: list[str] = []
        for key in ("symbol", "code", "name", "industry", "sector", "market", "tags"):
            value = row.get(key)
            if isinstance(value, list):
                parts.extend(str(x) for x in value)
            elif value is not None:
                parts.append(str(value))
        return " ".join(parts).lower()

    @staticmethod
    def _row_matches_tag(row: dict[str, Any], searchable: str, key: str) -> bool:
        if key == "low_pb":
            pb = row.get("pb") or row.get("pb_ratio") or row.get("price_to_book")
            try:
                return float(pb) < 1
            except (TypeError, ValueError):
                return any(token in searchable for token in ("low pb", "破净", "低pb"))
        aliases = next((tag.aliases for tag in DISCOVERY_TAGS if tag.key == key), ())
        return any(alias.lower() in searchable for alias in aliases)

    @staticmethod
    def _suggestions(parsed: dict[str, Any]) -> list[str]:
        if parsed.get("filters"):
            return ["try strict=1 to hide weak matches", "add an industry or factor tag to narrow results"]
        return ["try tags like power, limit_up, low_pb", "combine terms with +, for example power+low_pb"]


__all__ = ["StockDiscoveryService", "DISCOVERY_TAGS"]
