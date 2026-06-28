from __future__ import annotations

"""Read user notification preferences for retail psychology pushes."""

import json
import logging
from pathlib import Path
from typing import Any

from app.modules.user.services.user.user_lifecycle_service import DEFAULT_NOTIFICATION_PREFS

logger = logging.getLogger(__name__)



class _UserIdOnly:
    """Minimal user stand-in for lifecycle service."""

    def __init__(self, user_id: int) -> None:
        self.id = int(user_id)


def _read_psychology_pref_from_store(user_id: int) -> bool | None:
    """Fallback for Celery workers without wired lifecycle service."""
    path = Path("instance/user_lifecycle.json")
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return None
        row = raw.get(str(int(user_id))) or {}
        notifications = dict(DEFAULT_NOTIFICATION_PREFS)
        notifications.update(row.get("notifications") or {})
        if "psychology_alerts" not in (row.get("notifications") or {}):
            return None
        return bool(notifications.get("psychology_alerts", True))
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        return None


def psychology_alerts_enabled(
    user_id: int,
    *,
    lifecycle_service: Any | None = None,
    user: Any | None = None,
) -> bool:
    """Return False when user opted out of psychology_guardian message center pushes."""
    if lifecycle_service is not None:
        subject = user if user is not None else _UserIdOnly(user_id)
        try:
            settings = lifecycle_service.get_settings(user=subject)
            notifications = (settings or {}).get("notifications") or {}
            return bool(notifications.get("psychology_alerts", True))
        except Exception:
            logger.warning("Suppressed exception", exc_info=True)
            pass
    stored = _read_psychology_pref_from_store(user_id)
    if stored is not None:
        return stored
    return True
