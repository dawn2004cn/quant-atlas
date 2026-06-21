from __future__ import annotations
"""东八区（Asia/Shanghai）时间：业务落库与展示统一为 UTC+8。"""


from datetime import datetime
from zoneinfo import ZoneInfo

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


def now_sh_str(fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """当前上海时区的本地时间字符串。"""
    return datetime.now(SHANGHAI_TZ).strftime(fmt)


def today_sh_str() -> str:
    """当前上海时区的日历日期 YYYY-MM-DD。"""
    return datetime.now(SHANGHAI_TZ).strftime("%Y-%m-%d")
