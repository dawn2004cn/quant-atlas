from __future__ import annotations

"""Flask-Login models."""


from flask_login import UserMixin

from ...domain.entities import UserAccount


class SessionUser(UserMixin):
    """Session user."""

    def __init__(self, user_id: int, username: str, role: str, avatar_url: str = ""):
        self.id = str(user_id)
        self.username = username
        self.role = role
        self.avatar_url = (avatar_url or "").strip()

    @property
    def avatar_display_url(self) -> str:
        """有上传头像用 URL，否则用确定性 SVG。"""
        if self.avatar_url:
            return self.avatar_url
        return f"/avatars/user?id={self.id}"

    @property
    def role_name(self) -> str:
        role_names = {
            "admin": "管理员",
            "developer": "开发者",
            "researcher": "研究员",
            "trader": "交易员",
            "viewer": "访客",
        }
        return role_names.get(self.role, self.role)

    def can_manage_users(self) -> bool:
        """Admin or Manager role can manage users.

        Aligned with ``domain.shared.value_objects.UserAccount.can_manage_users()``
        which also recognises ``manager`` as a managing role.
        """
        return self.role in ("admin", "manager")

    def can_run_research_writes(self) -> bool:
        """Qlib 数据写入、RD-Agent 提交等研究型写操作（交易员/访客禁止）。"""
        return self.role in ("admin", "developer", "researcher")

    def may_trigger_server_data_ingestion(self) -> bool:
        """龙虎榜/研报等服务器侧入库与刷新（交易员/访客禁止）。"""
        return self.role in ("admin", "developer", "researcher")

    def may_run_expensive_ai_pipeline(self) -> bool:
        """全量多角色 AI 研究、LLM 模型发现等（交易员/访客禁止）。"""
        return self.role in ("admin", "developer", "researcher")

    @classmethod
    def from_entity(cls, user: UserAccount) -> SessionUser:
        return cls(user.user_id, user.username, user.role, getattr(user, "avatar_url", "") or "")
