from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# Valid layout widgets recognized by the stock detail page
_STOCK_DETAIL_WIDGETS = frozenset({
    "resonance-meter",
    "decision-brief-strip",
    "technical-chart",
    "fundamental-panel",
    "news-feed",
    "trade-panel",
})


class PagePreferenceService:
    """Persist and retrieve page layout preferences via JSON files."""

    def __init__(self, store_path: Optional[Path] = None) -> None:
        self._store_path: Path = store_path or Path("page_preferences.json")
        self._data: Dict[str, Dict[str, Any]] = self._load()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if self._store_path.exists():
            try:
                with open(self._store_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save(self) -> None:
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._store_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def update_preferences(
        self, user_id: str, preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update preferences for a user, filtering out invalid widget IDs."""
        if user_id not in self._data:
            self._data[user_id] = {}

        merged: Dict[str, Any] = self._data[user_id].copy()
        merged.update(preferences)

        # Filter stock_detail_layout to known widgets
        if "stock_detail_layout" in merged:
            layout = merged["stock_detail_layout"]
            if isinstance(layout, list):
                merged["stock_detail_layout"] = [
                    w for w in layout if w in _STOCK_DETAIL_WIDGETS
                ]

        self._data[user_id] = merged
        self._save()
        return merged

    def get_preferences(self, user_id: str) -> Dict[str, Any]:
        return self._data.get(user_id, {})
