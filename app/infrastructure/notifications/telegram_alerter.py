"""Telegram (or env-based) alerter for Risk Guard events."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from app.core.logger import get_logger
from app.domain.trading.risk_guard import RiskGuardDecision

logger = get_logger(__name__)


class TelegramAlerter:
    """Send Risk Guard alerts via Telegram Bot API when configured.

    Env: ``TELEGRAM_BOT_TOKEN``, ``TELEGRAM_CHAT_ID``.
    When unset, ``send`` logs and returns False (no raise).
    """

    def __init__(
        self,
        *,
        bot_token: str | None = None,
        chat_id: str | None = None,
        timeout_sec: float = 5.0,
    ) -> None:
        self._bot_token = (bot_token if bot_token is not None else os.getenv("TELEGRAM_BOT_TOKEN", "")).strip()
        self._chat_id = (chat_id if chat_id is not None else os.getenv("TELEGRAM_CHAT_ID", "")).strip()
        self._timeout_sec = timeout_sec

    @property
    def configured(self) -> bool:
        return bool(self._bot_token and self._chat_id)

    def send_risk_guard_alert(self, account_id: str, decision: RiskGuardDecision) -> bool:
        text = (
            f"[QuantAtlas RiskGuard]\n"
            f"account={account_id}\n"
            f"action={decision.action}\n"
            f"reason={decision.reason}"
        )
        return self.send(text)

    def send(self, text: str) -> bool:
        if not self.configured:
            logger.info("telegram_alerter skipped (not configured): %s", text[:200])
            return False
        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        payload: dict[str, Any] = {"chat_id": self._chat_id, "text": text}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout_sec) as resp:  # noqa: S310
                ok = 200 <= getattr(resp, "status", 200) < 300
                if not ok:
                    logger.warning("telegram_alerter non-2xx status")
                return ok
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            logger.warning("telegram_alerter failed: %s", exc)
            return False


def make_risk_guard_telegram_callback() -> Any:
    """Return ``(account_id, decision) -> None`` suitable for LoggingRiskGuardActions."""
    alerter = TelegramAlerter()

    def _cb(account_id: str, decision: RiskGuardDecision) -> None:
        alerter.send_risk_guard_alert(account_id, decision)

    return _cb
