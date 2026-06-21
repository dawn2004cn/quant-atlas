"""Legacy unit tests depend on ``scripts/`` modules (backtest_engine, trading_strategies)."""

from __future__ import annotations

import sys
from pathlib import Path

_scripts = Path(__file__).resolve().parents[2] / "scripts"
_scripts_str = str(_scripts)
if _scripts_str not in sys.path:
    sys.path.insert(0, _scripts_str)
