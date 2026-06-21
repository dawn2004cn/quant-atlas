"""Compliance pivot routes (reputation, ZK proof, disclosure)."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.presentation.api.responses import success_response
from app.presentation.api.v1.optimization.runtime import get_compliance_service
from app.presentation.api.v1_context import ApiV1Context


def register_optimization_compliance_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
) -> None:
    _ = ctx

    @blueprint.get("/compliance/reputation")
    @login_required
    def compliance_reputation():
        svc = get_compliance_service()
        account = svc.get_reputation(current_user.id)
        return success_response(data=account.__dict__)

    @blueprint.post("/compliance/reward")
    @login_required
    def compliance_reward():
        data = request.get_json(silent=True) or {}
        points = float(data.get("points", 0))
        reason = str(data.get("reason", "contribution"))
        svc = get_compliance_service()
        account = svc.reward_contribution(current_user.id, points, reason)
        return success_response(data=account.__dict__)

    @blueprint.post("/compliance/spend")
    @login_required
    def compliance_spend():
        data = request.get_json(silent=True) or {}
        cost = float(data.get("cost", 0))
        reason = str(data.get("reason", "access"))
        svc = get_compliance_service()
        success = svc.spend_reputation(current_user.id, cost, reason)
        return success_response(data={"spent": success, "accepted": success})

    @blueprint.get("/compliance/leaderboard")
    @login_required
    def compliance_leaderboard():
        svc = get_compliance_service()
        board = svc.get_leaderboard()
        return success_response(data=board)

    @blueprint.post("/compliance/zk-proof")
    @login_required
    def compliance_zk_proof():
        data = request.get_json(silent=True) or {}
        svc = get_compliance_service()
        proof = svc.create_proof(
            factor_id=str(data.get("factor_id", "")),
            owner_id=current_user.id,
            ic_mean=float(data.get("ic_mean", 0)),
            ic_std=float(data.get("ic_std", 0)),
            sharpe=float(data.get("sharpe", 0)),
            sample_size=int(data.get("sample_size", 0)),
        )
        payload = proof.public_dict()
        payload["verification_nonce"] = proof.verification_nonce
        return success_response(data=payload)

    @blueprint.post("/compliance/zk-proof/verify")
    @login_required
    def compliance_zk_proof_verify():
        data = request.get_json(silent=True) or {}
        svc = get_compliance_service()
        factor_id = str(data.get("factor_id", ""))
        owner_id = int(data.get("owner_id", current_user.id))
        nonce = str(data.get("verification_nonce") or data.get("nonce") or "")
        if nonce:
            valid = svc.verify_proof(factor_id, owner_id, nonce)
        else:
            valid = svc.verify_stored_proof(factor_id, owner_id) if owner_id == current_user.id else False
        return success_response(data={"valid": valid, "factor_id": factor_id})

    @blueprint.post("/compliance/disclosure")
    @login_required
    def compliance_disclosure():
        data = request.get_json(silent=True) or {}
        svc = get_compliance_service()
        disclosure = svc.get_disclosure(
            factor_id=str(data.get("factor_id", "")),
            viewer_id=current_user.id,
            level=str(data.get("level", "low")),
        )
        return success_response(data=disclosure.__dict__)
