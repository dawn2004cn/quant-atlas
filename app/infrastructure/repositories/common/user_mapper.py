from __future__ import annotations
"""Map persistence user rows/models to domain ``UserAccount``."""

from app.domain.entities import UserAccount


def user_row_to_account(
    *,
    user_id: int,
    username: str,
    role: str,
    password_hash: str,
    avatar_url: str | None = None,
) -> UserAccount:
    return UserAccount(
        user_id=int(user_id),
        username=str(username),
        role=str(role),
        password_hash=str(password_hash),
        avatar_url=str(avatar_url or ""),
    )
