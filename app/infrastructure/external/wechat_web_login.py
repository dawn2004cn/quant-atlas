from __future__ import annotations
"""微信开放平台网站应用扫码登录（OAuth2 snsapi_login）。

需在开放平台创建「网站应用」并配置授权回调域；环境变量见 ``AppSettings``。
文档：https://developers.weixin.qq.com/doc/oplatform/Website_App/WeChat_Login/Wechat_Login.html
"""


from typing import Any
from urllib.parse import quote, urlencode

import requests

_QRCONNECT = "https://open.weixin.qq.com/connect/qrconnect"
_TOKEN_URL = "https://api.weixin.qq.com/sns/oauth2/access_token"
_USERINFO_URL = "https://api.weixin.qq.com/sns/userinfo"


def build_qrconnect_url(*, app_id: str, redirect_uri: str, state: str) -> str:
    q = urlencode(
        {
            "appid": app_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "snsapi_login",
            "state": state,
        },
        quote_via=quote,
        safe="",
    )
    return f"{_QRCONNECT}?{q}#wechat_redirect"


def exchange_code(app_id: str, app_secret: str, code: str) -> dict[str, Any] | None:
    """用 code 换 access_token；失败返回 None。"""
    params = {
        "appid": app_id,
        "secret": app_secret,
        "code": code,
        "grant_type": "authorization_code",
    }
    try:
        r = requests.get(_TOKEN_URL, params=params, timeout=12)
        data = r.json()
    except Exception:
        return None
    if not isinstance(data, dict) or data.get("errcode"):
        return None
    return data


def fetch_sns_userinfo(access_token: str, openid: str) -> dict[str, Any] | None:
    try:
        r = requests.get(
            _USERINFO_URL,
            params={"access_token": access_token, "openid": openid, "lang": "zh_CN"},
            timeout=12,
        )
        data = r.json()
    except Exception:
        return None
    if not isinstance(data, dict) or data.get("errcode"):
        return None
    return data
