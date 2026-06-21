"""Subprocess IPC: emit structured JSON on stdout (not application logging)."""

from __future__ import annotations

import json
import sys
from typing import Any


def write_stdout_json(payload: Any, *, indent: int | None = 2) -> None:
    """Write one JSON document to stdout for parent process parsers."""
    text = json.dumps(payload, indent=indent, ensure_ascii=False)
    sys.stdout.write(text)
    if not text.endswith("\n"):
        sys.stdout.write("\n")
    sys.stdout.flush()


def write_stdout_error(message: str, **extra: Any) -> None:
    """Emit a JSON error object on stdout then exit (subprocess contract)."""
    body: dict[str, Any] = {"error": message}
    body.update(extra)
    write_stdout_json(body, indent=None)
    raise SystemExit(1)
