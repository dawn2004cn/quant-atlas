"""Phase 40 UX-2 v2: alert notification dispatch channels."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.modules.system.services.system.alert_center_service import AlertCenterService
from app.modules.system.services.system.alert_notification_service import AlertNotificationService
from app.domain.dto.alert_dto import AlertEventDTO
from app.infrastructure.messaging.alert_notification_adapters import (
    DingTalkAlertChannel,
    EmailAlertChannel,
    WebhookAlertChannel,
    WeChatTemplateAlertChannel,
)


class _FakeAlertStore:
    def list_recent(self, *, limit: int = 80) -> list[dict]:
        return [
            {
                "id": "1",
                "ts": "2026-05-23T10:00:00Z",
                "event": "task_failed",
                "task_id": "t-1",
                "task_name": "market_tasks.scheduled_longhu",
                "label": "龙虎榜",
                "detail": "timeout",
                "meta": {},
            }
        ][:limit]


class _OkChannel:
    channel_name = "webhook"

    def __init__(self) -> None:
        self.sent = False

    def is_configured(self) -> bool:
        return True

    def send(self, *, title: str, body: str, items: list[AlertEventDTO]) -> bool:
        self.sent = True
        return True


class _FailChannel:
    channel_name = "dingtalk"

    def is_configured(self) -> bool:
        return True

    def send(self, *, title: str, body: str, items: list[AlertEventDTO]) -> bool:
        return False


def test_dispatch_sends_via_configured_channel() -> None:
    alert_service = AlertCenterService(
        message_store_factory=lambda: _FakeAlertStore(),
        freshness_checker=lambda _table, _minutes=15: True,
    )
    ok_channel = _OkChannel()
    svc = AlertNotificationService(
        alert_service=alert_service,
        channels=[ok_channel, _FailChannel()],
    )
    result = svc.dispatch(min_level="warning", limit=10, include_system_probes=False, respect_dedup=False)
    assert result.alert_count >= 1
    assert result.sent == 1
    assert result.failed == 1
    assert ok_channel.sent is True


def test_dispatch_skips_when_no_alerts() -> None:
    alert_service = AlertCenterService(
        message_store_factory=lambda: _FakeAlertStore(),
        freshness_checker=lambda _table, _minutes=15: True,
    )
    alert_service.list_alerts = MagicMock(  # type: ignore[method-assign]
        return_value=MagicMock(items=[], total=0, counts_by_level={}, counts_by_category={})
    )
    svc = AlertNotificationService(alert_service=alert_service, channels=[_OkChannel()])
    result = svc.dispatch(min_level="critical")
    assert result.skipped is True
    assert result.alert_count == 0


def test_webhook_channel_requires_url() -> None:
    ch = WebhookAlertChannel(url="")
    assert ch.is_configured() is False


def test_dingtalk_channel_requires_url() -> None:
    ch = DingTalkAlertChannel(url="https://example.com/hook")
    assert ch.is_configured() is True


def test_email_channel_requires_smtp_and_recipient() -> None:
    ch = EmailAlertChannel(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="u",
        smtp_password="p",
        mail_from="from@example.com",
        mail_to="ops@example.com",
    )
    assert ch.is_configured() is True


def test_wechat_channel_requires_template_and_openids() -> None:
    ch = WeChatTemplateAlertChannel(
        app_id="wx123",
        app_secret="secret",
        template_id="tpl-1",
        to_openids="",
    )
    assert ch.is_configured() is False
    ch2 = WeChatTemplateAlertChannel(
        app_id="wx123",
        app_secret="secret",
        template_id="tpl-1",
        to_openids="openid-a,openid-b",
    )
    assert ch2.is_configured() is True


def test_wechat_channel_send_uses_template_api(monkeypatch) -> None:
    ch = WeChatTemplateAlertChannel(
        app_id="wx123",
        app_secret="secret",
        template_id="tpl-1",
        to_openids="openid-a",
    )
    monkeypatch.setattr(ch, "_access_token", lambda: "token-abc")
    calls: list[dict] = []

    def _fake_post(
        base_url: str,
        payload: dict,
        *,
        query: dict[str, str] | None = None,
        timeout: int = 10,
    ) -> bool:
        calls.append({"base_url": base_url, "query": query, "payload": payload})
        return True

    monkeypatch.setattr("app.infrastructure.messaging.alert_notification_adapters._post_json", _fake_post)
    ok = ch.send(title="Alert", body="detail", items=[])
    assert ok is True
    assert len(calls) == 1
    assert calls[0]["base_url"].endswith("/message/template/send")
    assert calls[0]["query"] == {"access_token": "token-abc"}
    assert calls[0]["payload"]["template_id"] == "tpl-1"


def test_dispatch_deduplicates_within_cooldown(tmp_path) -> None:
    from pathlib import Path

    from app.infrastructure.messaging.alert_dispatch_state_store import AlertDispatchStateStore

    alert_service = AlertCenterService(
        message_store_factory=lambda: _FakeAlertStore(),
        freshness_checker=lambda _table, _minutes=15: True,
    )
    store = AlertDispatchStateStore(tmp_path / "state.json")
    ok_channel = _OkChannel()
    svc = AlertNotificationService(
        alert_service=alert_service,
        channels=[ok_channel],
        state_store=store,
    )
    first = svc.dispatch(min_level="warning", include_system_probes=False)
    assert first.sent == 1
    second = svc.dispatch(min_level="warning", include_system_probes=False)
    assert second.deduplicated is True
    assert second.skipped is True
