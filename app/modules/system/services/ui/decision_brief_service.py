from __future__ import annotations

"""Convert raw stock DTOs into decision-oriented UI components."""

from typing import Any


class DecisionBriefService:
    """Build semantic components for the stock decision path."""

    def build_brief(
        self,
        *,
        symbol: str,
        market: str,
        stock_detail: dict[str, Any],
        timeline: dict[str, Any] | None = None,
        decision_context: dict[str, Any] | None = None,
        sector_context: dict[str, Any] | None = None,
        supporting_evidence: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        profile = stock_detail.get("profile") or {}
        realtime = profile.get("realtime") if isinstance(profile, dict) else {}
        realtime = realtime or {}
        directives = (decision_context or {}).get("dto_directives") or {}
        role = (decision_context or {}).get("role", "default")
        timeline_payload = timeline or {}
        freshness = stock_detail.get("_quote_freshness") if isinstance(stock_detail.get("_quote_freshness"), dict) else {}
        components = [
            self._quote_component(
                symbol,
                market,
                realtime,
                stock_detail.get("quote_fact") or {},
                freshness=freshness,
            ),
            self._risk_component(stock_detail.get("data_coverage") or {}, role),
            self._sector_component(sector_context),
            self._evidence_component(timeline_payload, directives),
            self._action_component(symbol, market, role),
        ]
        components = [component for component in components if component]
        return {
            "symbol": symbol,
            "market": market,
            "role": role,
            "density": (decision_context or {}).get("response_density", "balanced"),
            "header": {
                "name": realtime.get("name") or stock_detail.get("name") or symbol,
                "price": realtime.get("price"),
                "change_pct": realtime.get("change_pct"),
                "industry": profile.get("industry") or profile.get("sector") if isinstance(profile, dict) else "",
                "chain_name": (sector_context or {}).get("chain_name") or "",
            },
            "timeline_summary": timeline_payload.get("summary")
            or {"count": 0, "by_type": {}, "has_evidence": False},
            "attribution_timeline": timeline_payload,
            "components": components,
            "warnings": self._warnings(stock_detail.get("data_coverage") or {}, timeline_payload),
            "supporting_evidence": supporting_evidence or {},
            "verdict": (supporting_evidence or {}).get("one_line_verdict"),
        }

    @staticmethod
    def _quote_component(
        symbol: str,
        market: str,
        realtime: dict[str, Any],
        quote_fact: dict[str, Any],
        *,
        freshness: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        fresh = freshness or {}
        return {
            "type": "quote_strip",
            "title": "Quote",
            "priority": 1,
            "payload": {
                "symbol": symbol,
                "market": market,
                "price": realtime.get("price"),
                "change_pct": realtime.get("change_pct"),
                "volume": realtime.get("volume"),
                "fact": quote_fact,
                "data_timestamp": fresh.get("data_timestamp") or fresh.get("freshness", {}).get("data_timestamp"),
                "is_realtime": fresh.get("is_realtime", fresh.get("freshness", {}).get("is_realtime")),
                "freshness_level": fresh.get("freshness", {}).get("freshness_level"),
            },
            "trace_ref": quote_fact.get("trace_ref"),
        }

    @staticmethod
    def _sector_component(sector_context: dict[str, Any] | None) -> dict[str, Any] | None:
        ctx = sector_context or {}
        chain = str(ctx.get("chain") or "").strip()
        if not chain and not ctx.get("navigation"):
            return None
        return {
            "type": "sector_drilldown",
            "title": "Industry Chain",
            "priority": 2,
            "payload": {
                "chain": chain,
                "chain_name": ctx.get("chain_name") or chain,
                "nodes": ctx.get("nodes") or {},
                "navigation": ctx.get("navigation") or {},
                "chain_effects": ctx.get("chain_effects") or {},
            },
        }

    @staticmethod
    def _risk_component(data_coverage: dict[str, Any], role: str) -> dict[str, Any]:
        level = data_coverage.get("level") or "unknown"
        return {
            "type": "risk_banner",
            "title": "Data Confidence",
            "priority": 2 if role == "trader" else 4,
            "severity": "warning" if level in {"poor", "unknown"} else "info",
            "payload": {
                "coverage_level": level,
                "coverage_pct": data_coverage.get("coverage_pct"),
                "warning": data_coverage.get("warning"),
                "confidence_penalty": data_coverage.get("confidence_penalty"),
            },
        }

    @staticmethod
    def _evidence_component(
        timeline: dict[str, Any],
        directives: dict[str, Any],
    ) -> dict[str, Any]:
        markers = timeline.get("markers") or []
        include_raw = bool(directives.get("include_raw_factors"))
        highlighted = markers[-8:] if include_raw else markers[-5:]
        return {
            "type": "evidence_timeline",
            "title": "Evidence Timeline",
            "priority": 2,
            "payload": {
                "summary": timeline.get("summary") or {"count": 0, "by_type": {}, "has_evidence": False},
                "markers": highlighted,
                "data_gaps": timeline.get("data_gaps") or [],
            },
        }

    @staticmethod
    def _action_component(symbol: str, market: str, role: str) -> dict[str, Any]:
        actions = [
            {
                "id": "open_timeline",
                "label": "Open Timeline",
                "href": f"/stock/{symbol}?m={market}#attribution-timeline",
            },
            {
                "id": "run_copilot",
                "label": "Stress Strategy",
                "href": f"/strategy?symbol={symbol}&market={market}",
            },
            {
                "id": "adopt_plan",
                "label": "采纳计划",
                "method": "POST",
                "href": "/api/v1/trade-plan/adopt",
                "body": {"symbol": symbol, "market": market, "source": "decision_brief"},
            },
            {
                "id": "create_snapshot",
                "label": "生成决策快照",
                "method": "POST",
                "href": "/api/v1/decision/snapshots",
                "body": {"symbol": symbol, "market": market},
            },
        ]
        if role == "researcher":
            actions.append(
                {
                    "id": "open_reports",
                    "label": "Review Reports",
                    "href": f"/stock/{symbol}?m={market}#research-reports",
                }
            )
        return {
            "type": "action_bar",
            "title": "Next Actions",
            "priority": 3,
            "payload": {"items": actions},
        }

    @staticmethod
    def _warnings(data_coverage: dict[str, Any], timeline: dict[str, Any]) -> list[dict[str, str]]:
        warnings: list[dict[str, str]] = []
        if data_coverage.get("level") in {"poor", "unknown"}:
            warnings.append(
                {
                    "code": "data_coverage_low",
                    "message": data_coverage.get("warning") or "Recent K-line coverage is incomplete.",
                }
            )
        if timeline.get("data_gaps"):
            warnings.append(
                {
                    "code": "timeline_partial",
                    "message": "Some evidence sources were unavailable for this brief.",
                }
            )
        return warnings


__all__ = ["DecisionBriefService"]
