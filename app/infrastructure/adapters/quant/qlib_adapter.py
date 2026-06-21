"""Qlib adapter placeholder."""

from typing import Any, Dict


class QlibBacktestAdapter:
    """Adapter for Qlib backtest (disabled due to import issues)."""

    def __init__(self, qlib_config_path: str | None = None):
        self.config_path = qlib_config_path

    def run(self, strategy_config: Dict[str, Any]) -> Dict[str, Any]:
        """Disabled."""
        return {"status": "disabled", "message": "Qlib adapter unavailable"}