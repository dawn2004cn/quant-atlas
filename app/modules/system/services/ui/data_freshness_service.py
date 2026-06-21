from __future__ import annotations

"""Build trust metadata for market data freshness."""

from datetime import datetime, timezone
from typing import Any


class DataFreshnessService:
    """Attach ``data_timestamp`` and realtime trust flags to DTOs."""

    def __init__(self, *, realtime_threshold_sec: int = 300) -> None:
        self._threshold = max(1, int(realtime_threshold_sec))

    def assess(self, payload: Any, *, source: str = "unknown") -> dict[str, Any]:
        timestamp = self._find_timestamp(payload)
        age_sec = self._age_seconds(timestamp) if timestamp else None
        is_realtime = bool(age_sec is not None and age_sec <= self._threshold)
        return {
            "data_timestamp": timestamp or "",
            "is_realtime": is_realtime,
            "age_seconds": age_sec,
            "freshness_level": self._level(age_sec),
            "stale_after_seconds": self._threshold,
            "source": source,
        }

    def enrich_dict(self, row: dict[str, Any], *, source: str = "unknown") -> dict[str, Any]:
        out = dict(row)
        out["freshness"] = self.assess(row, source=source)
        out["data_timestamp"] = out["freshness"]["data_timestamp"]
        out["is_realtime"] = out["freshness"]["is_realtime"]
        return out

    def collection(self, rows: list[Any], *, source: str = "unknown") -> dict[str, Any]:
        return self.assess(rows, source=source)

    def _find_timestamp(self, payload: Any) -> str | None:
        if isinstance(payload, list):
            stamps = [self._find_timestamp(item) for item in payload]
            stamps = [stamp for stamp in stamps if stamp]
            return max(stamps) if stamps else None
        if not isinstance(payload, dict):
            payload = self._to_dict(payload)
        for key in ("updated_at", "data_timestamp", "timestamp", "quote_time", "trade_time", "datetime"):
            value = payload.get(key)
            if value:
                parsed = self._parse_datetime(value)
                if parsed:
                    return parsed.isoformat().replace("+00:00", "Z")
        for nested_key in ("profile", "realtime", "quote"):
            nested = payload.get(nested_key)
            if isinstance(nested, dict):
                found = self._find_timestamp(nested)
                if found:
                    return found
        return None

    @staticmethod
    def _to_dict(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if hasattr(value, "model_dump"):
            return value.model_dump()
        if hasattr(value, "dict"):
            return value.dict()
        return dict(getattr(value, "__dict__", {}) or {})

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if isinstance(value, datetime):
            dt = value
        else:
            text = str(value or "").strip()
            if not text:
                return None
            text = text.replace(" UTC", "+00:00").replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(text)
            except ValueError:
                try:
                    dt = datetime.strptime(text[:19], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    @staticmethod
    def _age_seconds(timestamp: str) -> int | None:
        dt = DataFreshnessService._parse_datetime(timestamp)
        if dt is None:
            return None
        return max(0, int((datetime.now(timezone.utc) - dt).total_seconds()))

    def _level(self, age_sec: int | None) -> str:
        if age_sec is None:
            return "unknown"
        if age_sec <= self._threshold:
            return "realtime"
        if age_sec <= self._threshold * 12:
            return "delayed"
        return "stale"


def enrich_market_payload(row: dict[str, Any], *, source: str = "unknown") -> dict[str, Any]:
    """Attach top-level freshness fields for quote/panorama DTOs."""
    return DataFreshnessService().enrich_dict(row, source=source)


__all__ = ["DataFreshnessService", "enrich_market_payload"]
