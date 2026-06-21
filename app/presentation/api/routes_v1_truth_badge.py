"""Data Truth Badge API — Guardian verification evidence for UI truth cards."""
from __future__ import annotations

from typing import Any

from flask import Blueprint
from flask_login import login_required

from app.core.logger import get_logger
from app.core.registry import register_routes
from app.domain.data_truth.byzantine_consensus import SourceQuote, compute_quorum_consensus
from app.modules.system.services.system.data_truth_guardian_service import DataTruthGuardianService
from app.presentation.api.responses import success_response

logger = get_logger(__name__)
blueprint = Blueprint("truth_badge", __name__, url_prefix="/truth")


def _build_quorum(symbol: str, market: str) -> dict[str, Any] | None:
    """Build quorum consensus using Guardian service infrastructure."""
    try:
        guardian = DataTruthGuardianService()
        manifest = guardian.get_manifest()
        sources = manifest.get("sources", ["TDX", "Qlib", "AkShare"])
        threshold = float(manifest.get("diff_threshold_pct", 0.5))

        quotes: list[SourceQuote] = []
        # Collect quotes from Guardian"s sentry scan
        sentry = guardian._sentry
        if sentry and hasattr(sentry, "scan"):
            scan_result = sentry.scan(symbol, market)
            src_data = scan_result.get("sources", {})
            for src_name in sources:
                src_entry = src_data.get(src_name, {})
                value = src_entry.get("close", src_entry.get("price", 0.0))
                if value and float(value) > 0:
                    quotes.append(SourceQuote(
                        source=src_name,
                        value=float(value),
                        trade_date=str(src_entry.get("trade_date", "")),
                    ))

        if not quotes:
            return None

        result = compute_quorum_consensus(
            symbol=symbol,
            quotes=quotes,
            threshold_pct=threshold,
        )

        trust_level = "verified"
        if result.byzantine_fault:
            trust_level = "partial"
        if result.confidence < 0.5:
            trust_level = "disputed"

        return {
            "symbol": symbol,
            "market": market,
            "trust_level": trust_level,
            "confidence": round(result.confidence, 4),
            "evidence": result.evidence,
            "consensus_value": result.consensus_value,
            "sources": [
                {"source": d["source"], "value": d["value"],
                 "diff_pct": round(d["diff_pct"], 2), "trade_date": d.get("trade_date", "")}
                for d in result.source_deviations
            ],
            "agreeing_sources": result.agreeing_sources,
            "outlier_sources": result.outlier_sources,
        }
    except Exception as exc:
        logger.debug("truth badge quorum for %s: %s", symbol, exc)
        return None


@blueprint.route("/badge/<market>/<symbol>")
@login_required
def truth_badge(market: str, symbol: str):
    """Return Guardian verification evidence for a symbol truth badge."""
    data = _build_quorum(symbol.upper(), market.upper())
    if data is None:
        data = {
            "symbol": symbol, "market": market,
            "trust_level": "unverified", "confidence": 0.0,
            "evidence": "未有足够数据源进行验证",
            "sources": [], "consensus_value": None,
        }
    return success_response(data=data)


@blueprint.route("/droplet/<market>/<symbol>")
@login_required
def truth_droplet(market: str, symbol: str):
    """Health-droplet data for the TruthDroplet frontend component."""
    data = _build_quorum(symbol.upper(), market.upper())
    if data is None:
        return success_response(
            data={
                "health": 0,
                "sources": "无数据",
                "verified_count": 0,
                "total_count": 0,
            },
        )
    total = len(data.get("sources", [])) or 1
    verified = len(data.get("agreeing_sources", []))
    health = round((verified / total) * 90 + (data.get("confidence", 0) * 10), 1)
    return success_response(
        data={
            "health": health,
            "sources": f"{verified}/{total}",
            "verified_count": verified,
            "total_count": total,
            "trust_level": data.get("trust_level", "unverified"),
        },
    )


@register_routes(name="truth_badge", context="data", description="Data Truth Badge UI endpoint")
def register_truth_badge_routes(bp, ctx):
    bp.register_blueprint(blueprint)
