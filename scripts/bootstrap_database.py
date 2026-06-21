"""Bootstrap database schema and connection pool."""

from __future__ import annotations

import logging

from app.config import AppSettings
from app.infrastructure.database.db_manager import get_db_manager, bootstrap_schema
from app.infrastructure.database.mysql_client import mysql_get_connection

logger = logging.getLogger(__name__)

def bootstrap_database():
    """Bootstrap database schema and connection pool."""
    settings = AppSettings.from_env()
    
    # Bootstrap schema
    try:
        bootstrap_schema(settings.mysql)
        logger.info("Database schema bootstrapped successfully")
    except Exception as e:
        logger.error(f"Failed to bootstrap schema: {e}")
    
    # Test connection pool
    try:
        conn = mysql_get_connection(settings.mysql)
        conn.close()
        logger.info("Connection pool initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize connection pool: {e}")

if __name__ == "__main__":
    bootstrap_database()
