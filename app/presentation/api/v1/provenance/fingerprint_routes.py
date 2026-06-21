"""Provenance fingerprint card route."""

from __future__ import annotations

from flask import Blueprint, jsonify
from flask_login import login_required

from app.core.logger import get_logger
from app.core.mesh.memory_fabric import MemoryFabric as MemoryFabricService
from app.domain.data_truth.byzantine_consensus import SourceQuote, compute_quorum_consensus
from app.modules.system.services.system.data_truth_guardian_service import DataTruthGuardianService
from app.presentation.api.error_codes import ErrorCode, error_payload
from app.presentation.api.responses import success_response
from app.presentation.api.v1.provenance.models import ProvenanceFingerprint
from app.presentation.api.v1_context import ApiV1Context

logger = get_logger(__name__)


def register_provenance_fingerprint_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
) -> None:
    _ = ctx

    @blueprint.get("/fingerprint/<market>/<symbol>/<tradedate>")
    @login_required
    def provenance_fingerprint(market: str, symbol: str, tradedate: str):
        """3D data fingerprint card."""
        guardian = DataTruthGuardianService()
        memory_fabric = MemoryFabricService()

        try:
            sentry = guardian._sentry
            source_deviation = None

            if sentry and hasattr(sentry, "check_symbol"):
                published = sentry.check_symbol(symbol.upper(), market.upper())
                quotes = []
                for evt in published:
                    value_a = getattr(evt, "value_a", None)
                    value_b = getattr(evt, "value_b", None)
                    if value_a is not None and float(value_a) > 0:
                        quotes.append(
                            SourceQuote(
                                source=getattr(evt, "source_a", "source_a"),
                                value=float(value_a),
                            )
                        )
                    if value_b is not None and float(value_b) > 0:
                        quotes.append(
                            SourceQuote(
                                source=getattr(evt, "source_b", "source_b"),
                                value=float(value_b),
                            )
                        )
                if quotes:
                    result = compute_quorum_consensus(symbol=symbol.upper(), quotes=quotes)
                    source_deviation = {
                        "sources": {d["source"]: d["value"] for d in result.source_deviations},
                        "consensus_value": result.consensus_value,
                        "confidence": result.confidence,
                        "evidence": result.evidence,
                    }

            fab_notes = []
            try:
                entries = memory_fabric.find_entries(
                    query=f"point:{symbol}+{market}+trdate:{tradedate}",
                    limit=2,
                )
                if entries:
                    fab_notes = [
                        {
                            "agent": getattr(n, "meta", {}).get("agent_name", "unknown"),
                            "note": getattr(n, "note", ""),
                            "strength": getattr(n, "meta", {}).get("strength", "weak"),
                            "timestamp": getattr(n, "timestamp", ""),
                        }
                        for n in (entries if isinstance(entries, list) else [entries])
                    ]
            except Exception as exc:
                logger.debug("Memory fabric lookup skipped: %s", exc)

            rust_metrics = {
                "nanoseconds": 50000.0,
                "bytes_processed": 800.0,
            }

            confidence = 0.5
            if source_deviation:
                confidence = source_deviation.get("confidence", 0.5)

            card = ProvenanceFingerprint(
                symbol=symbol,
                market=market,
                trade_date=tradedate,
                point_label="close",
                guardian=source_deviation or {"error": "scan_failed"},
                rust_core_metrics=rust_metrics,
                memory_fabric_notes=fab_notes,
                confidence_score=round(confidence, 4),
            )
            return success_response(data=card.__dict__)

        except Exception as exc:
            payload = error_payload(ErrorCode.VALIDATION_ERROR, str(exc))
            return jsonify(payload), ErrorCode.VALIDATION_ERROR.http_status
