from __future__ import annotations

"""角色代码与内置演示账号（与 SQLite ``roles`` / 种子用户一致）。"""


# 五类角色；各对应一个内置演示账号，禁止删除
ROLE_CODES: tuple[str, ...] = ("admin", "developer", "researcher", "trader", "viewer")
PROTECTED_DEMO_USERNAMES: frozenset[str] = frozenset(ROLE_CODES)

ROLE_LABELS: dict[str, str] = {
    "admin": "管理员",
    "developer": "开发者",
    "researcher": "研究员",
    "trader": "交易员",
    "viewer": "访客",
}
