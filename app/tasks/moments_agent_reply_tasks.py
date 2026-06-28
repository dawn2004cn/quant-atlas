from __future__ import annotations

"""朋友圈：Agent 评论自动回复（像对话）"""


from typing import Any

from ..celery_app import celery as _celery
from ..config import get_settings
from ..core.logger import get_logger
from ..infrastructure.repositories.deps import create_moments_repository
from .task_wiring import generate_ollama_text

logger = get_logger(__name__)


def _moments_repository() -> Any:
    return create_moments_repository(get_settings())


def _build_prompt(*, role: str, post_text: str, user_comment: str) -> str:
    return (
        "你是量化交易平台的研究助手（朋友圈内Analyst）。\n"
        f"你的角色：{role}\n"
        "请像在朋友圈评论区对话一样回复，要求：\n"
        "- 用中文\n"
        "- 不要超过 120 字\n"
        "- 给出 1-2 条可执行建议或风险提示\n"
        "- 不要编造数据；仅基于帖子内容与用户评论\n\n"
        f"【帖子】\n{post_text}\n\n"
        f"【用户评论】\n{user_comment}\n\n"
        "【你的回复】\n"
    )


if _celery is not None:

    @_celery.task(name="app.tasks.moments_agent_reply_tasks.reply_to_agent_comment")
    def reply_to_agent_comment(post_id: int, user_id: str, user_name: str, comment_text: str) -> dict[str, Any]:
        # 避免自我循环：agent 自己的评论不触发回复
        if str(user_id).startswith("agent:"):
            return {"ok": True, "skipped": True, "reason": "agent_comment"}

        repo = _moments_repository()
        post = repo.get_post(int(post_id))
        if not post:
            return {"ok": True, "skipped": True, "reason": "post_not_found"}
        if str(post.get("actor_type") or "") != "agent":
            return {"ok": True, "skipped": True, "reason": "not_agent_post"}

        role = str(post.get("actor_id") or "Agent")
        post_text = str(post.get("content_text") or "")[:2000]
        prompt = _build_prompt(role=role, post_text=post_text, user_comment=str(comment_text or "")[:800])
        out = generate_ollama_text(prompt=prompt)
        reply = str(out.get("text") or "").strip()
        if not reply:
            return {"ok": True, "skipped": True, "reason": "empty_reply"}

        agent_uid = f"agent:{role}"
        agent_name = f"Agent·{role}"
        c = repo.add_comment(
            post_id=int(post_id),
            user_id=agent_uid,
            author_name=agent_name,
            content_text=reply,
        )
        return {"ok": True, "posted": bool(c.get("ok")), "post_id": int(post_id), "role": role}

else:
    reply_to_agent_comment = None  # type: ignore[misc, assignment]
