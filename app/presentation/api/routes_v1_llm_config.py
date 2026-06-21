"""API v1: LLM config management routes (CRUD for user LLM settings)."""

from __future__ import annotations

from flask import Blueprint, request

from ...application.errors import ValidationError
from ...core.middleware.request_context import require_authenticated_user_id
from ...core.registry import register_routes
from ...presentation.api.common import ok_resource, ok_response
from ...presentation.api.route_deps import AiRouteDeps
from ...presentation.api.v1_context import ApiV1Context
from ...presentation.api.decorators import require_role


@register_routes(name="llm_config", context="ai_agent", description="User LLM config management endpoints")
def register_llm_config_routes(blueprint, ctx: ApiV1Context | None = None, *, deps: AiRouteDeps | None = None) -> None:
    blueprint.name = "llm_config"

    def _uid() -> int:
        return require_authenticated_user_id()

    def _service():
        try:
            from flask import current_app
            registry = current_app.extensions.get("service_registry")
            if registry is not None:
                service = registry.get_or_none("llm_provider_service")
                if service is not None:
                    return service
        except Exception:
            logger.warning("Suppressed exception", exc_info=True)
            pass
        from app.modules.system.services.llm_provider_service import LlmProviderService
        from app.config import get_settings
        from app.core.key_encryption import KeyEncryptionService
        from app.infrastructure.database.orm import create_db_engine, create_session_factory, mysql_engine_kwargs
        from app.infrastructure.repositories.llm_config_repository import SqlAlchemyUserLlmConfigRepository
        settings = get_settings()
        engine = create_db_engine(settings.database_uri, **mysql_engine_kwargs())
        session = create_session_factory(engine)()
        kms = KeyEncryptionService()
        repo = SqlAlchemyUserLlmConfigRepository(session, key_encryption=kms)
        return LlmProviderService(repo, key_encryption=kms)

    @blueprint.get("/list")
    def list_configs():
        """List all LLM configs for the current user."""
        user_id = _uid()
        configs = _service().get_user_configs(user_id)
        return ok_resource(resource={"configs": configs}, resource_key="llm_configs")

    @blueprint.get("/defaults")
    def get_defaults():
        """Get system-wide default LLM config."""
        from app.application.services.llm_provider_service import _PROVIDER_DEFAULTS

        return ok_resource(
            resource={"defaults": _PROVIDER_DEFAULTS},
            resource_key="llm_defaults",
        )

    @blueprint.post("/save")
    @require_role("can_manage_users")
    def save_config():
        """Save/update a user LLM config."""
        user_id = _uid()
        body = request.get_json(silent=True) or {}

        provider = (body.get("provider") or "default").strip()
        model_name = (body.get("model_name") or "").strip()
        if not model_name:
            raise ValidationError("model_name is required")

        base_url = (body.get("base_url") or "").strip() or None
        api_key = (body.get("api_key") or "").strip()
        if not api_key:
            raise ValidationError("api_key is required")

        temperature = float(body.get("temperature", 0.2))
        max_tokens = int(body.get("max_tokens", 4096))
        timeout_sec = int(body.get("timeout_sec", 120))
        model_alias = (body.get("model_alias") or "").strip() or None
        fallback_chain = body.get("fallback_chain")
        if not isinstance(fallback_chain, list):
            fallback_chain = None

        _service().save_user_config(
            user_id=user_id,
            provider=provider,
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_sec=timeout_sec,
            model_alias=model_alias,
            fallback_chain=fallback_chain,
        )
        return ok_response(data={"ok": True, "provider": provider, "message": "Config saved"})

    @blueprint.delete("/<provider>")
    @require_role("can_manage_users")
    def delete_config(provider):
        """Delete a user LLM config by provider."""
        user_id = _uid()

        _service().delete_user_config(user_id, provider)
        return ok_response(data={"ok": True, "provider": provider, "message": "Config deleted"})
