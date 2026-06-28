"""WSGI entry point for production gunicorn deployment.

Usage:
    gunicorn -c gunicorn_config.py app.wsgi:app
"""

from __future__ import annotations

from app.core.runtime_config import _load_dotenv_if_present

_load_dotenv_if_present()

from app import create_app

app = create_app()
