"""Smoke: UI/CSS migration inline-style gate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECK_SCRIPT = ROOT / "scripts" / "check_template_inline_styles.py"


def test_template_inline_style_gate_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(CHECK_SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
