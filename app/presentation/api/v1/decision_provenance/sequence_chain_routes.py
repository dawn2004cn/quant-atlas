"""Sequence chain provenance routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ValidationError
from app.presentation.api.common import ok_response, require_ctx_service
from app.presentation.api.v1.decision_provenance.runtime import DecisionProvenanceRuntime
from app.presentation.api.v1_context import ApiV1Context


def register_sequence_chain_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: DecisionProvenanceRuntime,
) -> None:
    legacy = runtime.legacy

    @blueprint.get("/system/sequence-chain")
    @login_required
    def sequence_chain_list():
        """List provenance chains (evidence → consensus → trade lineage)."""
        svc = require_ctx_service(ctx, "sequence_chain_service")
        symbol = (request.args.get("symbol") or "").strip() or None
        visibility = (request.args.get("visibility") or "").strip() or None
        team_id_raw = request.args.get("team_id")
        team_id: int | None = None
        if team_id_raw:
            try:
                team_id = int(team_id_raw)
            except ValueError:
                raise ValidationError("invalid_team_id") from None
        limit_raw = request.args.get("limit")
        try:
            limit = min(max(int(limit_raw), 1), 100) if limit_raw else 30
        except ValueError:
            limit = 30
        chains = svc.list_chains(
            symbol=symbol,
            team_id=team_id,
            visibility=visibility,
            limit=limit,
        )
        return ok_response(
            data=chains,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/system/sequence-chain/<provenance_id>")
    @login_required
    def sequence_chain_detail(provenance_id: str):
        """Fetch one provenance chain by id."""
        svc = require_ctx_service(ctx, "sequence_chain_service")
        chain = svc.get_chain(provenance_id)
        if chain is None:
            raise ValidationError("provenance_not_found", details={"provenance_id": provenance_id})
        return ok_response(data=chain.model_dump(), legacy_alias_key=None, enable_legacy_alias=legacy)
