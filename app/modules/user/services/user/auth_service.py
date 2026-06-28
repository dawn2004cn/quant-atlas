"""Authentication service with secure password hashing.

Migrated from unsalted SHA-256 to PBKDF2-HMAC-SHA256 (600k iterations)
via the ``cryptography`` library.  Supports automatic hash upgrade on
login — users created under the old scheme are silently rehashed.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.core.password_hash import get_hash_info, hash_password, needs_rehash
from app.domain.entities import UserAccount

if TYPE_CHECKING:
    from app.domain.ports import UserRepository

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, user_repository: UserRepository):
        self._repo = user_repository

    def authenticate(self, username: str, password: str) -> UserAccount | None:
        user = self._repo.get_by_username(username)
        if not user:
            return None
        if not self._check_password(password, user.password_hash):
            return None
        # Auto-migrate: rehash if the stored hash is weak
        if needs_rehash(user.password_hash):
            self._try_upgrade_password(user, password)
        return user

    @staticmethod
    def _check_password(password: str, stored_hash: str) -> bool:
        from app.core.password_hash import verify_password
        return verify_password(password, stored_hash)

    def _try_upgrade_password(self, user: UserAccount, password: str) -> None:
        """Upgrade a legacy hash to PBKDF2 in-place."""
        new_hash = hash_password(password)
        try:
            self._repo.update(str(user.user_id), {"password": new_hash})
            algo, _ = get_hash_info(
                self._repo.get_by_username(user.username).password_hash
            )
            logger.info("Password hash migrated for user %s: %s -> %s",
                        user.username, "sha256_raw", algo)
        except Exception as exc:
            logger.warning("Failed to migrate password hash for %s: %s", user.username, exc)

    def register(self, username: str, password: str, role: str = "viewer") -> bool:
        """Create a new user with a secure PBKDF2 hash."""
        try:
            user = UserAccount(
                user_id=0,
                username=username,
                role=role,
                password_hash=hash_password(password),
                avatar_url="",
            )
            self._repo.create(user)
            return True
        except ValueError:
            return False


__all__ = ["AuthService"]
