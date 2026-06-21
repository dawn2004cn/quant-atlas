"""LLM provider configuration routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ValidationError
from app.presentation.api.common import ok_resource, require_expensive_ai_role
from app.presentation.api.v1.quant_ai.runtime import QuantAiRuntime
from app.presentation.api.v1_context import ApiV1Context


def register_quant_ai_llm_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: QuantAiRuntime,
) -> None:
    _ = ctx
    legacy = runtime.legacy

    @blueprint.get("/llm/providers")
    @login_required
    def llm_providers():
        from app.modules.system.services.config.llm_user_config import list_public_providers

        return ok_resource(
            resource={"providers": list_public_providers()},
            resource_key="llm_providers",
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/llm/models")
    @login_required
    def llm_models_refresh():
        require_expensive_ai_role()
        from app.modules.system.services.config.llm_user_config import fetch_models_for_user

        body = request.get_json(silent=True) or {}
        provider = (body.get("provider") or "").strip()
        api_key = body.get("api_key")
        if api_key is not None and not isinstance(api_key, str):
            raise ValidationError("api_key must be a string")
        api_key_s = (api_key or "").strip()
        base_url = body.get("base_url")
        base_opt = (str(base_url).strip() if base_url else None) or None
        if not provider:
            raise ValidationError("provider is required")
        models = fetch_models_for_user(provider, api_key_s, base_url=base_opt)
        return ok_resource(
            resource={"models": models},
            resource_key="llm_models",
            enable_legacy_alias=legacy,
        )
