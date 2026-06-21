"""Alpha marketplace reputation, proof and legacy wallet routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.application.errors import ValidationError
from app.presentation.api.common import ok_resource, ok_response
from app.presentation.api.v1.alpha_marketplace._helpers import get_compliance_service
from app.presentation.api.v1_context import ApiV1Context


def register_alpha_marketplace_reputation_routes(
    bp: Blueprint,
    ctx: ApiV1Context,
    *,
    legacy: bool,
) -> None:
    _ = ctx

    @bp.post("/alpha/marketplace/proof/verify")
    @login_required
    def marketplace_proof_verify():
        body = request.get_json(silent=True) or {}
        factor_id = str(body.get("token_id") or body.get("factor_id") or "").strip()
        owner_id = int(body.get("owner_id", current_user.id))
        nonce = str(body.get("verification_nonce") or body.get("nonce") or "")
        if not factor_id:
            raise ValidationError("token_id required")
        compliance = get_compliance_service()
        if nonce:
            valid = compliance.verify_proof(factor_id, owner_id, nonce)
        elif owner_id == current_user.id:
            valid = compliance.verify_stored_proof(factor_id, owner_id)
        else:
            valid = False
        proof = compliance.get_proof(factor_id, owner_id)
        return ok_response(
            data={
                "valid": valid,
                "proof_hash": proof.proof_hash if proof else "",
                "ic_mean": proof.ic_mean if proof else None,
                "sharpe": proof.sharpe if proof else None,
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @bp.get("/alpha/reputation/balance")
    @login_required
    def reputation_balance():
        account = get_compliance_service().get_reputation(current_user.id)
        return ok_resource(
            resource={
                "user_id": account.user_id,
                "reputation_score": account.reputation_score,
                "contribution_count": account.contribution_count,
            },
            resource_key="reputation",
            enable_legacy_alias=legacy,
        )

    @bp.get("/alpha/reputation/leaderboard")
    @login_required
    def reputation_leaderboard():
        board = get_compliance_service().get_leaderboard()
        return ok_response(data={"leaderboard": board}, legacy_alias_key=None, enable_legacy_alias=legacy)

    @bp.get("/alpha/wallet/balance")
    @login_required
    def wallet_balance():
        account = get_compliance_service().get_reputation(
            int(request.args.get("user_id", current_user.id))
        )
        return ok_resource(
            resource={"user_id": account.user_id, "balance": account.reputation_score},
            resource_key="wallet",
            enable_legacy_alias=legacy,
        )

    @bp.post("/alpha/wallet/credit")
    @login_required
    def wallet_credit():
        body = request.get_json(silent=True) or {}
        user_id = int(body.get("user_id", current_user.id))
        amount = float(body.get("amount", 0))
        if amount <= 0:
            raise ValidationError("amount must be positive")
        account = get_compliance_service().reward_contribution(user_id, amount, "legacy_wallet_credit")
        return ok_resource(
            resource={"user_id": user_id, "balance": account.reputation_score},
            resource_key="wallet",
            enable_legacy_alias=legacy,
        )
