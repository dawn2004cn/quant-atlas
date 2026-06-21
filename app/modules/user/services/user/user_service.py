from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.domain.entities import UserAccount
from app.domain.ports import UserRepository
from app.domain.role_catalog import PROTECTED_DEMO_USERNAMES

if TYPE_CHECKING:
    from app.modules.user.services.user.auth_service import AuthService


class UserApplicationService:
    def __init__(self, repository: UserRepository, auth_service: AuthService | None = None):
        self._repository = repository
        self._auth_service = auth_service

    def register_public(self, username: str, password: str) -> tuple[bool, str]:
        value = (username or "").strip()
        if len(value) < 2:
            return False, "用户名至少 2 个字符"
        if value.lower() in {name.lower() for name in PROTECTED_DEMO_USERNAMES}:
            return False, "该用户名受保护，不能开放注册"
        if not re.match(r"^[A-Za-z0-9_一-鿿-]+$", value):
            return False, "用户名只能包含字母、数字、中文、下划线或短横线"
        if len(password or "") < 6:
            return False, "密码至少 6 个字符"
        try:
            if hasattr(self._repository, "create_user"):
                self._repository.create_user(value, password, "viewer")
            else:
                self._repository.create(UserAccount(user_id=0, username=value, role="viewer", password_hash=""))
            return True, "注册成功，请登录"
        except ValueError:
            return False, "用户名已存在"
        except Exception as exc:
            return False, f"注册失败：{exc}"

    def change_password(
        self,
        *,
        target_username: str,
        old_password: str | None,
        new_password: str,
        confirm_password: str | None,
        current_username: str | None = None,
        current_role: str = "viewer",
    ) -> tuple[bool, str]:
        """Change password for a user.

        Admin users can change any user's password (old_password may be empty).
        Regular users must provide the correct old password.
        """
        new_password = (new_password or "").strip()
        old_password = old_password or ""
        confirm_password = confirm_password or ""

        # Validate new password strength
        if len(new_password) < 8:
            return False, "新密码至少 8 个字符"
        if new_password != confirm_password:
            return False, "两次输入的密码不一致"

        # Admin can bypass old password check
        if current_role != "admin":
            # Verify old password via AuthService
            if not self._auth_service:
                return False, "认证服务未配置"
            user = self._auth_service.authenticate(target_username, old_password)
            if not user:
                return False, "原密码不正确"

        # Update password hash
        try:
            from app.core.password_hash import hash_password
            new_hash = hash_password(new_password)
            update_method = getattr(self._repository, "update", None)
            if callable(update_method):
                uid_method = getattr(self._repository, "get_by_username", None)
                existing = uid_method(target_username) if uid_method else None
                if existing:
                    update_method(str(existing.user_id), {"password": new_hash})
                else:
                    return False, "用户不存在"
            else:
                return False, "当前用户仓库不支持密码修改"

            return True, "密码已更新"
        except Exception as exc:
            return False, f"密码修改失败：{exc}"

    def provision_wechat_user(self, openid: str, *, nickname: str | None = None) -> UserAccount | None:
        method = getattr(self._repository, "link_or_create_wechat_user", None)
        if callable(method):
            return method(openid, nickname=nickname)
        return None

    def provision_oauth_user(
        self,
        oauth_sub: str,
        *,
        display_name: str | None = None,
    ) -> UserAccount | None:
        method = getattr(self._repository, "link_or_create_oauth_user", None)
        if callable(method):
            return method(oauth_sub, display_name=display_name)
        return None

    def set_user_role(self, username: str, role: str, *, actor_role: str) -> tuple[bool, str]:
        actor = getattr(self._repository, "get_by_username", None)
        if callable(actor):
            current = actor(username)
            if current is None:
                return False, "用户不存在"
        if actor_role != "admin":
            return False, "仅管理员可以调整用户角色"
        method = getattr(self._repository, "update_user_role", None)
        if not callable(method):
            return False, "当前用户仓库不支持角色调整"
        return bool(method(username, role)), "角色已更新"


__all__ = ["UserApplicationService"]
