"""Enhance Institution Tier Service with Phase C capabilities."""
import hashlib
import json
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


# ============================================================
# NEW CODE FRAGMENTS TO INJECT
# ============================================================

ALMGREN_CHRISS_CODE = '''
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

'''

ADAPTIVE_ALGO_CODE = '''
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

'''

FEDERATED_EXPORT_CODE = '''
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
        self._models[model_name] = {
            "weights": weights,
            "version": export_data.get("version", 1),
            "num_nodes": export_data.get("num_nodes", 0),
            "performance_metrics": export_data.get("performance_metrics", {}),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._store.open("w", encoding="utf-8") as fh:
            json.dump(self._models, fh, ensure_ascii=False, indent=2)
        logger.info("Model %s imported from air-gapped transfer (version=%s)",
                   model_name, export_data.get("version", 1))
        return True

'''

RBAC_ENHANCE_CODE = '''
    def check_multi_resource(self, user_id: int,
                              resources: dict[str, str]) -> dict[str, bool]:
        """Check multiple resource permissions at once."""
        result = {}
        from typing import get_args
        for resource, permission in resources.items():
            result[f"{resource}:{permission}"] = self.check_permission(user_id, resource, permission)
        return result

    def list_user_permissions(self, user_id: int) -> dict[str, list[str]]:
        """List all permissions for a user, grouped by resource."""
        from app.infrastructure.database.models import UserRoleAssignment, Role
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

'''

# ============================================================
# MAIN: read, slot, write
# ============================================================

TARGET = r'E:\project\workspace\myrepo\quant-atlas\app\modules\system\services\institution_tier_service.py'

with open(TARGET, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Locate insertion points (0-indexed)
insertions = []

for i, line in enumerate(lines):
    s = line.strip()

    # (1) After MarketImpactModelService.forecast() — insert Almgren-Chriss + multi-asset
    #    The class ends at line 76 (ImpactForecast dataclass is before)
    if s == '        )' and i > 65 and i < 80:
        # Check if next line starts next section
        next_line = lines[i+1].strip() if i+1 < len(lines) else ''
        if next_line.startswith('# '):
            print(f'Found forecast() return: line {i+1}, inserting Almgren-Chriss after')
            insertions.append((i + 1, ALMGREN_CHRISS_CODE))

    # (2) After AdvancedExecutionAlgoService.generate_iceberg() — insert adaptive + shortfall
    if s == "        ]" and i > 240 and i < 260:
        prev_line = lines[i-1].strip() if i > 0 else ''
        prev_prev = lines[i-2].strip() if i > 1 else ''
        # Check if we're at the end of generate_iceberg (the last method before next section)
        next_line = lines[i+1].strip() if i+1 < len(lines) else ''
        if next_line.startswith('#'):
            print(f'Found iceberg() end: line {i+1}, inserting adaptive algo after')
            insertions.append((i + 1, ADAPTIVE_ALGO_CODE))

    # (3) After FederatedDeploymentService.get_aggregated_model() — insert export/import
    if s == '        return self._models.get(model_name)' and i > 330 and i < 360:
        next_line = lines[i+1].strip() if i+1 < len(lines) else ''
        if next_line.startswith('#'):
            print(f'Found get_aggregated_model: line {i+1}, inserting export/import after')
            insertions.append((i + 1, FEDERATED_EXPORT_CODE))

    # (4) After RBACService.get_user_assignment() — insert multi-resource + list + audit
    if 'get_user_assignment' in s and 'def' in s:
        print(f'Found get_user_assignment def: line {i+1}')
    if s == '        }' and i > 745 and i < 770:
        print(f'Found RBAC end brace: line {i+1}')

if not insertions:
    print('No insertion points found by heuristic — using known line numbers')
    # Fallback: known line numbers from the original 766-line file
    insertions = [
        (77, ALMGREN_CHRISS_CODE),
        (249, ADAPTIVE_ALGO_CODE),
        (339, FEDERATED_EXPORT_CODE),
        (710, RBAC_ENHANCE_CODE),
    ]

# Apply in reverse order
insertions.sort(key=lambda x: x[0], reverse=True)
for ins_line, code in insertions:
    lines[ins_line:ins_line] = code

with open(TARGET, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f'Written: {len(lines)} lines')
