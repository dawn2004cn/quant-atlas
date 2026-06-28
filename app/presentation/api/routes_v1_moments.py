from __future__ import annotations

"""API v1：朋友圈（Moments）信息流与发帖/上传。"""


from flask import Blueprint, request
from flask_login import current_user, login_required

from ...application.errors import ValidationError
from ...core.logger import get_logger
from ...core.registry import register_routes
from .common import ok_response
from .request_parsers import parse_int_param
from .route_deps import SocialRouteDeps, build_social_route_deps, require_moments_service
from .v1_context import ApiV1Context

logger = get_logger(__name__)


@register_routes(name="moments", context="user", description="朋友圈（Moments）信息流与发帖/上传")
def register_moments_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context | None = None,
    *,
    deps: SocialRouteDeps | None = None,
) -> None:
    route_deps = deps or build_social_route_deps(ctx)
    legacy = route_deps.enable_legacy_response_fields
    enable_celery = route_deps.enable_celery
    task_dispatcher = route_deps.task_dispatcher
    task_message_store = route_deps.task_message_store

    def _svc():
        return require_moments_service(route_deps)

    def _moments_viewer_keys() -> list[str]:
        return [
            str(getattr(current_user, "id", "") or ""),
            str(getattr(current_user, "username", "") or ""),
        ]

    @blueprint.get("/moments/feed")
    @login_required
    def feed():
        limit = parse_int_param(request.args.get("limit"), name="limit", default=50, min_value=1)
        before = request.args.get("before_post_id")
        before_id = int(before) if before and str(before).isdigit() else None
        out = _svc().list_feed(limit=limit, before_post_id=before_id)
        out.get("items") or []
        return ok_response(data=out, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/moments")
    @login_required
    def create_post():
        body = request.get_json(silent=True) or {}
        text = str(body.get("content_text") or "")
        attachments = body.get("attachments") or []
        if attachments is not None and not isinstance(attachments, list):
            raise ValidationError("attachments_must_be_list")
        out = _svc().create_post(
            actor_type="user",
            actor_id=str(getattr(current_user, "id", "") or getattr(current_user, "username", "") or "user"),
            author_name=str(getattr(current_user, "username", "") or "用户"),
            content_text=text,
            attachments=attachments if isinstance(attachments, list) else [],
            content=body.get("content") if isinstance(body.get("content"), dict) else None,
            market_date=str(body.get("market_date") or "")[:10] or None,
        )
        return ok_response(data=out, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.patch("/moments/<int:post_id>")
    @login_required
    def patch_post(post_id: int):
        body = request.get_json(silent=True) or {}
        text = str(body.get("content_text") or "")
        attachments = body.get("attachments")
        if attachments is not None and not isinstance(attachments, list):
            raise ValidationError("attachments_must_be_list")
        out = _svc().update_user_post(
            post_id=int(post_id),
            user_keys=_moments_viewer_keys(),
            content_text=text,
            attachments=attachments if isinstance(attachments, list) else None,
        )
        return ok_response(data=out, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.delete("/moments/<int:post_id>")
    @login_required
    def delete_post(post_id: int):
        out = _svc().delete_user_post(post_id=int(post_id), user_keys=_moments_viewer_keys())
        return ok_response(data=out, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/moments/upload")
    @login_required
    def upload():
        f = request.files.get("file")
        out = _svc().save_upload(f)  # type: ignore[arg-type]
        return ok_response(data=out, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/moments/<int:post_id>/like")
    @login_required
    def like(post_id: int):
        uid = str(getattr(current_user, "id", "") or getattr(current_user, "username", "") or "user")
        out = _svc().toggle_like(post_id=int(post_id), user_id=uid)
        return ok_response(data=out, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/moments/<int:post_id>/comments")
    @login_required
    def list_comments(post_id: int):
        limit = parse_int_param(request.args.get("limit"), name="limit", default=50, min_value=1)
        out = _svc().list_comments(post_id=int(post_id), limit=limit)
        return ok_response(data=out, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/moments/<int:post_id>/comments")
    @login_required
    def add_comment(post_id: int):
        body = request.get_json(silent=True) or {}
        text = str(body.get("content_text") or "")
        uid = str(getattr(current_user, "id", "") or getattr(current_user, "username", "") or "user")
        name = str(getattr(current_user, "username", "") or "用户")
        out = _svc().add_comment(post_id=int(post_id), user_id=uid, author_name=name, content_text=text)

        # 若评论的是 Agent 帖子，则异步触发自动回复
        try:
            if enable_celery and out.get("ok"):
                from app.celery_app import celery as _celery
                from app.tasks.moments_agent_reply_tasks import reply_to_agent_comment

                if (
                    _celery is not None
                    and reply_to_agent_comment is not None
                    and hasattr(reply_to_agent_comment, "delay")
                ):
                    _, task_id, enqueued = task_dispatcher.dispatch(
                        reply_to_agent_comment,
                        task_name="app.tasks.moments_agent_reply_tasks.reply_to_agent_comment",
                        args=[int(post_id), uid, name, text],
                        bucket_seconds=30,
                        ttl_seconds=300,
                    )
                    if not enqueued:
                        return ok_response(data=out, legacy_alias_key=None, enable_legacy_alias=legacy)
                    task_message_store.push(
                        event="task_queued",
                        task_id=task_id,
                        task_name="app.tasks.moments_agent_reply_tasks.reply_to_agent_comment",
                        detail=f"Agent 自动回复排队中（post_id={post_id}）",
                        meta={"post_id": int(post_id)},
                    )
        except Exception:
            logger.warning("Agent auto-reply failed for post_id=%s", post_id)
        return ok_response(data=out, legacy_alias_key=None, enable_legacy_alias=legacy)

