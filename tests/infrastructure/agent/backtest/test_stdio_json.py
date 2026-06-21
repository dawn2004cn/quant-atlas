"""Tests for backtest subprocess stdout JSON helper."""

from __future__ import annotations

import json
from io import StringIO

from app.infrastructure.agent.backtest import stdio_json
from app.infrastructure.agent.backtest.stdio_json import write_stdout_json


def test_write_stdout_json_emits_newline(monkeypatch):
    buf = StringIO()
    monkeypatch.setattr(stdio_json.sys, "stdout", buf)
    write_stdout_json({"ok": True, "n": 1})
    payload = json.loads(buf.getvalue().strip())
    assert payload == {"ok": True, "n": 1}
