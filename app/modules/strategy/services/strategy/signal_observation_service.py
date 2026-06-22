from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Signal observation service.

Turns strategy signals into a lightweight simulated observation loop. The
service records an entry plan, refreshes current price, tracks max gain/drawdown
and marks whether stop-loss or target has been touched.

Supports converting observations to real positions for portfolio tracking.
"""


import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.logger import get_logger
from app.domain.enums import MarketCode
from app.domain.ports.signal_observation_port import SignalObservationRepository

logger = get_logger(__name__)


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


def _to_dict(value: object) -> GenericResponseDTO:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if isinstance(value, dict):
        return value
    return {}


class SignalObservationService:
    """Manage simulated observation cards derived from signals.

    Supports both MySQL (via repository) and JSON (fallback) storage.
    """

    def __init__(
        self,
        *,
        market_service: object | None = None,
        store_path: Path | None = None,
        observation_repository: SignalObservationRepository | None = None,
    ) -> None:
        self._market_service = market_service
        self._store_path = Path(store_path) if store_path else Path("instance/signal_observations.json")
        self._lock = threading.Lock()
        self._repo: SignalObservationRepository | None = observation_repository
        if not self._use_db():
            self._store_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_repo(self) -> SignalObservationRepository | None:
        return self._repo

    def _use_db(self) -> bool:
        """Check if using database repository."""
        return self._get_repo() is not None

    def _build_row_from_quote(self, symbol: str, market: MarketCode, user_id: int,
                                name: str, price: float, stop: float, target: float,
                                source: str, reason: str, ai_summary: str) -> GenericResponseDTO:
        """Build a new observation row."""
        now = _now_str()
        return {
            "id": uuid.uuid4().hex[:12],
            "user_id": user_id,
            "symbol": symbol,
            "market": market.value,
            "name": name,
            "entry_price": round(price, 4),
            "current_price": round(price, 4),
            "stop_loss": round(stop, 4),
            "target_price": round(target, 4),
            "source": source,
            "reason": reason,
            "ai_summary": ai_summary,
            "status": "open",
            "trigger_status": "watching",
            "created_at": now,
            "updated_at": now,
            "closed_at": None,
            "close_reason": "",
            "peak_price": round(price, 4),
            "trough_price": round(price, 4),
            "max_gain_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "return_pct": 0.0,
            "notes": "",
        }

    def _add_observation_db(self, *, symbol: str, market: MarketCode, user_id: int,
                             name: str, entry_price: float, stop_loss: float,
                             target_price: float, source: str, reason: str,
                             ai_summary: str) -> GenericResponseDTO:
        """Add observation using database repository."""
        repo = self._get_repo()
        existing = None
        try:
            obs_list = repo.list_observations(user_id=user_id, status="open", limit=50)
            for obs in obs_list:
                if obs.get("symbol") == symbol and obs.get("market") == market.value:
                    existing = obs
                    break
        except Exception as e:
            logger.warning("Failed to check existing observations: %s", e)

        if existing:
            quote = self._quote(symbol, market)
            current_price = _safe_float(quote.get("price"), entry_price)
            repo.update_observation(
                existing["id"],
                user_id,
                {
                    "name": name,
                    "entry_price": round(entry_price, 4),
                    "current_price": round(current_price, 4),
                    "stop_loss": round(stop_loss, 4),
                    "target_price": round(target_price, 4),
                    "source": source,
                    "reason": reason,
                    "ai_summary": ai_summary,
                }
            )
            return repo.get_observation(existing["id"], user_id)

        row = self._build_row_from_quote(symbol, market, user_id, name, entry_price, stop_loss, target_price, source, reason, ai_summary)
        repo.create_observation(row)
        return row

    def add_observation(
        self,
        *,
        symbol: str,
        market: MarketCode = MarketCode.CN,
        user_id: int = 1,
        name: str | None = None,
        entry_price: float | None = None,
        stop_loss: float | None = None,
        target_price: float | None = None,
        source: str = "manual",
        reason: str = "",
        ai_summary: str = "",
    ) -> GenericResponseDTO:
        """Add or refresh an open observation for a symbol."""
        clean_symbol = str(symbol or "").strip().upper()
        if not clean_symbol:
            raise ValueError("symbol_required")
        quote = self._quote(clean_symbol, market)
        price = _safe_float(entry_price) or _safe_float(quote.get("price"))
        if price <= 0:
            raise ValueError(f"entry_price_required: {clean_symbol}/{market}")
        stop = _safe_float(stop_loss) or round(price * 0.93, 2)
        target = _safe_float(target_price) or round(price * 1.12, 2)

        obs_name = name or quote.get("name") or clean_symbol

        if self._get_repo():
            return self._add_observation_db(
                symbol=clean_symbol, market=market, user_id=user_id,
                name=obs_name, entry_price=price, stop_loss=stop,
                target_price=target, source=source, reason=reason,
                ai_summary=ai_summary
            )

        now = _now_str()

        with self._lock:
            rows = self._read_rows()
            for row in rows:
                if (row.get("status") == "open" and
                    row.get("symbol") == clean_symbol and
                    row.get("market") == market.value and
                    row.get("user_id") == user_id):
                    row.update(
                        {
                            "name": name or quote.get("name") or row.get("name") or clean_symbol,
                            "entry_price": round(price, 4),
                            "current_price": round(_safe_float(quote.get("price"), price), 4),
                            "stop_loss": round(stop, 4),
                            "target_price": round(target, 4),
                            "source": source or row.get("source") or "manual",
                            "reason": reason or row.get("reason") or "",
                            "ai_summary": ai_summary or row.get("ai_summary") or "",
                            "updated_at": now,
                        }
                    )
                    row = self._refresh_row(row, quote)
                    self._write_rows(rows)
                    return row

            row = {
                "id": uuid.uuid4().hex[:12],
                "user_id": user_id,
                "symbol": clean_symbol,
                "market": market.value,
                "name": name or quote.get("name") or clean_symbol,
                "entry_price": round(price, 4),
                "current_price": round(_safe_float(quote.get("price"), price), 4),
                "stop_loss": round(stop, 4),
                "target_price": round(target, 4),
                "source": source or "manual",
                "reason": reason or "",
                "ai_summary": ai_summary or "",
                "status": "open",
                "trigger_status": "watching",
                "created_at": now,
                "updated_at": now,
                "closed_at": None,
                "close_reason": "",
                "peak_price": round(price, 4),
                "trough_price": round(price, 4),
                "max_gain_pct": 0.0,
                "max_drawdown_pct": 0.0,
            }
            row = self._refresh_row(row, quote)
            rows.append(row)
            self._write_rows(rows)
            return row

    def list_observations(
        self,
        *,
        user_id: int = 1,
        status: str = "open",
        refresh: bool = True
    ) -> GenericResponseDTO:
        """List observations for a user, optionally refreshing quote-derived metrics."""
        status_filter = (status or "open").strip().lower()

        if self._get_repo():
            try:
                repo = self._get_repo()
                items = repo.list_observations(user_id=user_id, status=status_filter, limit=100)
                if refresh:
                    items = self._refresh_rows(items)
                    for item in items:
                        if item.get("id"):
                            self._repo.update_observation(item["id"], user_id, item)
                return {"items": items, "count": len(items), "status": status_filter}
            except Exception as e:
                logger.warning("DB list_observations failed, falling back to JSON: %s", e)

        with self._lock:
            rows = self._read_rows()
            if refresh:
                rows = self._refresh_rows(rows)
                self._write_rows(rows)
        items = [r for r in rows if r.get("user_id") == user_id]
        if status_filter not in ("all", "*"):
            items = [r for r in items if str(r.get("status") or "").lower() == status_filter]
        items.sort(key=lambda r: str(r.get("updated_at") or r.get("created_at") or ""), reverse=True)
        return {"items": items, "count": len(items), "status": status_filter}

    def close_observation(
        self,
        observation_id: str,
        *,
        user_id: int = 1,
        reason: str = "manual_close"
    ) -> GenericResponseDTO:
        """Close one observation manually."""
        oid = str(observation_id or "").strip()
        if not oid:
            raise ValueError("observation_id_required")

        if self._get_repo():
            repo = self._get_repo()
            result = repo.close_observation(oid, user_id, reason)
            if result:
                return result
            raise ValueError("observation_not_found")

        with self._lock:
            rows = self._read_rows()
            for row in rows:
                if row.get("id") == oid and row.get("user_id") == user_id:
                    row["status"] = "closed"
                    row["close_reason"] = reason or "manual_close"
                    row["closed_at"] = _now_str()
                    row["updated_at"] = row["closed_at"]
                    self._write_rows(rows)
                    return row
        raise ValueError("observation_not_found")

    def update_notes(self, observation_id: str, user_id: int, notes: str) -> GenericResponseDTO:
        """Update observation notes."""
        oid = str(observation_id or "").strip()
        if not oid:
            raise ValueError("observation_id_required")

        if self._get_repo():
            repo = self._get_repo()
            repo.update_notes(oid, user_id, notes)
            return repo.get_observation(oid, user_id) or {"id": oid, "notes": notes}

        with self._lock:
            rows = self._read_rows()
            for row in rows:
                if row.get("id") == oid and row.get("user_id") == user_id:
                    row["notes"] = notes
                    row["updated_at"] = _now_str()
                    self._write_rows(rows)
                    return row
        raise ValueError("observation_not_found")

    def stats(self, *, user_id: int = 1) -> GenericResponseDTO:
        """Aggregate observation performance by source for a user."""
        if self._get_repo():
            try:
                return self._get_repo().get_stats(user_id)
            except Exception as e:
                logger.warning("DB stats failed, falling back to JSON: %s", e)

        rows = self.list_observations(user_id=user_id, status="all", refresh=True)["items"]
        by_source: dict[str, dict[str, Any]] = {}
        for row in rows:
            src = str(row.get("source") or "unknown")
            item = by_source.setdefault(
                src,
                {
                    "source": src,
                    "count": 0,
                    "open_count": 0,
                    "target_hits": 0,
                    "stop_hits": 0,
                    "avg_return_pct": 0.0,
                    "avg_max_gain_pct": 0.0,
                    "avg_max_drawdown_pct": 0.0,
                },
            )
            item["count"] += 1
            if row.get("status") == "open":
                item["open_count"] += 1
            if row.get("trigger_status") == "target_hit":
                item["target_hits"] += 1
            if row.get("trigger_status") == "stop_hit":
                item["stop_hits"] += 1
            item["avg_return_pct"] += _safe_float(row.get("return_pct"))
            item["avg_max_gain_pct"] += _safe_float(row.get("max_gain_pct"))
            item["avg_max_drawdown_pct"] += _safe_float(row.get("max_drawdown_pct"))

        for item in by_source.values():
            count = max(int(item["count"]), 1)
            item["target_hit_rate"] = round(item["target_hits"] / count * 100, 2)
            item["stop_hit_rate"] = round(item["stop_hits"] / count * 100, 2)
            item["avg_return_pct"] = round(item["avg_return_pct"] / count, 2)
            item["avg_max_gain_pct"] = round(item["avg_max_gain_pct"] / count, 2)
            item["avg_max_drawdown_pct"] = round(item["avg_max_drawdown_pct"] / count, 2)
        return {"items": list(by_source.values()), "total": len(rows)}

    def _quote(self, symbol: str, market: MarketCode) -> GenericResponseDTO:
        try:
            rows = self._market_service.list_quotes(market, [symbol])
            if rows:
                return _to_dict(rows[0])
        except Exception as exc:  # noqa: BLE001
            logger.warning("signal observation quote unavailable for %s: %s", symbol, exc)
        return {"code": symbol, "name": symbol}

    def _refresh_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        open_rows = [r for r in rows if r.get("status") == "open"]
        by_market: dict[str, list[str]] = {}
        for row in open_rows:
            by_market.setdefault(str(row.get("market") or "CN"), []).append(str(row.get("symbol") or ""))

        quotes: dict[tuple[str, str], dict[str, Any]] = {}
        for market_raw, symbols in by_market.items():
            try:
                market = MarketCode(market_raw)
            except ValueError:
                market = MarketCode.CN
            try:
                for quote in self._market_service.list_quotes(market, symbols):
                    q = _to_dict(quote)
                    code = str(q.get("code") or "")
                    quotes[(market.value, code)] = q
                    quotes[(market.value, code[-6:])] = q
            except Exception as exc:  # noqa: BLE001
                logger.warning("signal observation batch quote unavailable: %s", exc)

        for row in rows:
            if row.get("status") != "open":
                continue
            key = (str(row.get("market") or "CN"), str(row.get("symbol") or ""))
            quote = quotes.get(key) or quotes.get((key[0], key[1][-6:])) or {}
            self._refresh_row(row, quote)
        return rows

    def _refresh_row(self, row: dict[str, Any], quote: dict[str, Any]) -> GenericResponseDTO:
        entry = _safe_float(row.get("entry_price"))
        current = _safe_float(quote.get("price")) or _safe_float(row.get("current_price")) or entry
        if entry <= 0 or current <= 0:
            return row
        peak = max(_safe_float(row.get("peak_price"), entry), current)
        trough = min(_safe_float(row.get("trough_price"), entry), current)
        stop = _safe_float(row.get("stop_loss"))
        target = _safe_float(row.get("target_price"))
        row["current_price"] = round(current, 4)
        row["current_change_pct"] = _safe_float(quote.get("change_pct"))
        row["peak_price"] = round(peak, 4)
        row["trough_price"] = round(trough, 4)
        row["return_pct"] = round((current / entry - 1) * 100, 2)
        row["max_gain_pct"] = round((peak / entry - 1) * 100, 2)
        row["max_drawdown_pct"] = round((trough / entry - 1) * 100, 2)
        row["risk_reward_ratio"] = self._risk_reward(entry, stop, target)
        if stop > 0 and current <= stop:
            row["trigger_status"] = "stop_hit"
        elif target > 0 and current >= target:
            row["trigger_status"] = "target_hit"
        else:
            row["trigger_status"] = "watching"
        row["updated_at"] = _now_str()
        return row

    def _risk_reward(self, entry: float, stop: float, target: float) -> float:
        downside = max(entry - stop, 0.01)
        upside = max(target - entry, 0)
        return round(upside / downside, 2)

    def _read_rows(self) -> list[dict[str, Any]]:
        if not self._store_path.exists():
            return []
        try:
            raw = json.loads(self._store_path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                return [dict(x) for x in raw if isinstance(x, dict)]
        except Exception as exc:  # noqa: BLE001
            logger.warning("signal observation store read failed: %s", exc)
        return []

    def _write_rows(self, rows: list[dict[str, Any]]) -> None:
        self._store_path.write_text(
            json.dumps(rows, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def convert_to_position(
        self,
        observation_id: str,
        *,
        user_id: int = 1,
        shares: int | None = None,
        cost_basis: float | None = None
    ) -> GenericResponseDTO:
        """Convert an observation to a formal position (simulated holding)."""
        oid = str(observation_id or "").strip()
        if not oid:
            raise ValueError("observation_id_required")

        if self._get_repo():
            repo = self._get_repo()
            obs = repo.get_observation(oid, user_id)
            if not obs:
                raise ValueError("observation_not_found")

            now = _now_str()
            shares_val = shares or 100
            cost_val = cost_basis or obs.get("entry_price", 0)
            current_price = obs.get("current_price", cost_val)

            position_data = {
                "id": uuid.uuid4().hex[:12],
                "user_id": user_id,
                "observation_id": oid,
                "symbol": obs.get("symbol"),
                "market": obs.get("market"),
                "name": obs.get("name"),
                "shares": shares_val,
                "cost_basis": round(cost_val, 4),
                "current_price": round(current_price, 4),
                "total_cost": round(shares_val * cost_val, 2),
                "total_value": round(shares_val * current_price, 2),
                "pnl": round(shares_val * (current_price - cost_val), 2),
                "return_pct": round((current_price - cost_val) / cost_val * 100, 4) if cost_val else 0,
                "max_gain_pct": 0,
                "max_drawdown_pct": 0,
                "source": obs.get("source"),
                "converted_at": now,
                "created_at": obs.get("created_at"),
                "updated_at": now,
            }

            repo.create_position(position_data)
            repo.update_observation(oid, user_id, {"status": "position"})
            return position_data

        with self._lock:
            rows = self._read_rows()
            for row in rows:
                if row.get("id") == oid and row.get("user_id") == user_id:
                    row["status"] = "position"
                    row["shares"] = shares or 100
                    row["cost_basis"] = cost_basis or row.get("entry_price", 0)
                    row["converted_at"] = _now_str()
                    row["updated_at"] = _now_str()
                    self._write_rows(rows)
                    return row
        raise ValueError("observation_not_found")

    def list_positions(self, *, user_id: int = 1) -> GenericResponseDTO:
        """List all converted positions for a user."""
        if self._get_repo():
            try:
                repo = self._get_repo()
                positions = repo.list_positions(user_id=user_id, limit=100)
                total_cost = sum(p.get("total_cost", 0) or 0 for p in positions)
                total_value = sum(p.get("total_value", 0) or 0 for p in positions)
                total_pnl = sum(p.get("pnl", 0) or 0 for p in positions)
                total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
                return {
                    "positions": positions,
                    "count": len(positions),
                    "total_cost": round(total_cost, 2),
                    "total_value": round(total_value, 2),
                    "total_pnl": round(total_pnl, 2),
                    "total_pnl_pct": round(total_pnl_pct, 2),
                }
            except Exception as e:
                logger.warning("DB list_positions failed, falling back to JSON: %s", e)

        rows = self._read_rows()
        positions = [r for r in rows if r.get("status") == "position" and r.get("user_id") == user_id]
        
        total_cost = 0.0
        total_value = 0.0
        for pos in positions:
            shares = pos.get("shares", 0)
            cost = pos.get("cost_basis", 0)
            current = pos.get("current_price", 0)
            total_cost += shares * cost
            total_value += shares * current
        
        total_pnl = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
        
        return {
            "positions": positions,
            "count": len(positions),
            "total_cost": round(total_cost, 2),
            "total_value": round(total_value, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
        }
