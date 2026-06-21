"""Billing status API — Stripe placeholder for Beta (Phase E)."""

from __future__ import annotations

from flask import Blueprint
from flask_login import current_user, login_required

from app.core.registry import register_routes
from app.domain.billing.retail_billing import build_billing_status
from app.presentation.api.common import ok_response
from app.presentation.api.v1_context import ApiV1Context


@register_routes(name="billing", context="user", description="Retail billing placeholder")
def register_billing_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    _ = ctx
    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/billing/status")
    @login_required
    def billing_status():
        return ok_response(
            data=build_billing_status(current_user),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
