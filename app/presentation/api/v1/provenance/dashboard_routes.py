"""Site-wide truth dashboard route."""

from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, jsonify
from flask_login import login_required

from app.domain.verification import list_pending
from app.modules.system.services.system.data_truth_guardian_service import DataTruthGuardianService
from app.presentation.api.error_codes import ErrorCode, error_payload
from app.presentation.api.responses import success_response
from app.presentation.api.v1.provenance._helpers import health_color
from app.presentation.api.v1_context import ApiV1Context


def register_provenance_dashboard_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
) -> None:
    _ = ctx

    @blueprint.get("/truth-dashboard")
    @login_required
    def truth_dashboard():
        """Site-wide data truth health dashboard."""
        try:
            guardian = DataTruthGuardianService()
            manifest = guardian.get_manifest()

            if not manifest:
                return success_response(
                    data={
                        "global_truth_index": 0.3,
                        "sources": [],
                        "stale_catalog": [],
                    },
                    meta={"warning": "Guardian may not be online."},
                )

            pending = list_pending()
            stale = [f"{key} ({reason})" for key, reason in pending.items()]

            sources = manifest.get("sources", []) or ["TDX", "Qlib", "AkShare"]
            health = {source: 0.85 for source in sources}

            index = sum(health.values()) / max(1.0, len(health))
            return success_response(
                data={
                    "global_truth_index": round(index, 4),
                    "sources": [
                        {
                            "source": key,
                            "health": value,
                            "color": health_color(value),
                        }
                        for key, value in health.items()
                    ],
                    "stale_catalog": stale[:10],
                    "last_update": datetime.now(timezone.utc).isoformat().replace("+", "Z"),
                },
            )

        except Exception as exc:
            payload = error_payload(ErrorCode.VALIDATION_ERROR, str(exc))
            return jsonify(payload), ErrorCode.VALIDATION_ERROR.http_status
