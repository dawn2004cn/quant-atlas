"""Data Verification API — Phase 15/16 truth badge endpoint + Guardian evidence chain.
GET /api/v1/data/verify/<market>/<symbol> — returns quorum consensus evidence for UI."""

from __future__ import annotations

from flask import Blueprint
from flask_login import login_required

from app.core.logger import get_logger
from app.core.registry import register_routes
from app.domain.data_truth.byzantine_consensus import SourceQuote, compute_quorum_consensus
from app.modules.system.services.system.data_truth_guardian_service import DataTruthGuardianService
from app.presentation.api.responses import success_response

logger = get_logger(__name__)
blueprint = Blueprint("data_verify", __name__, url_prefix="/data/verify")


@blueprint.get("/<market>/<symbol>")
@login_required
def data_verify(market: str, symbol: str):
    """Verify data authenticity for a symbol.
    Returns Guardian quorum consensus evidence suitable for UI truth badge rendering.
    """
    try:
        guardian = DataTruthGuardianService()
        manifest = guardian.get_manifest()
        manifest.get("sources", ["TDX", "Qlib", "AkShare"])
        threshold = float(manifest.get("diff_threshold_pct", 0.5))
        quotes: list[SourceQuote] = []

        sentry = guardian._sentry
        if sentry and hasattr(sentry, "check_symbol"):
            published = sentry.check_symbol(symbol.upper(), market.upper())
            # Build quotes from deviation events
            for evt in published:
                value_a = getattr(evt, "value_a", None)
                value_b = getattr(evt, "value_b", None)
                if value_a is not None and float(value_a) > 0:
                    quotes.append(SourceQuote(
                        source=getattr(evt, "source_a", "source_a"),
                        value=float(value_a),
                        trade_date="",
                    ))
                if value_b is not None and float(value_b) > 0:
                    quotes.append(SourceQuote(
                        source=getattr(evt, "source_b", "source_b"),
                        value=float(value_b),
                        trade_date="",
                    ))

        result = compute_quorum_consensus(
            symbol=symbol.upper(),
            quotes=quotes,
            threshold_pct=threshold,
        )

        trust_level = "verified"
        if result.byzantine_fault:
            trust_level = "partial"
        if result.confidence < 0.5:
            trust_level = "disputed"

        return success_response(
            data={
                "symbol": symbol,
                "market": market,
                "trust_level": trust_level,
                "confidence": round(result.confidence, 4),
                "evidence": result.evidence,
                "consensus_value": result.consensus_value,
                "sources": [
                    {
                        "source": d["source"],
                        "value": d["value"],
                        "diff_pct": round(d["diff_pct"], 2),
                        "trade_date": d.get("trade_date", ""),
                    }
                    for d in result.source_deviations
                ],
                "agreeing_sources": result.agreeing_sources,
                "outlier_sources": result.outlier_sources,
            },
        )
    except Exception as exc:
        logger.warning("Data verify for %s/%s failed: %s", market, symbol, exc)
        return success_response(
            data={
                "symbol": symbol,
                "market": market,
                "trust_level": "unverified",
                "confidence": 0.0,
                "evidence": f"Verification unavailable: {exc}",
                "sources": [],
                "consensus_value": None,
            },
        )


@register_routes(name="data_verify", context="data", description="Truth Badge verification evidence")
def register_data_verify_routes(bp, ctx):
    bp.register_blueprint(blueprint)
