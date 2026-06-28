"""Tier 5: Large Institution — Impact Model, Execution Algos, Federated Deployment, RBAC."""

from __future__ import annotations

import hashlib
import json
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from app.core.logger import get_logger
from app.infrastructure.database.models import Role, UserRoleAssignment

logger = get_logger(__name__)

Permission = Literal["read", "write", "execute", "admin"]
ResourceType = Literal["data", "strategy", "factor", "order", "account", "user"]


# ── Market Impact Model ─────────────────────────────────────────────

@dataclass
class ImpactForecast:
    """Market impact forecast for a large order."""
    symbol: str
    order_value_usd: float
    side: str  # buy / sell
    estimated_impact_bps: float
    estimated_slippage_bps: float
    liquidity_score: float  # 0..1
    suggested_speed: str  # slow / normal / urgent
    expected_price_movement_pct: float
    confidence: float = 0.0


class MarketImpactModelService:
    """Market impact forecasting for large institutional orders."""

    def forecast(self, symbol: str, order_value_usd: float, side: str = "buy",
                 avg_daily_volume_usd: float = 10_000_000,
                 volatility: float = 0.02) -> ImpactForecast:
        """Forecast market impact of a large order using square-root model."""
        participation_rate = order_value_usd / max(avg_daily_volume_usd, 1)

        # Square-root impact model: impact ∝ sqrt(participation)
        raw_impact = 100 * volatility * math.sqrt(participation_rate)
        impact_bps = raw_impact * 100  # convert to bps

        # Slippage is typically 0.5-1.5x of impact
        slippage_bps = impact_bps * (0.8 if side == "buy" else 1.2)

        # Liquidity score
        liquidity_score = max(0, min(1, 1 - participation_rate * 5))

        # Suggested execution speed
        if impact_bps > 50:
            speed = "slow"
        elif impact_bps > 20:
            speed = "normal"
        else:
            speed = "urgent"

        return ImpactForecast(
            symbol=symbol,
            order_value_usd=order_value_usd,
            side=side,
            estimated_impact_bps=round(impact_bps, 2),
            estimated_slippage_bps=round(slippage_bps, 2),
            liquidity_score=round(liquidity_score, 4),
            suggested_speed=speed,
            expected_price_movement_pct=round(impact_bps / 100, 4),
            confidence=round(max(0, 1 - participation_rate), 3),
        )


    def forecast_almgren_chriss(self, symbol: str, order_value_usd: float,
                                 side: str = "buy", price: float = 100.0,
                                 avg_daily_volume_usd: float = 10_000_000,
                                 volatility: float = 0.02,
                                 trading_days: int = 1,
                                 spread_bps: float = 5.0) -> dict:
        """Almgren-Chriss impact model: permanent + temporary decomposition."""
        participation = order_value_usd / max(avg_daily_volume_usd, 1)
        sigma = volatility * math.sqrt(trading_days)

        # Permanent impact (information leakage): gamma * sigma * sign
        gamma = 0.1
        permanent_bps = gamma * sigma * 10000 * (1 if side == "buy" else -1)

        # Temporary impact (liquidity demand): eta * sigma * participation^beta
        eta = 0.3
        beta = 0.6
        temporary_bps = eta * sigma * math.pow(participation, beta) * 10000

        total_bps = abs(permanent_bps) + temporary_bps
        slippage_cost = total_bps / 10000 * order_value_usd

        return {
            "symbol": symbol,
            "order_value_usd": order_value_usd,
            "side": side,
            "participation_rate": round(participation, 6),
            "permanent_impact_bps": round(permanent_bps, 4),
            "temporary_impact_bps": round(temporary_bps, 4),
            "total_impact_bps": round(total_bps, 4),
            "slippage_cost_usd": round(slippage_cost, 2),
            "spread_bps": spread_bps,
            "confidence": round(max(0, 1 - participation * 3), 3),
        }

    def forecast_multi_asset(self, orders: list[dict]) -> dict:
        """Portfolio-level impact forecast across multiple assets."""
        results = []
        total_slippage = 0.0
        total_value = 0.0
        for o in orders:
            result = self.forecast_almgren_chriss(
                symbol=o.get("symbol", ""),
                order_value_usd=float(o.get("order_value_usd", 0)),
                side=o.get("side", "buy"),
                price=float(o.get("price", 100)),
                avg_daily_volume_usd=float(o.get("avg_daily_volume_usd", 10_000_000)),
                volatility=float(o.get("volatility", 0.02)),
                spread_bps=float(o.get("spread_bps", 5)),
            )
            results.append(result)
            total_slippage += result["slippage_cost_usd"]
            total_value += result["order_value_usd"]
        return {
            "orders": results,
            "total_value_usd": round(total_value, 2),
            "total_slippage_usd": round(total_slippage, 2),
            "weighted_avg_impact_bps": round(
                total_slippage / max(total_value, 1) * 10000, 4
            ) if total_value > 0 else 0,
            "num_assets": len(orders),
        }

