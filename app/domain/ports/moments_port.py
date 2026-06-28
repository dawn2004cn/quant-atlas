from __future__ import annotations

"""Port for social moments feed persistence."""

from abc import ABC, abstractmethod
from typing import Any


class MomentsRepository(ABC):
    """Contract for moments posts, attachments and likes."""

    @abstractmethod
    def create_post(
        self,
        *,
        actor_type: str,
        actor_id: str,
        author_name: str,
        content_text: str,
        content: dict[str, Any] | None = None,
        market_date: str | None = None,
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    def add_attachment(
        self,
        *,
        post_id: int,
        media_type: str,
        file_name: str,
        file_path: str,
        file_url: str,
        mime_type: str | None,
        size_bytes: int,
        meta: dict[str, Any] | None = None,
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    def list_feed(self, *, limit: int = 50, before_post_id: int | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def toggle_like(self, *, post_id: int, user_id: str) -> dict[str, Any]:
        raise NotImplementedError
