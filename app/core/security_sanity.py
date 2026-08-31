"""Boot-time security sanity checks (committed; no local secrets)."""

from __future__ import annotations

import logging
import os
import re

logger = logging.getLogger(__name__)

_BANNED_LITERALS = (
    "AdminPassword123!",
    "root123",
    "changeme",
)

_REDIS_LAN = re.compile(r"redis://192\.168\.\d+\.\d+")


def run_security_sanity_checks() -> None:
    """Warn when known-insecure defaults appear in the runtime environment."""
    for key, value in os.environ.items():
        if not value:
            continue
        for needle in _BANNED_LITERALS:
            if needle in value:
                logger.warning(
                    "Security sanity: banned literal %r found in env var %s",
                    needle,
                    key,
                )
        if _REDIS_LAN.search(value):
            logger.warning(
                "Security sanity: hardcoded LAN Redis URL in env var %s",
                key,
            )

    if os.environ.get("TESTING", "").lower() in {"1", "true", "yes"}:
        return

    if not os.environ.get("FLASK_SECRET_KEY", "").strip():
        logger.warning(
            "Security sanity: FLASK_SECRET_KEY is unset; sessions reset on restart"
        )