# ── Advanced Execution Algos ─────────────────────────────────────────

@dataclass
class ExecutionSchedule:
    """Unified execution schedule for institutional algos."""
    schedule_id: str
    algo: str  # vwap / twap / iceberg / pov
    symbol: str
    side: str
    total_quantity: int
    slices: list[dict] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class POVSchedule:
    """Percentage of Volume execution schedule."""
    schedule_id: str
    symbol: str
    side: str
    total_quantity: int
    participation_rate: float  # 0.05 = 5% of volume
    slices: list[dict] = field(default_factory=list)


class AdvancedExecutionAlgoService:
    """VWAP, TWAP, Iceberg, POV execution algorithms."""

    def generate_vwap(
        self,
        symbol: str,
        side: str,
        total_quantity: int,
        num_slices: int = 20,
        volume_profile: list[float] | None = None,
    ) -> ExecutionSchedule:
        """VWAP: slice by volume-weighted profile across the session."""
        profile = volume_profile or self._default_volume_profile(num_slices)
        total_weight = sum(profile) or 1.0
        remaining = total_quantity
        slices: list[dict] = []
        for i, weight in enumerate(profile):
            if i == len(profile) - 1:
                qty = remaining
            else:
                qty = max(1, int(total_quantity * weight / total_weight))
                remaining -= qty
            slices.append({
                "slice": i + 1,
                "quantity": qty,
                "weight_pct": round(weight / total_weight * 100, 2),
                "type": "limit",
                "note": "VWAP volume-weighted slice",
            })
        return ExecutionSchedule(
            schedule_id=f"vwap.{uuid.uuid4().hex[:8]}",
            algo="vwap",
            symbol=symbol,
            side=side,
            total_quantity=total_quantity,
            slices=slices,
            params={"num_slices": num_slices},
        )

    def generate_twap(
        self,
        symbol: str,
        side: str,
        total_quantity: int,
        num_slices: int = 20,
        interval_minutes: int = 5,
    ) -> ExecutionSchedule:
        """TWAP: equal quantity per time interval."""
        qty_per_slice = max(1, total_quantity // num_slices)
        slices = []
        for i in range(num_slices):
            qty = qty_per_slice if i < num_slices - 1 else total_quantity - qty_per_slice * (num_slices - 1)
            slices.append({
                "slice": i + 1,
                "quantity": qty,
                "interval_minutes": interval_minutes,
                "type": "limit",
                "note": f"TWAP every {interval_minutes}min",
            })
        return ExecutionSchedule(
            schedule_id=f"twap.{uuid.uuid4().hex[:8]}",
            algo="twap",
            symbol=symbol,
            side=side,
            total_quantity=total_quantity,
            slices=slices,
            params={"interval_minutes": interval_minutes, "num_slices": num_slices},
        )

    def generate_iceberg(
        self,
        symbol: str,
        side: str,
        total_quantity: int,
        display_quantity: int = 100,
        variance_pct: float = 0.1,
    ) -> ExecutionSchedule:
        """Iceberg: show small display size, replenish hidden quantity."""
        display_qty = max(1, min(display_quantity, total_quantity))
        remaining = total_quantity
        slices = []
        slice_idx = 1
        while remaining > 0:
            shown = min(display_qty, remaining)
            if variance_pct > 0:
                jitter = int(shown * variance_pct * (0.5 - (hash(f"{symbol}{slice_idx}") % 100) / 100))
                shown = max(1, shown + jitter)
                shown = min(shown, remaining)
            slices.append({
                "slice": slice_idx,
                "quantity": shown,
                "display_quantity": shown,
                "hidden": True,
                "type": "limit",
                "note": "Iceberg display slice",
            })
            remaining -= shown
            slice_idx += 1
            if slice_idx > 500:
                break
        return ExecutionSchedule(
            schedule_id=f"ice.{uuid.uuid4().hex[:8]}",
            algo="iceberg",
            symbol=symbol,
            side=side,
            total_quantity=total_quantity,
            slices=slices,
            params={"display_quantity": display_qty, "variance_pct": variance_pct},
        )

    def generate_pov(self, symbol: str, side: str, total_quantity: int,
                     participation_rate: float = 0.1,
                     num_slices: int = 20) -> POVSchedule:
        """Generate POV execution schedule."""
        qty_per_slice = max(1, total_quantity // num_slices)
        slices = []

        for i in range(num_slices):
            qty = qty_per_slice if i < num_slices - 1 else total_quantity - qty_per_slice * (num_slices - 1)
            slices.append({
                "slice": i + 1,
                "quantity": qty,
                "participation_target": participation_rate,
                "type": "market",
                "note": f"Target {participation_rate*100:.0f}% of volume",
            })

        return POVSchedule(
            schedule_id=f"pov.{uuid.uuid4().hex[:8]}",
            symbol=symbol,
            side=side,
            total_quantity=total_quantity,
            participation_rate=participation_rate,
            slices=slices,
        )

    @staticmethod
    def _default_volume_profile(num_slices: int) -> list[float]:
        """U-shaped intraday volume profile approximation."""
        if num_slices <= 1:
            return [1.0]
        mid = num_slices // 2
        return [1.5 if i < 2 or i >= num_slices - 2 else 0.6 + 0.4 * (1 - abs(i - mid) / max(mid, 1))
                for i in range(num_slices)]


# ── Federated / Air-gapped Deployment ──────────────────────────────

    def generate_adaptive(self, symbol: str, side: str, total_quantity: int,
                           impact_bps: float = 0.0, urgency: str = "normal",
                           market_volatility: float = 0.02) -> ExecutionSchedule:
        """Adaptive algo: auto-selects VWAP/TWAP/iceberg based on impact & urgency."""
        if impact_bps > 50 or urgency == "stealth":
            return self.generate_iceberg(symbol, side, total_quantity,
                                          display_quantity=max(1, total_quantity // 10))
        elif impact_bps > 20 or market_volatility > 0.03:
            return self.generate_twap(symbol, side, total_quantity)
        else:
            return self.generate_vwap(symbol, side, total_quantity)

    def generate_implementation_shortfall(self, symbol: str, side: str,
                                           total_quantity: int, price: float,
                                           urgency: str = "normal",
                                           num_slices: int = 10) -> ExecutionSchedule:
        """Implementation Shortfall: trade off market impact vs. timing risk."""
        if urgency == "urgent":
            profile = [0.30, 0.20, 0.15, 0.10, 0.08, 0.06, 0.05, 0.03, 0.02, 0.01]
        elif urgency == "slow":
            profile = [0.02, 0.03, 0.05, 0.07, 0.10, 0.12, 0.15, 0.18, 0.18, 0.10]
        else:
            profile = [0.15, 0.15, 0.12, 0.12, 0.10, 0.10, 0.08, 0.08, 0.05, 0.05]

        total_weight = sum(profile) or 1.0
        remaining = total_quantity
        slices = []
        for i, w in enumerate(profile):
            if i == len(profile) - 1:
                qty = remaining
            else:
                qty = max(1, int(total_quantity * w / total_weight))
                remaining -= qty
            slices.append({
                "slice": i + 1,
                "quantity": qty,
                "weight_pct": round(w / total_weight * 100, 2),
                "type": "limit",
                "note": f"shortfall slice (urgency={urgency})",
            })
        return ExecutionSchedule(
            schedule_id=f"shortfall.{uuid.uuid4().hex[:8]}",
            algo="implementation_shortfall",
            symbol=symbol,
            side=side,
            total_quantity=total_quantity,
            slices=slices,
            params={"urgency": urgency, "arrival_price": price, "num_slices": num_slices},
        )


@dataclass
class FederatedModelUpdate:
    """A model update from a federated node."""
    update_id: str
    node_id: str
    model_name: str
    gradient_hash: str
    weight_updates: dict[str, float]
    performance_delta: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class DeploymentNode:
    """A federated or air-gapped deployment node."""
    node_id: str
    name: str
    mode: str  # online / airgap / federated
    last_sync: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FederatedClusterStatus:
    """Health summary for federated deployment cluster."""
    total_nodes: int = 0
    active_nodes: int = 0
    stale_nodes: int = 0
    pending_updates: int = 0
    models_with_updates: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class FedAvgRoundResult:
    """Result of a FedAvg aggregation round."""
    ok: bool
    model_name: str
    nodes_used: int = 0
    weights: dict[str, float] = field(default_factory=dict)
    message: str = ""


class FederatedDeploymentService:
    """Federated learning and air-gapped deployment support."""

    def __init__(self):
        root = Path(__file__).resolve().parents[4]
        self._store = root / "instance" / "federated"
        self._store.mkdir(parents=True, exist_ok=True)
        self._updates_file = self._store / "model_updates.jsonl"
        self._nodes_file = self._store / "deployment_nodes.jsonl"
        self._config_file = self._store / "deployment_config.json"
        self._models_dir = self._store / "aggregated_models"
        self._models_dir.mkdir(parents=True, exist_ok=True)

    def get_deployment_config(self) -> dict[str, Any]:
        """Get global deployment configuration."""
        if self._config_file.exists():
            return json.loads(self._config_file.read_text(encoding="utf-8"))
        return {
            "mode": "federated",
            "airgap_enabled": False,
            "sync_interval_hours": 24,
            "min_nodes_for_aggregate": 2,
            "heartbeat_timeout_sec": 300,
            "update_ttl_hours": 48,
        }

    def set_deployment_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Update deployment configuration."""
        current = self.get_deployment_config()
        current.update(config)
        self._config_file.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
        return current

    def _parse_ts(self, ts: str) -> datetime:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))

    def _load_nodes_map(self) -> dict[str, DeploymentNode]:
        if not self._nodes_file.exists():
            return {}
        nodes: dict[str, DeploymentNode] = {}
        with self._nodes_file.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
        if not self._nodes_file.exists():
            return {}
        nodes: dict[str, DeploymentNode] = {}
        with self._nodes_file.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                data = json.loads(line)
                node = DeploymentNode(**data)
                nodes[node.node_id] = node
        return nodes

    def _write_nodes(self, nodes: dict[str, DeploymentNode]) -> None:
        _lines = [json.dumps(n.__dict__, ensure_ascii=False) for n in nodes.values()]
        self._nodes_file.write_text("\n".join(_lines) + ("\n" if _lines else ""), encoding="utf-8")

    def export_model(self, model_name: str, export_format: str = "json") -> dict | None:
        """Export aggregated model for air-gapped transfer."""
        model = self.get_aggregated_model(model_name)
        if model is None:
            return None
        export = {
            "model_name": model_name,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "format": export_format,
            "version": model.get("version", 1),
            "weights": model.get("weights", {}),
            "num_nodes": model.get("num_nodes", 0),
            "performance_metrics": model.get("performance_metrics", {}),
            "signature": hashlib.sha256(
                json.dumps(model.get("weights", {}), sort_keys=True).encode("utf-8")
            ).hexdigest()[:16],
        }
        return export

    def import_model(self, model_name: str, export_data: dict) -> bool:
        """Import model from air-gapped transfer."""
        weights = export_data.get("weights", {})
        if not weights:
            return False
        out_path = self._models_dir / f"{model_name.replace('/', '_')}.json"
        out_path.write_text(
            json.dumps({
                "model_name": model_name,
                "weights": weights,
                "version": export_data.get("version", 1),
                "num_nodes": export_data.get("num_nodes", 0),
                "performance_metrics": export_data.get("performance_metrics", {}),
                "imported_at": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Model %s imported from air-gapped transfer (version=%s)",
                   model_name, export_data.get("version", 1))
        return True
    def register_node(self, node_id: str, name: str, mode: str = "federated") -> DeploymentNode:
        """Register or refresh a deployment node."""
        nodes = self._load_nodes_map()
        node = DeploymentNode(node_id=node_id, name=name, mode=mode)
        nodes[node_id] = node
        self._write_nodes(nodes)
        logger.info("Deployment node registered: %s (%s, mode=%s)", node_id, name, mode)
        return node
    def heartbeat(self, node_id: str, *, metadata: dict[str, Any] | None = None) -> DeploymentNode | None:
        """Record node heartbeat and refresh last_sync."""
        nodes = self._load_nodes_map()
        node = nodes.get(node_id)
        if node is None:
            return None
        node.last_sync = datetime.now(timezone.utc).isoformat()
        node.active = True
        if metadata:
            node.metadata.update(metadata)
        nodes[node_id] = node
        self._write_nodes(nodes)
        logger.debug("Federated heartbeat: %s", node_id)
        return node

    def list_nodes(self) -> list[dict[str, Any]]:
        """List deployment nodes with stale/active health flags."""
        config = self.get_deployment_config()
        timeout = int(config.get("heartbeat_timeout_sec", 300))
        now = datetime.now(timezone.utc)
        result: list[dict[str, Any]] = []
        for node in self._load_nodes_map().values():
            last = self._parse_ts(node.last_sync)
            age = int((now - last).total_seconds())
            row = dict(node.__dict__)
            row["seconds_since_sync"] = age
            row["stale"] = age > timeout
            result.append(row)
        return result

    def get_cluster_status(self) -> FederatedClusterStatus:
        """Cluster health: active/stale nodes and pending model updates."""
        nodes = self.list_nodes()
        active = sum(1 for n in nodes if not n.get("stale"))
        stale = sum(1 for n in nodes if n.get("stale"))
        updates = self._load_all_updates()
        models = sorted({u.get("model_name", "") for u in updates if u.get("model_name")})
        return FederatedClusterStatus(
            total_nodes=len(nodes),
            active_nodes=active,
            stale_nodes=stale,
            pending_updates=len(updates),
            models_with_updates=models,
            config=self.get_deployment_config(),
        )

    def scan_cluster_health(self, *, mark_inactive: bool = True) -> dict[str, Any]:
        """Scheduler hook: detect stale nodes and optionally mark them inactive."""
        stale_ids = [n["node_id"] for n in self.list_nodes() if n.get("stale")]
        if mark_inactive and stale_ids:
            nodes = self._load_nodes_map()
            changed = False
            for node_id in stale_ids:
                node = nodes.get(node_id)
                if node is not None and node.active:
                    node.active = False
                    changed = True
            if changed:
                self._write_nodes(nodes)
        status = self.get_cluster_status()
        if stale_ids:
            logger.info(
                "Federated cluster scan: %d stale node(s): %s",
                len(stale_ids),
                ", ".join(stale_ids[:5]),
            )
        return {
            "ok": True,
            "stale_node_ids": stale_ids,
            "total_nodes": status.total_nodes,
            "active_nodes": status.active_nodes,
            "stale_nodes": status.stale_nodes,
            "pending_updates": status.pending_updates,
        }

    def _load_all_updates(self) -> list[dict[str, Any]]:
        if not self._updates_file.exists():
            return []
        rows: list[dict[str, Any]] = []
        with self._updates_file.open("r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    rows.append(json.loads(line))
        return rows

    def _eligible_updates(self, model_name: str) -> list[dict[str, Any]]:
        """Updates from non-stale nodes within TTL window."""
        config = self.get_deployment_config()
        ttl_hours = float(config.get("update_ttl_hours", 48))
        int(config.get("heartbeat_timeout_sec", 300))
        now = datetime.now(timezone.utc)
        node_health = {n["node_id"]: n for n in self.list_nodes()}
        eligible: list[dict[str, Any]] = []
        for row in self._load_all_updates():
            if row.get("model_name") != model_name:
                continue
            node_id = str(row.get("node_id", ""))
            node = node_health.get(node_id)
            if not node or node.get("stale"):
                continue
            ts = self._parse_ts(str(row.get("timestamp", now.isoformat())))
            if (now - ts).total_seconds() > ttl_hours * 3600:
                continue
            eligible.append(row)
        return eligible

    def receive_update(self, node_id: str, model_name: str,
                       weight_updates: dict[str, float],
                       performance_delta: float) -> FederatedModelUpdate:
        """Receive a model update from a federated node."""
        self.heartbeat(node_id)
        raw = f"{node_id}:{model_name}:{json.dumps(weight_updates, sort_keys=True)}"
        gradient_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]

        update = FederatedModelUpdate(
            update_id=f"fed.{uuid.uuid4().hex[:8]}",
            node_id=node_id,
            model_name=model_name,
            gradient_hash=gradient_hash,
            weight_updates=weight_updates,
            performance_delta=performance_delta,
        )
        with self._updates_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(update.__dict__, ensure_ascii=False) + "\n")
        logger.info("Federated update received from node %s for model %s (delta=%.4f)",
                   node_id, model_name, performance_delta)
        return update

    def aggregate_updates(self, model_name: str) -> dict[str, float]:
        """Aggregate weight updates from eligible nodes (FedAvg)."""
        updates = self._eligible_updates(model_name)
        if not updates:
            return {}

        all_keys: set[str] = set()
        for u in updates:
            all_keys.update(u.get("weight_updates", {}).keys())

        aggregated: dict[str, float] = {}
        for key in all_keys:
            values = [float(u["weight_updates"].get(key, 0)) for u in updates]
            aggregated[key] = round(sum(values) / len(values), 6)
        return aggregated

    def run_fedavg_round(self, model_name: str) -> FedAvgRoundResult:
        """Run FedAvg if minimum active nodes met; persist aggregated weights."""
        config = self.get_deployment_config()
        min_nodes = int(config.get("min_nodes_for_aggregate", 2))
        updates = self._eligible_updates(model_name)
        node_ids = {u.get("node_id") for u in updates}
        if len(node_ids) < min_nodes:
            return FedAvgRoundResult(
                ok=False,
                model_name=model_name,
                nodes_used=len(node_ids),
                message=f"need {min_nodes} nodes, got {len(node_ids)}",
            )
        weights = self.aggregate_updates(model_name)
        if not weights:
            return FedAvgRoundResult(ok=False, model_name=model_name, message="no eligible updates")
        out_path = self._models_dir / f"{model_name.replace('/', '_')}.json"
        out_path.write_text(
            json.dumps({"model_name": model_name, "weights": weights, "aggregated_at": datetime.now(timezone.utc).isoformat()}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return FedAvgRoundResult(
            ok=True,
            model_name=model_name,
            nodes_used=len(node_ids),
            weights=weights,
            message="fedavg_complete",
        )

    def get_aggregated_model(self, model_name: str) -> dict[str, Any] | None:
        """Load last FedAvg result for a model."""
        out_path = self._models_dir / f"{model_name.replace('/', '_')}.json"
        if not out_path.exists():
            return None
        return json.loads(out_path.read_text(encoding="utf-8"))


# ── RBAC (Role-Based Access Control) — ORM-backed ──────────────────


class RBACService:
    """Fine-grained role-based access control backed by SQLAlchemy.

    Roles are defined in the ``roles`` table with JSON permissions.
    User assignments live in ``user_role_assignments``.
    """

    # Default role definitions: role_id → {name, permissions}
    _DEFAULT_ROLES: dict[str, dict[str, Any]] = {
        "researcher": {
            "name": "研究员",
            "permissions": {
                "data": ["read"],
                "strategy": ["read", "write"],
                "factor": ["read", "write"],
                "order": ["read"],
                "account": [],
                "user": [],
            },
        },
        "trader": {
            "name": "交易员",
            "permissions": {
                "data": ["read"],
                "strategy": ["read"],
                "factor": ["read"],
                "order": ["read", "write", "execute"],
                "account": ["read"],
                "user": [],
            },
        },
        "risk_manager": {
            "name": "风控经理",
            "permissions": {
                "data": ["read"],
                "strategy": ["read"],
                "factor": ["read"],
                "order": ["read"],
                "account": ["read", "write"],
                "user": [],
            },
        },
        "compliance": {
            "name": "合规官",
            "permissions": {
                "data": ["read"],
                "strategy": ["read"],
                "factor": ["read"],
                "order": ["read"],
                "account": ["read"],
                "user": ["read"],
            },
        },
        "admin": {
            "name": "管理员",
            "permissions": {
                "data": ["read", "write", "execute"],
                "strategy": ["read", "write", "execute"],
                "factor": ["read", "write", "execute"],
                "order": ["read", "write", "execute"],
                "account": ["read", "write", "admin"],
                "user": ["read", "write", "admin"],
            },
        },
    }

    def __init__(self, session=None):
        self._session = session

    # ── Internal helpers ──────────────────────────────────────────

    def _get_session(self):
        if self._session is not None:
            return self._session
        # Lazy import to avoid circular dependency

        # Return None — caller must provide session
        return None

    @staticmethod
    def _register_default_roles(session) -> None:
        """Seed canonical role definitions (idempotent via code uniqueness)."""

        for role_id, info in RBACService._DEFAULT_ROLES.items():
            role = session.query(Role).filter_by(code=role_id).first()
            if role is None:
                role = Role(
                    code=role_id,
                    label=info["name"],
                    permissions_json=json.dumps(info["permissions"], ensure_ascii=False),
                )
                session.add(role)
        session.flush()

    # ── Public API ────────────────────────────────────────────────

    def assign_role(self, user_id: int, role_id: str, scope: str = "global",
                    assigned_by: int | None = None) -> dict[str, Any]:
        """Assign a role to a user."""
        session = self._get_session()
        if session is None:
            raise RuntimeError("RBACService requires a SQLAlchemy session")

        self._register_default_roles(session)

        role = session.query(Role).filter_by(code=role_id).first()
        if role is None:
            raise ValueError(f"Unknown role: {role_id}")


        assignment = session.query(UserRoleAssignment).filter_by(user_id=user_id).first()
        if assignment is None:
            assignment = UserRoleAssignment(
                user_id=user_id,
                role_id=role.id,
                scope=scope,
                assigned_by=assigned_by,
            )
            session.add(assignment)
        else:
            assignment.role_id = role.id
            assignment.scope = scope
            if assigned_by is not None:
                assignment.assigned_by = assigned_by

        session.flush()
        logger.info("User %d assigned role %s (scope=%s)", user_id, role_id, scope)
        return {
            "user_id": user_id,
            "role_id": role_id,
            "scope": scope,
        }

    def check_permission(self, user_id: int, resource: ResourceType,
                         permission: Permission) -> bool:
        """Check if a user has a specific permission."""
        session = self._get_session()
        if session is None:
            return True  # no session = legacy open access


        assignment = session.query(UserRoleAssignment).filter_by(user_id=user_id).first()
        if assignment is None:
            return True  # no assignment = legacy open access

        role = session.query(Role).filter_by(id=assignment.role_id).first()
        if role is None:
            return False

        perms = json.loads(role.permissions_json)
        resource_perms = perms.get(resource, [])
        return permission in resource_perms or "admin" in resource_perms

    def require_permission(self, user_id: int, resource: ResourceType,
                           permission: Permission) -> None:
        """Raise PermissionError if user lacks permission."""
        if not self.check_permission(user_id, resource, permission):
            raise PermissionError(
                f"User {user_id} lacks {permission} on {resource}"
            )

    def get_user_role(self, user_id: int) -> str | None:
        """Get the role name for a user."""
        session = self._get_session()
        if session is None:
            return None
        assignment = session.query(UserRoleAssignment).filter_by(user_id=user_id).first()
        if not assignment:
            return None
        role = session.query(Role).filter_by(id=assignment.role_id).first()
        return role.label if role else None

    def check_multi_resource(self, user_id: int,
                              resources: dict[str, str]) -> dict[str, bool]:
        """Check multiple resource permissions at once."""
        result = {}
        for resource, permission in resources.items():
            result[f"{resource}:{permission}"] = self.check_permission(user_id, resource, permission)
        return result

    def list_user_permissions(self, user_id: int) -> dict[str, list[str]]:
        """List all permissions for a user, grouped by resource."""
        session = self._get_session()
        if session is None:
            resources = ["data", "strategy", "factor", "order", "account", "user"]
            return {res: ["read", "write"] for res in resources}

        assignment = session.query(UserRoleAssignment).filter_by(user_id=user_id).first()
        if not assignment:
            return {}

        role = session.query(Role).filter_by(id=assignment.role_id).first()
        if not role:
            return {}

        perms = json.loads(role.permissions_json) if role.permissions_json else {}
        return perms

    def audit_change(self, changed_by: int, target_user: int,
                      action: str, detail: dict | None = None) -> dict:
        """Log a permission change for audit trail."""
        record = {
            "audit_id": f"perm.{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "changed_by": changed_by,
            "target_user": target_user,
            "action": action,
            "detail": detail or {},
        }
        log_path = Path(__file__).resolve().parents[4] / "instance" / "rbac_audit.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        logger.info("RBAC audit: %s by user %d on user %d", action, changed_by, target_user)
        return record

    def list_roles(self) -> list[dict]:
        """List all available roles with their permissions."""
        session = self._get_session()
        if session is None:
            return [
                {
                    "role_id": rid,
                    "name": info["name"],
                    "permissions": {k: v for k, v in info["permissions"].items() if v},
                }
                for rid, info in self._DEFAULT_ROLES.items()
            ]


        roles = session.query(Role).all()
        return [
            {
                "role_id": r.code,
                "name": r.label,
                "permissions": {
                    k: v for k, v in (
                        json.loads(r.permissions_json) if r.permissions_json else {}
                    ).items() if v
                },
            }
            for r in roles
        ]

    def get_user_assignment(self, user_id: int) -> dict[str, Any] | None:
        """Get role assignment for a user."""
        session = self._get_session()
        if session is None:
            return None


        assignment = session.query(UserRoleAssignment).filter_by(user_id=user_id).first()
        if not assignment:
            return None
        role = session.query(Role).filter_by(id=assignment.role_id).first()
        return {
            "user_id": user_id,
            "role_id": assignment.role_id,
            "role_name": role.label if role else assignment.role_id,
            "scope": assignment.scope,
        }
