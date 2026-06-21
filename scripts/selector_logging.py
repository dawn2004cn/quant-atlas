"""Shared logging bootstrap for ``scripts/*_selector.py`` entrypoints."""

from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from app.core.logger import get_logger


def get_selector_logger(name: str):
    return get_logger(name)
