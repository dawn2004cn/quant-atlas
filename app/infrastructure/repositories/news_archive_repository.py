"""News Archive Repository.

This module re-exports the canonical implementation from the MySQL module.
The original ``NewsArchiveRepository`` class lived here after the P06 migration.
"""

from app.infrastructure.repositories.sqlite.sqlite_news_archive_repository import (
    SQLiteNewsArchiveRepository as NewsArchiveRepository,
)

__all__ = ["NewsArchiveRepository"]
