"""Federated deployment service - federated learning and air-gapped deployment."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FederatedModelUpdate:
    """A model update from a federated node."""
    update_id: str
    node_id: str
    model_name: str
    gradient_hash: str
    weight_updates: dict[str, float]
    performance_delta: float
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class DeploymentNode:
    """A federated or air-gapped deployment node."""
    node_id: str
    name: str
    mode: str  # online / airgap / federated
    last_sync: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
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
        self._config_file.write_text(
            json.dumps(current, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return current

    def _parse_ts(self, ts: str) -> datetime:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))

    def _load_nodes_map(self) -> dict[str, DeploymentNode]:
        nodes: dict[str, DeploymentNode] = {}
        if not self._nodes_file.exists():
            return nodes
        with self._nodes_file.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                node = DeploymentNode(**data)
                nodes[node.node_id] = node
        return nodes

    def _write_nodes(self, nodes: dict[str, DeploymentNode]) -> None:
        _lines = [
            json.dumps(n.__dict__, ensure_ascii=False) for n in nodes.values()
        ]
        self._nodes_file.write_text(
            "\n".join(_lines) + ("\n" if _lines else ""),
            encoding="utf-8",
        )

    def export_model(
        self, model_name: str, export_format: str = "json"
    ) -> dict | None:
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
                json.dumps(
                    model.get("weights", {}), sort_keys=True
                ).encode("utf-8")
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
            json.dumps(
                {
                    "model_name": model_name,
                    "weights": weights,
                    "version": export_data.get("version", 1),
                    "num_nodes": export_data.get("num_nodes", 0),
                    "performance_metrics": export_data.get(
                        "performance_metrics", {}
                    ),
                    "imported_at": datetime.now(timezone.utc).isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        logger.info(
            "Model %s imported from air-gapped transfer (version=%s)",
            model_name,
            export_data.get("version", 1),
        )
        return True

    def register_node(
        self, node_id: str, name: str, mode: str = "federated"
    ) -> DeploymentNode:
        """Register or refresh a deployment node."""
        nodes = self._load_nodes_map()
        node = DeploymentNode(node_id=node_id, name=name, mode=mode)
        nodes[node_id] = node
        self._write_nodes(nodes)
        logger.info(
            "Deployment node registered: %s (%s, mode=%s)",
            node_id, name, mode,
        )
        return node

    def heartbeat(
        self,
        node_id: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> DeploymentNode | None:
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
        models = sorted({
            u.get("model_name", "") for u in updates if u.get("model_name")
        })
        return FederatedClusterStatus(
            total_nodes=len(nodes),
            active_nodes=active,
            stale_nodes=stale,
            pending_updates=len(updates),
            models_with_updates=models,
            config=self.get_deployment_config(),
        )

    def scan_cluster_health(
        self, *, mark_inactive: bool = True
    ) -> dict[str, Any]:
        """Scheduler hook: detect stale nodes and optionally mark inactive."""
        stale_ids = [
            n["node_id"] for n in self.list_nodes() if n.get("stale")
        ]
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
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows

    def _eligible_updates(self, model_name: str) -> list[dict[str, Any]]:
        """Updates from non-stale nodes within TTL window."""
        config = self.get_deployment_config()
        ttl_hours = float(config.get("update_ttl_hours", 48))
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

    def receive_update(
        self,
        node_id: str,
        model_name: str,
        weight_updates: dict[str, float],
        performance_delta: float,
    ) -> FederatedModelUpdate:
        """Receive a model update from a federated node."""
        self.heartbeat(node_id)
        raw = (
            f"{node_id}:{model_name}:"
            f"{json.dumps(weight_updates, sort_keys=True)}"
        )
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
            fh.write(
                json.dumps(update.__dict__, ensure_ascii=False) + "\n"
            )
        logger.info(
            "Federated update received from node %s for model %s (delta=%.4f)",
            node_id, model_name, performance_delta,
        )
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
            values = [
                float(u["weight_updates"].get(key, 0)) for u in updates
            ]
            aggregated[key] = round(sum(values) / len(values), 6)
        return aggregated

    def run_fedavg_round(self, model_name: str) -> FedAvgRoundResult:
        """Run FedAvg if minimum active nodes met; persist weights."""
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
            return FedAvgRoundResult(
                ok=False, model_name=model_name, message="no eligible updates"
            )
        out_path = (
            self._models_dir / f"{model_name.replace('/', '_')}.json"
        )
        out_path.write_text(
            json.dumps(
                {
                    "model_name": model_name,
                    "weights": weights,
                    "aggregated_at": datetime.now(timezone.utc).isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return FedAvgRoundResult(
            ok=True,
            model_name=model_name,
            nodes_used=len(node_ids),
            weights=weights,
            message="fedavg_complete",
        )

    def get_aggregated_model(
        self, model_name: str
    ) -> dict[str, Any] | None:
        """Load last FedAvg result for a model."""
        out_path = (
            self._models_dir / f"{model_name.replace('/', '_')}.json"
        )
        if not out_path.exists():
            return None
        return json.loads(out_path.read_text(encoding="utf-8"))
