"""Scoring and enrichment logic for recommendation — Phase C split.

Extracted from recommendation_service.py to separate scoring / business-logic concerns.
"""

from __future__ import annotations

from typing import Any


from app.core.logger import get_logger

logger = get_logger(__name__)


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


class RecommendationScoringService:
    """Scoring, core logic, verdict and industry-chain enrichment."""

    @staticmethod
    def score(
        row: dict[str, Any],
        evidence: dict[str, Any],
        agent_cal: dict[str, Any] | None = None,
    ) -> float:
        """Compute composite score from base safety score, trust and agent boost."""
        base = _safe_float(row.get("safety_score") or row.get("score"), 50)
        trust = _safe_float((evidence.get("trust") or {}).get("score"), 50)
        composite = base * 0.65 + trust * 0.35
        boost = _safe_float((agent_cal or {}).get("boost"), 0.0)
        return round(composite + boost, 2)

    @staticmethod
    def core_logic(row: dict[str, Any], evidence: dict[str, Any]) -> list[str]:
        """Extract core logic bullets from signals and trust reasons."""
        logic = []
        signals = row.get("signal_strategies") or row.get("buy_signals") or []
        if signals:
            names = []
            for item in signals[:3]:
                if isinstance(item, dict):
                    names.append(str(item.get("name") or item.get("id") or item))
                else:
                    names.append(str(item))
            logic.append(", ".join(names))

        change = _safe_float(row.get("change_pct"))
        if change:
            logic.append(f"?{change:+.2f}%")
        for reason in (evidence.get("trust") or {}).get("reasons", [])[:2]:
            logic.append(str(reason))
        return logic[:4] or [""]

    @staticmethod
    def one_line_verdict(
        row: dict[str, Any],
        core_logic: list[str],
        evidence: dict[str, Any],
    ) -> str:
        """Generate a one-line verdict string."""
        name = str(row.get("name") or row.get("code") or "")
        change = _safe_float(row.get("change_pct"))
        trust = (evidence.get("trust") or {}).get("level") or "medium"
        hook = core_logic[0] if core_logic else ""
        if change:
            return f"{name}{hook}{change:+.2f}%{trust}"
        return f"{name}{hook} {trust}"

    @staticmethod
    def industry_position(row: dict[str, Any]) -> dict[str, str]:
        """Resolve industry-chain positioning for a stock row."""
        industry = str(row.get("industry") or "")
        chain_name = industry
        upstream_hint = ""
        downstream_hint = ""
        try:
            from app.modules.market_data.services.industry_chain_map_service import (
                INDUSTRY_CHAIN_CONFIG,
                IndustryChainAnalyzer,
            )

            matched_key = None
            for key, cfg in INDUSTRY_CHAIN_CONFIG.items():
                name = str(cfg.get("name") or "")
                if industry == key or industry == name or key in industry or industry in key:
                    matched_key = key
                    break

            if matched_key:
                cfg = INDUSTRY_CHAIN_CONFIG[matched_key]
                chain_name = str(cfg.get("name") or matched_key)
                up = IndustryChainAnalyzer.get_upstream(matched_key)[:3]
                down = IndustryChainAnalyzer.get_downstream(matched_key)[:3]
                upstream_hint = ", ".join(up) if up else ""
                downstream_hint = ", ".join(down) if down else ""
        except Exception as exc:
            logger.debug("recommendation industry chain map: %s", exc)

        return {
            "industry": industry,
            "chain_name": chain_name,
            "position": f" {upstream_hint} -> {chain_name} -> {downstream_hint}",
            "opportunity": f" {chain_name} ecosystem",
            "linkage": f"{upstream_hint or ''}  {downstream_hint or ''}",
        }
