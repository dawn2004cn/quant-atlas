from __future__ import annotations
"""Team research moments feed — publish evidence chains and logic challenges."""

import json
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


class TeamResearchChannelService:
    """Team-scoped research feed built on Moments."""

    def __init__(self, *, moments_service: Any) -> None:
        self._moments = moments_service

    def list_feed(self, team_id: int, *, limit: int = 40) -> dict[str, Any]:
        raw = self._moments.list_feed(limit=min(limit * 4, 200))
        items = raw.get("items") or []
        team_items = [row for row in items if self._team_id_of(row) == team_id]
        return {
            "ok": True,
            "team_id": team_id,
            "items": team_items[:limit],
            "count": len(team_items[:limit]),
        }

    def publish_research(
        self,
        *,
        team_id: int,
        user_id: int,
        author_name: str,
        content_text: str,
        provenance_id: str | None = None,
        symbol: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        content = {
            "team_id": team_id,
            "channel": "research",
            "post_type": "evidence_chain",
            "provenance_id": provenance_id,
            "symbol": symbol,
        }
        prefix = f"[团队#{team_id}] "
        text = prefix + (content_text or "").strip()
        if not text.strip(prefix):
            text = prefix + f"发布证据链 {provenance_id or symbol or ''}".strip()
        return self._moments.create_post(
            actor_type="user",
            actor_id=str(user_id),
            author_name=author_name,
            content_text=text,
            content=content,
            attachments=attachments,
        )

    def logic_challenge(
        self,
        *,
        post_id: int,
        user_id: int,
        author_name: str,
        challenge_text: str,
    ) -> dict[str, Any]:
        text = (challenge_text or "").strip()
        if not text:
            return {"ok": False, "error": "challenge_text_required"}
        body = f"🧩 逻辑挑战: {text}"
        return self._moments.add_comment(
            post_id=post_id,
            user_id=str(user_id),
            author_name=author_name,
            content_text=body,
        )

    @staticmethod
    def _team_id_of(row: dict[str, Any]) -> int | None:
        raw = row.get("content_json") or row.get("content") or {}
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                return None
        if not isinstance(raw, dict):
            return None
        tid = raw.get("team_id")
        return int(tid) if tid is not None else None
