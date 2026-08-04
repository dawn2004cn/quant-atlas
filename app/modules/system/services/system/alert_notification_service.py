from __future__ import annotations

"""Dispatch alert center feed to webhook / DingTalk / email channels."""

from typing import Any

from app.core.runtime_config import get_runtime_int
from app.domain.dto.alert_dispatch_dto import AlertDispatchChannelResultDTO, AlertDispatchResultDTO
from app.domain.dto.alert_dto import AlertEventDTO, AlertLevel
from app.infrastructure.messaging.alert_dispatch_state_store import AlertDispatchStateStore
from app.infrastructure.messaging.alert_notification_adapters import build_default_alert_channels
from app.modules.system.services.system.alert_center_service import AlertCenterService


class AlertNotificationService:
    """Push aggregated alerts to configured outbound channels."""

    _VALID_CHANNELS = frozenset({"webhook", "dingtalk", "email", "wechat"})

    def __init__(
        self,
        *,
        alert_service: AlertCenterService | None = None,
        channels: list[Any] | None = None,
        state_store: AlertDispatchStateStore | None = None,
    ) -> None:
        self._alert_service = alert_service or AlertCenterService()
        self._channels = channels if channels is not None else build_default_alert_channels()
        self._state_store = state_store or AlertDispatchStateStore()

    def dispatch(
        self,
        *,
        min_level: AlertLevel = "warning",
        limit: int = 20,
        channel_names: list[str] | None = None,
        include_system_probes: bool = True,
        respect_dedup: bool = True,
    ) -> AlertDispatchResultDTO:
        feed = self._alert_service.list_alerts(
            limit=limit,
            min_level=min_level,
            include_system_probes=include_system_probes,
        )
        if not feed.items:
            return AlertDispatchResultDTO(
                skipped=True,
                min_level=min_level,
                alert_count=0,
                message="no_alerts_to_dispatch",
            )

        fingerprint = self._fingerprint(feed.items)
        cooldown = get_runtime_int("ALERT_DISPATCH_COOLDOWN_MINUTES", 60)
        if respect_dedup and self._state_store.should_skip(fingerprint, cooldown_minutes=cooldown):
            return AlertDispatchResultDTO(
                skipped=True,
                deduplicated=True,
                fingerprint=fingerprint,
                min_level=min_level,
                alert_count=len(feed.items),
                message="deduplicated_within_cooldown",
            )

        title = f"Quant Atlas 预警 ({len(feed.items)} 条, >= {min_level})"
        body = self._format_body(feed.items)
        selected = {name.strip().lower() for name in (channel_names or []) if name.strip()}
        channel_results: list[AlertDispatchChannelResultDTO] = []
        sent = failed = 0

        for channel in self._channels:
            name = str(getattr(channel, "channel_name", "") or "")
            if selected and name not in selected:
                continue
            if not channel.is_configured():
                channel_results.append(
                    AlertDispatchChannelResultDTO(
                        channel=name,
                        ok=False,
                        skipped=True,
                        reason="not_configured",
                    )
                )
                continue
            ok = bool(channel.send(title=title, body=body, items=feed.items))
            channel_results.append(
                AlertDispatchChannelResultDTO(channel=name, ok=ok, reason="" if ok else "send_failed")
            )
            if ok:
                sent += 1
            else:
                failed += 1

        if not any(not r.skipped for r in channel_results):
            return AlertDispatchResultDTO(
                skipped=True,
                min_level=min_level,
                alert_count=len(feed.items),
                channels=channel_results,
                fingerprint=fingerprint,
                message="no_configured_channels",
            )

        self._record_success(fingerprint, sent)
        return AlertDispatchResultDTO(
            sent=sent,
            failed=failed,
            min_level=min_level,
            alert_count=len(feed.items),
            channels=channel_results,
            fingerprint=fingerprint,
            message="dispatch_completed" if sent else "dispatch_failed",
        )

    def list_channel_status(self) -> list[dict[str, Any]]:
        """Return configured status for each outbound channel (no secrets)."""
        rows: list[dict[str, Any]] = []
        for channel in self._channels:
            name = str(getattr(channel, "channel_name", "") or "")
            configured = False
            try:
                configured = bool(channel.is_configured())
            except Exception:
                configured = False
            rows.append(
                {
                    "channel": name,
                    "configured": configured,
                    "label": {
                        "webhook": "Webhook",
                        "dingtalk": "钉钉",
                        "email": "邮件",
                        "wechat": "微信",
                    }.get(name, name or "unknown"),
                }
            )
        return rows

    @staticmethod
    def _fingerprint(items: list[AlertEventDTO]) -> str:
        return "|".join(sorted(item.id for item in items))

    def _record_success(self, fingerprint: str, sent: int) -> None:
        if sent > 0 and fingerprint:
            self._state_store.record(fingerprint)

    @staticmethod
    def _format_body(items: list[AlertEventDTO]) -> str:
        lines: list[str] = []
        for item in items[:20]:
            ts = item.occurred_at or "-"
            lines.append(f"[{item.level.upper()}][{item.category}] {item.title} ({ts})")
            lines.append(f"  {item.message[:300]}")
            preferred = (item.meta or {}).get("preferred_endpoint")
            action_url = (item.meta or {}).get("action_url")
            if preferred or action_url:
                hint_parts = []
                if preferred:
                    hint_parts.append(f"preferred={preferred}")
                if action_url:
                    hint_parts.append(f"action={action_url}")
                lines.append(f"  → {' · '.join(hint_parts)}")
        if len(items) > 20:
            lines.append(f"... 另有 {len(items) - 20} 条未展示")
        return "\n".join(lines)
