from __future__ import annotations

"""Webhook / DingTalk / SMTP / WeChat template adapters for alert dispatch."""

import json
import logging
import smtplib
import time
from email.message import EmailMessage
from typing import Any
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

from app.core.runtime_config import get_runtime
from app.domain.dto.alert_dto import AlertEventDTO

logger = logging.getLogger(__name__)

_WECHAT_TOKEN_CACHE: dict[str, Any] = {"token": "", "expires_at": 0.0}


def _post_json(
    base_url: str,
    payload: dict[str, Any],
    *,
    query: dict[str, str] | None = None,
    timeout: int = 10,
) -> bool:
    url = base_url
    if query:
        url = f"{base_url}?{urlparse.urlencode(query)}"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urlrequest.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return 200 <= int(resp.status) < 300
    except (urlerror.URLError, TimeoutError, ValueError) as exc:
        logger.warning("alert notification POST failed [%s]: %s", base_url, exc)
        return False


def _get_json(
    base_url: str,
    *,
    query: dict[str, str] | None = None,
    timeout: int = 10,
) -> dict[str, Any]:
    url = base_url
    if query:
        url = f"{base_url}?{urlparse.urlencode(query)}"
    try:
        with urlrequest.urlopen(url, timeout=timeout) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
    except (urlerror.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("alert notification GET failed [%s]: %s", base_url, exc)
        return {}


class WebhookAlertChannel:
    channel_name = "webhook"

    def __init__(self, url: str | None = None) -> None:
        self._url = (url if url is not None else get_runtime("ALERT_WEBHOOK_URL", "") or "").strip()

    def is_configured(self) -> bool:
        return bool(self._url)

    def send(self, *, title: str, body: str, items: list[AlertEventDTO]) -> bool:
        payload = {
            "title": title,
            "text": body,
            "alerts": [item.model_dump(mode="json") for item in items],
        }
        return _post_json(self._url, payload)


class DingTalkAlertChannel:
    channel_name = "dingtalk"

    def __init__(self, url: str | None = None) -> None:
        self._url = (url if url is not None else get_runtime("DINGTALK_WEBHOOK_URL", "") or "").strip()

    def is_configured(self) -> bool:
        return bool(self._url)

    def send(self, *, title: str, body: str, items: list[AlertEventDTO]) -> bool:
        content = f"{title}\n\n{body}"[:4000]
        return _post_json(self._url, {"msgtype": "text", "text": {"content": content}})


class EmailAlertChannel:
    channel_name = "email"

    def __init__(
        self,
        *,
        smtp_host: str | None = None,
        smtp_port: int | None = None,
        smtp_user: str | None = None,
        smtp_password: str | None = None,
        mail_from: str | None = None,
        mail_to: str | None = None,
    ) -> None:
        self._host = (smtp_host if smtp_host is not None else get_runtime("SMTP_HOST", "") or "").strip()
        self._port = smtp_port if smtp_port is not None else int(get_runtime("SMTP_PORT", "587") or "587")
        self._user = (smtp_user if smtp_user is not None else get_runtime("SMTP_USER", "") or "").strip()
        self._password = smtp_password if smtp_password is not None else get_runtime("SMTP_PASSWORD", "") or ""
        self._mail_from = (mail_from if mail_from is not None else get_runtime("SMTP_FROM", "") or self._user).strip()
        self._mail_to = (mail_to if mail_to is not None else get_runtime("ALERT_EMAIL_TO", "") or "").strip()

    def is_configured(self) -> bool:
        return bool(self._host and self._mail_to and self._mail_from)

    def send(self, *, title: str, body: str, items: list[AlertEventDTO]) -> bool:
        msg = EmailMessage()
        msg["Subject"] = title[:200]
        msg["From"] = self._mail_from
        msg["To"] = self._mail_to
        msg.set_content(body[:8000])
        try:
            with smtplib.SMTP(self._host, self._port, timeout=10) as smtp:
                smtp.starttls()
                if self._user:
                    smtp.login(self._user, self._password)
                smtp.send_message(msg)
            return True
        except (OSError, smtplib.SMTPException) as exc:
            logger.warning("alert email send failed: %s", exc)
            return False


class WeChatTemplateAlertChannel:
    """WeChat Official Account template message channel."""

    channel_name = "wechat"

    def __init__(
        self,
        *,
        app_id: str | None = None,
        app_secret: str | None = None,
        template_id: str | None = None,
        to_openids: str | None = None,
    ) -> None:
        self._app_id = (app_id if app_id is not None else get_runtime("WECHAT_ALERT_APP_ID", "") or "").strip()
        self._app_secret = (
            app_secret if app_secret is not None else get_runtime("WECHAT_ALERT_APP_SECRET", "") or ""
        ).strip()
        self._template_id = (
            template_id if template_id is not None else get_runtime("WECHAT_ALERT_TEMPLATE_ID", "") or ""
        ).strip()
        raw_openids = to_openids if to_openids is not None else get_runtime("WECHAT_ALERT_TO_OPENIDS", "") or ""
        self._openids = [x.strip() for x in raw_openids.split(",") if x.strip()]

    def is_configured(self) -> bool:
        return bool(self._app_id and self._app_secret and self._template_id and self._openids)

    def send(self, *, title: str, body: str, items: list[AlertEventDTO]) -> bool:
        token = self._access_token()
        if not token:
            return False
        top_level = items[0].level.upper() if items else "INFO"
        template_data = {
            "first": {"value": title[:100]},
            "keyword1": {"value": str(len(items))},
            "keyword2": {"value": top_level},
            "remark": {"value": body[:200]},
        }
        ok_any = False
        for openid in self._openids:
            payload = {
                "touser": openid,
                "template_id": self._template_id,
                "data": template_data,
            }
            if _post_json(
                "https://api.weixin.qq.com/cgi-bin/message/template/send",
                payload,
                query={"access_token": token},
            ):
                ok_any = True
            else:
                logger.warning("wechat template send failed for openid=%s", openid[:8])
        return ok_any

    def _access_token(self) -> str:
        global _WECHAT_TOKEN_CACHE
        now = time.time()
        cached = str(_WECHAT_TOKEN_CACHE.get("token") or "")
        expires_at = float(_WECHAT_TOKEN_CACHE.get("expires_at") or 0)
        if cached and now < expires_at - 60:
            return cached
        data = _get_json(
            "https://api.weixin.qq.com/cgi-bin/token",
            query={
                "grant_type": "client_credential",
                "appid": self._app_id,
                "secret": self._app_secret,
            },
        )
        token = str(data.get("access_token") or "")
        if not token:
            logger.warning("wechat access_token fetch failed: %s", data.get("errmsg", data))
            return ""
        ttl = int(data.get("expires_in") or 7200)
        _WECHAT_TOKEN_CACHE = {"token": token, "expires_at": now + ttl}
        return token


def build_default_alert_channels() -> list[Any]:
    return [
        WebhookAlertChannel(),
        DingTalkAlertChannel(),
        EmailAlertChannel(),
        WeChatTemplateAlertChannel(),
    ]
