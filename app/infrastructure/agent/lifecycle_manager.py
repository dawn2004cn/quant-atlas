from __future__ import annotations
"""Lifecycle Manager: Archives stale experiment data."""


import shutil
import time
from pathlib import Path


from app.core.logger import get_logger

logger = get_logger(__name__)

class LifecycleManager:
    """Manages the lifecycle of experiment assets."""

    def __init__(self, data_dir: Path, archive_dir: Path, days_to_keep: int = 30):
        self.data_dir = data_dir
        self.archive_dir = archive_dir
        self.threshold_seconds = days_to_keep * 24 * 60 * 60

    def run_archiving(self) -> int:
        """Move stale experiments to archive."""
        count = 0
        now = time.time()

        for path in self.data_dir.glob("*.json"):
            if path.is_file():
                # Check modification time
                if now - path.stat().st_mtime > self.threshold_seconds:
                    logger.info(f"Archiving stale experiment: {path.name}")
                    shutil.move(str(path), str(self.archive_dir / path.name))
                    count += 1
        return count
