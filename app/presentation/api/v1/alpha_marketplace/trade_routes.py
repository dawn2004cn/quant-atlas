"""Alpha marketplace listing and order routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.application.errors import ValidationError
from app.presentation.api.common import ok_collection, ok_resource, ok_response
from app.presentation.api.v1.alpha_marketplace._helpers import get_marketplace_service
from app.presentation.api.v1_context import ApiV1Context


def register_alpha_marketplace_trade_routes(
    bp: Blueprint,
    ctx: ApiV1Context,
    *,
    legacy: bool,
) -> None:
    _ = ctx

    @bp.get("/alpha/marketplace/listings")
    @login_required
    def marketplace_listings():
        svc = get_marketplace_service()
        active = request.args.get("active", "true").lower() == "true"
        return ok_collection(
            items=svc.list_listings(active_only=active),
            item_key="listing",
            enable_legacy_alias=legacy,
        )

    @bp.post("/alpha/marketplace/list")
    @login_required
    def marketplace_list():
        svc = get_marketplace_service()
        body = request.get_json(silent=True) or {}
        token_id = (body.get("token_id") or "").strip()
        seller_id = body.get("seller_id") or current_user.id
        price = float(body.get("reputation_cost") or body.get("price") or 0)
        if not token_id or price <= 0:
            raise ValidationError("token_id and reputation_cost > 0 required")
        listing = svc.list_token(
            token_id=token_id,
            seller_id=int(seller_id),
            price_tokens=price,
            signal_count=int(body.get("signal_count", 100)),
        )
        return ok_resource(
            resource={
                "listing_id": listing.listing_id,
                "token_id": listing.token_id,
                "reputation_cost": listing.reputation_cost,
                "price": listing.reputation_cost,
                "diversity_bonus": listing.diversity_bonus,
            },
            resource_key="listing",
            enable_legacy_alias=legacy,
        )

    @bp.post("/alpha/marketplace/contribute")
    @login_required
    def marketplace_contribute():
        svc = get_marketplace_service()
        body = request.get_json(silent=True) or {}
        listing_id = (body.get("listing_id") or "").strip()
        contributor_id = body.get("contributor_id") or body.get("buyer_id") or current_user.id
        if not listing_id:
            raise ValidationError("listing_id_required")
        order = svc.contribute(listing_id=listing_id, contributor_id=int(contributor_id))
        return ok_resource(
            resource={
                "order_id": order.order_id,
                "status": order.status,
                "reputation_spent": order.reputation_spent,
            },
            resource_key="order",
            enable_legacy_alias=legacy,
        )

    @bp.post("/alpha/marketplace/buy")
    @login_required
    def marketplace_buy():
        return marketplace_contribute()

    @bp.get("/alpha/marketplace/orders")
    @login_required
    def marketplace_orders():
        svc = get_marketplace_service()
        buyer_id = request.args.get("buyer_id") or current_user.id
        return ok_response(
            data={"orders": svc.list_orders(buyer_id=int(buyer_id))},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @bp.post("/alpha/marketplace/deliver/<order_id>")
    @login_required
    def marketplace_deliver(order_id: str):
        svc = get_marketplace_service()
        body = request.get_json(silent=True) or {}
        signals = body.get("signals", [])
        if not signals:
            raise ValidationError("signals_required")
        if svc.deliver_signals(order_id=order_id, signals=signals):
            return ok_resource(
                resource={"order_id": order_id, "status": "delivered"},
                resource_key="delivery",
                enable_legacy_alias=legacy,
            )
        raise ValidationError("delivery_failed")

    @bp.get("/alpha/marketplace/disclosure/<token_id>")
    @login_required
    def marketplace_disclosure(token_id: str):
        svc = get_marketplace_service()
        level = request.args.get("level", "low")
        disclosure = svc.get_disclosure(token_id, current_user.id, level)
        return ok_resource(resource=disclosure, resource_key="disclosure", enable_legacy_alias=legacy)

    @bp.post("/alpha/marketplace/order/<order_id>/cancel")
    @login_required
    def marketplace_cancel(order_id: str):
        svc = get_marketplace_service()
        user_id = int(
            request.args.get("user_id")
            or (request.get_json(silent=True) or {}).get("user_id")
            or current_user.id
        )
        svc.cancel_order(order_id=order_id, user_id=user_id)
        return ok_resource(
            resource={"order_id": order_id, "status": "cancelled"},
            resource_key="order",
            enable_legacy_alias=legacy,
        )
