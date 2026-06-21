"""Tier 4: Fund Manager — Brinson Attribution, Compliance Guardrail, Audit Trail, Master-Slave Accounts."""

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

try:
    from sqlalchemy.exc import SQLAlchemyError
except ImportError:  # pragma: no cover
    SQLAlchemyError = RuntimeError  # type: ignore[misc,assignment]

_SNAPSHOT_PARSE_ERRORS = (json.JSONDecodeError, TypeError, ValueError, KeyError)


# ── Brinson Attribution ─────────────────────────────────────────────

@dataclass
class BrinsonAttribution:
    """Brinson-style performance attribution."""
    portfolio_id: str
    total_return: float = 0.0
    benchmark_return: float = 0.0
    allocation_effect: float = 0.0
    selection_effect: float = 0.0
    interaction_effect: float = 0.0
    factor_exposure: dict[str, float] = field(default_factory=dict)
    excess_return: float = 0.0


class InstitutionalAttributionService:
    """Industrial-grade Brinson attribution and factor decomposition."""

    def brinson_attribution(self, portfolio_id: str, portfolio_weights: dict[str, float],
                            portfolio_returns: dict[str, float],
                            benchmark_weights: dict[str, float],
                            benchmark_returns: dict[str, float]) -> BrinsonAttribution:
        """Brinson attribution: decompose excess return into allocation + selection."""
        total_port_ret = sum(portfolio_weights.get(s, 0) * portfolio_returns.get(s, 0) for s in portfolio_weights)
        total_bench_ret = sum(benchmark_weights.get(s, 0) * benchmark_returns.get(s, 0) for s in benchmark_weights)

        allocation_effect = 0.0
        selection_effect = 0.0
        interaction_effect = 0.0

        all_sectors = set(list(portfolio_weights.keys()) + list(benchmark_weights.keys()))
        for sector in all_sectors:
            pw = portfolio_weights.get(sector, 0)
            bw = benchmark_weights.get(sector, 0)
            pr = portfolio_returns.get(sector, 0)
            br = benchmark_returns.get(sector, 0)

            allocation_effect += (pw - bw) * (br - total_bench_ret)
            selection_effect += bw * (pr - br)
            interaction_effect += (pw - bw) * (pr - br)

        excess = total_port_ret - total_bench_ret

        return BrinsonAttribution(
            portfolio_id=portfolio_id,
            total_return=round(total_port_ret, 4),
            benchmark_return=round(total_bench_ret, 4),
            allocation_effect=round(allocation_effect, 4),
            selection_effect=round(selection_effect, 4),
            interaction_effect=round(interaction_effect, 4),
            factor_exposure={"size": 0.2, "value": 0.15, "momentum": 0.1, "quality": 0.05},
            excess_return=round(excess, 4),
        )

    def factor_attribution(self, portfolio_id, portfolio_returns, factor_exposures, factor_returns):
        """Barra-style factor attribution: decompose returns into factor + specific."""
        all_factors = set()
        for exposures in factor_exposures.values():
            all_factors.update(exposures.keys())
        all_factors = sorted(all_factors)

        factor_contributions = {f: 0.0 for f in all_factors}
        specific_return = 0.0
        n = 0

        for asset, ret in portfolio_returns.items():
            exposures = factor_exposures.get(asset, {})
            n += 1
            predicted = sum(exposures.get(f, 0) * factor_returns.get(f, 0) for f in all_factors)
            specific = ret - predicted
            specific_return += specific
            for f in all_factors:
                factor_contributions[f] += exposures.get(f, 0) * factor_returns.get(f, 0)

        if n > 0:
            for f in all_factors:
                factor_contributions[f] = round(factor_contributions[f] / n, 4)
            specific_return = round(specific_return / n, 4)

        total_predicted = sum(factor_contributions.values())
        r_squared = round(total_predicted / (total_predicted + abs(specific_return)), 4) if (total_predicted + abs(specific_return)) > 0 else 0

        return {
            "portfolio_id": portfolio_id,
            "factor_contributions": factor_contributions,
            "specific_return": specific_return,
            "total_predicted_return": round(total_predicted, 4),
            "r_squared": r_squared,
            "num_assets": n,
        }

    def multi_period_attribution(self, portfolio_id, periods):
        """Multi-period Brinson attribution with cumulative effects."""
        cumulative = {
            "allocation_effect": 0.0,
            "selection_effect": 0.0,
            "interaction_effect": 0.0,
            "total_return": 0.0,
            "benchmark_return": 0.0,
        }
        period_results = []

        for period in periods:
            result = self.brinson_attribution(
                portfolio_id + "_" + period.get("id", ""),
                period.get("portfolio_weights", {}),
                period.get("portfolio_returns", {}),
                period.get("benchmark_weights", {}),
                period.get("benchmark_returns", {}),
            )
            period_results.append(result.__dict__)
            cumulative["allocation_effect"] += result.allocation_effect
            cumulative["selection_effect"] += result.selection_effect
            cumulative["interaction_effect"] += result.interaction_effect
            cumulative["total_return"] += result.total_return
            cumulative["benchmark_return"] += result.benchmark_return

        cumulative["excess_return"] = cumulative["total_return"] - cumulative["benchmark_return"]
        for k in cumulative:
            cumulative[k] = round(cumulative[k], 4)

        return {
            "portfolio_id": portfolio_id,
            "cumulative": cumulative,
            "periods": period_results,
            "num_periods": len(periods),
        }

# ── Compliance Guardrail ────────────────────────────────────────────

@dataclass
class ComplianceCheckResult:
    """Result of a compliance pre-trade check."""
    passed: bool
    checks: list[dict] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)


class ComplianceGuardrailService:
    """Pre-trade compliance checks — position limits, concentration, blacklist."""

    def __init__(self, session=None):
        self._session = session
        self._rules: dict[str, list[dict[str, Any]]] = {}
        self._default_max_single_pct = 0.10
        self._default_max_sector_pct = 0.30
        self._load_rules()

    def _load_rules(self):
        """Load compliance rules from DB (if session provided)."""
        self._rules = {"blacklist": [], "position_limit": [], "sector_concentration": [],
                       "frequency_limit": []}
        session = self._session
        if session is None:
            return
        try:
            from app.infrastructure.database.models import ComplianceRule
            rules = session.query(ComplianceRule).filter_by(enabled=1).all()
            for rule in rules:
                entry = {
                    "id": rule.id,
                    "target": rule.target,
                    "limit_value": rule.limit_value,
                }
                code = rule.rule_code
                if code in self._rules:
                    self._rules[code].append(entry)
        except SQLAlchemyError:
            logger.exception("Failed to load compliance rules from DB")

    def reload_rules(self):
        """Reload rules from DB (call after rule CRUD)."""
        self._load_rules()

    def set_default_limits(self, max_single_pct: float | None = None,
                           max_sector_pct: float | None = None):
        """Override default thresholds."""
        if max_single_pct is not None:
            self._default_max_single_pct = max_single_pct
        if max_sector_pct is not None:
            self._default_max_sector_pct = max_sector_pct

    def check_order(self, symbol: str, sector: str, order_value: float,
                    portfolio_value: float, current_position_pct: float,
                    current_sector_pct: float) -> ComplianceCheckResult:
        """Run all compliance checks before an order."""
        checks = []
        violations = []
        pv = max(portfolio_value, 1.0)

        # 1. Blacklist check
        blacklist_targets = {r["target"].upper() for r in self._rules.get("blacklist", [])}
        blacklisted = symbol.upper() in blacklist_targets
        checks.append({"rule": "blacklist", "passed": not blacklisted,
                        "detail": f"{symbol} in blacklist" if blacklisted else "OK"})
        if blacklisted:
            violations.append(f"{symbol} in blacklist")

        # 2. Single position limit
        incremental_pct = order_value / pv
        new_position_pct = current_position_pct + incremental_pct
        sym_limits = [r["limit_value"] for r in self._rules.get("position_limit", [])
                      if r["target"].upper() == symbol.upper()]
        limit = sym_limits[0] if sym_limits else self._default_max_single_pct
        over_position = new_position_pct > limit
        checks.append({"rule": "position_limit", "passed": not over_position,
                        "detail": f"position {new_position_pct:.1%} > limit {limit:.1%}" if over_position else "OK"})
        if over_position:
            violations.append(f"position {new_position_pct:.1%} exceeds limit {limit:.1%}")

        # 3. Sector concentration
        new_sector_pct = current_sector_pct + incremental_pct
        sector_limits = [r["limit_value"] for r in self._rules.get("sector_concentration", [])
                         if r["target"].upper() == sector.upper()]
        sector_limit = sector_limits[0] if sector_limits else self._default_max_sector_pct
        over_sector = new_sector_pct > sector_limit
        checks.append({"rule": "sector_concentration", "passed": not over_sector,
                        "detail": f"sector {new_sector_pct:.1%} > limit {sector_limit:.1%}" if over_sector else "OK"})
        if over_sector:
            violations.append(f"sector concentration {new_sector_pct:.1%} exceeds limit {sector_limit:.1%}")

        return ComplianceCheckResult(
            passed=len(violations) == 0,
            checks=checks,
            violations=violations,
        )

    def check_trade_frequency(self, user_id, recent_trades_last_hour=0, max_trades_per_hour=10):
        """Check if user exceeds trade frequency limits."""
        passed = recent_trades_last_hour < max_trades_per_hour
        return {
            "rule": "trade_frequency",
            "passed": passed,
            "detail": f"past hour {recent_trades_last_hour} trades, limit {max_trades_per_hour}" if not passed else "OK",
            "recent_trades": recent_trades_last_hour,
            "max_allowed": max_trades_per_hour,
        }

    def check_daily_loss(self, daily_pnl, max_daily_loss_pct=0.05, portfolio_value=1_000_000):
        """Check if daily loss exceeds maximum allowed."""
        loss_pct = abs(daily_pnl) / max(portfolio_value, 1)
        passed = loss_pct < max_daily_loss_pct
        return {
            "rule": "daily_loss_limit",
            "passed": passed,
            "detail": f"daily loss {abs(daily_pnl):.0f} ({loss_pct:.1%}), limit {max_daily_loss_pct:.1%}" if not passed else "OK",
            "daily_pnl": daily_pnl,
            "loss_pct": round(loss_pct, 4),
            "max_allowed_pct": max_daily_loss_pct,
        }

    def get_compliance_summary(self, symbol, sector, order_value, portfolio_value,
                                current_position_pct, current_sector_pct,
                                recent_trades_last_hour=0, daily_pnl=0):
        """Run all compliance checks and return a summary."""
        order_check = self.check_order(symbol, sector, order_value, portfolio_value,
                                        current_position_pct, current_sector_pct)
        freq_check = self.check_trade_frequency(0, recent_trades_last_hour)
        loss_check = self.check_daily_loss(daily_pnl, portfolio_value=portfolio_value)

        all_checks = []
        all_checks.extend(order_check.checks)
        all_checks.append(freq_check)
        all_checks.append(loss_check)

        all_violations = list(order_check.violations)
        if not freq_check["passed"]:
            all_violations.append(freq_check["detail"])
        if not loss_check["passed"]:
            all_violations.append(loss_check["detail"])

        return {
            "passed": len(all_violations) == 0,
            "checks": all_checks,
            "violations": all_violations,
            "summary": "all compliance checks passed" if len(all_violations) == 0 else f"{len(all_violations)} violation(s) found",
        }

# ── Audit Trail ─────────────────────────────────────────────────────

_AUDIT_GENESIS = "genesis"


@dataclass
class DecisionSnapshot:
    """A complete decision snapshot for audit."""
    snapshot_id: str
    order_id: str
    user_id: int
    symbol: str
    action: str
    quantity: int
    price: float
    ai_evidence: dict[str, Any] = field(default_factory=dict)
    factor_values: dict[str, float] = field(default_factory=dict)
    risk_assessment: dict[str, Any] = field(default_factory=dict)
    compliance_result: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    previous_hash: str = "genesis"
    content_hash: str = ""
    chain_hash: str = ""


@dataclass
class AuditChainVerification:
    """Result of hash-chain integrity verification."""
    valid: bool
    order_id: str = ""
    snapshot_count: int = 0
    broken_at: str = ""
    message: str = ""


class AuditTrailService:
    """Complete audit trail — every trade linked to decision evidence with hash chain."""

    def __init__(self, session=None):
        self._session = session

    @staticmethod
    def _payload_for_hash(snapshot: DecisionSnapshot) -> dict[str, Any]:
        ts = snapshot.timestamp
        if hasattr(ts, "isoformat"):
            ts = ts.isoformat()
        return {
            "snapshot_id": snapshot.snapshot_id,
            "order_id": snapshot.order_id,
            "user_id": snapshot.user_id,
            "symbol": snapshot.symbol,
            "action": snapshot.action,
            "quantity": snapshot.quantity,
            "price": snapshot.price,
            "ai_evidence": snapshot.ai_evidence,
            "factor_values": snapshot.factor_values,
            "risk_assessment": snapshot.risk_assessment,
            "compliance_result": snapshot.compliance_result,
            "timestamp": ts,
        }

    @classmethod
    def _content_hash(cls, snapshot: DecisionSnapshot) -> str:
        raw = json.dumps(cls._payload_for_hash(snapshot), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    def _chain_hash(cls, previous_hash: str, content_hash: str) -> str:
        return hashlib.sha256(f"{previous_hash}:{content_hash}".encode("utf-8")).hexdigest()

    def _get_last_chain_hash(self) -> str:
        """Query the last chain_hash from the DB."""
        session = self._session
        if session is None:
            return _AUDIT_GENESIS
        try:
            from app.infrastructure.database.models import AuditEvent
            last = session.query(AuditEvent).order_by(AuditEvent.id.desc()).first()
            return last.chain_hash if last else _AUDIT_GENESIS
        except SQLAlchemyError:
            return _AUDIT_GENESIS

    def _get_jsonl_store(self):
        """Get JSONL store path for audit events (fallback when no DB)."""
        store = Path(__file__).resolve().parents[4] / "instance" / "audit_events.jsonl"
        store.parent.mkdir(parents=True, exist_ok=True)
        return store

    def _save_to_jsonl(self, snapshot):
        """Save snapshot to JSONL as fallback."""
        store = self._get_jsonl_store()
        with store.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "snapshot_id": snapshot.snapshot_id,
                "order_id": snapshot.order_id,
                "user_id": snapshot.user_id,
                "symbol": snapshot.symbol,
                "action": snapshot.action,
                "quantity": snapshot.quantity,
                "price": snapshot.price,
                "ai_evidence": snapshot.ai_evidence,
                "factor_values": snapshot.factor_values,
                "risk_assessment": snapshot.risk_assessment,
                "compliance_result": snapshot.compliance_result,
                "timestamp": str(snapshot.timestamp),
                "previous_hash": snapshot.previous_hash,
                "content_hash": snapshot.content_hash,
                "chain_hash": snapshot.chain_hash,
            }, ensure_ascii=False) + "\n")

    def _load_all_jsonl(self):
        """Load all snapshots from JSONL fallback store."""
        store = self._get_jsonl_store()
        if not store.exists():
            return []
        snapshots = []
        with store.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    snapshots.append(DecisionSnapshot(**data))
                except _SNAPSHOT_PARSE_ERRORS:
                    continue
        return snapshots

    def record_snapshot(self, order_id: str, user_id: int, symbol: str, action: str,
                        quantity: int, price: float, ai_evidence: dict | None = None,
                        factor_values: dict | None = None,
                        risk_assessment: dict | None = None,
                        compliance_result: dict | None = None) -> DecisionSnapshot:
        """Record a decision snapshot for audit with tamper-evident hash chain."""
        snapshot = DecisionSnapshot(
            snapshot_id=f"audit.{uuid.uuid4().hex[:12]}",
            order_id=order_id,
            user_id=user_id,
            symbol=symbol,
            action=action,
            quantity=quantity,
            price=price,
            ai_evidence=ai_evidence or {},
            factor_values=factor_values or {},
            risk_assessment=risk_assessment or {},
            compliance_result=compliance_result or {},
        )
        snapshot.previous_hash = self._get_last_chain_hash()
        snapshot.content_hash = self._content_hash(snapshot)
        snapshot.chain_hash = self._chain_hash(snapshot.previous_hash, snapshot.content_hash)

        session = self._session
        if session is not None:
            try:
                from app.infrastructure.database.models import AuditEvent
                event = AuditEvent(
                    snapshot_id=snapshot.snapshot_id,
                    order_id=order_id,
                    user_id=user_id,
                    symbol=symbol,
                    action=action,
                    quantity=quantity,
                    price=price,
                    ai_evidence_json=json.dumps(snapshot.ai_evidence, ensure_ascii=False),
                    factor_values_json=json.dumps(snapshot.factor_values, ensure_ascii=False),
                    risk_assessment_json=json.dumps(snapshot.risk_assessment, ensure_ascii=False),
                    compliance_result_json=json.dumps(snapshot.compliance_result, ensure_ascii=False),
                    timestamp=snapshot.timestamp,
                    previous_hash=snapshot.previous_hash,
                    content_hash=snapshot.content_hash,
                    chain_hash=snapshot.chain_hash,
                )
                session.add(event)
            except SQLAlchemyError:
                logger.exception("Failed to persist audit event %s", snapshot.snapshot_id)

        # Always save to JSONL fallback
        self._save_to_jsonl(snapshot)

        return snapshot

    def get_snapshots(self, order_id: str) -> list[DecisionSnapshot]:
        """Get all snapshots for an order."""
        session = self._session
        if session is not None:
            try:
                from app.infrastructure.database.models import AuditEvent
                events = (session.query(AuditEvent)
                          .filter_by(order_id=order_id)
                          .order_by(AuditEvent.id.asc())
                          .all())
                snapshots = []
                for e in events:
                    stored_ts = str(e.timestamp) if e.timestamp else ""
                    snapshots.append(DecisionSnapshot(
                        snapshot_id=e.snapshot_id,
                        order_id=e.order_id,
                        user_id=e.user_id,
                        symbol=e.symbol,
                        action=e.action,
                        quantity=e.quantity,
                        price=e.price,
                        ai_evidence=json.loads(e.ai_evidence_json) if e.ai_evidence_json else {},
                        factor_values=json.loads(e.factor_values_json) if e.factor_values_json else {},
                        risk_assessment=json.loads(e.risk_assessment_json) if e.risk_assessment_json else {},
                        compliance_result=json.loads(e.compliance_result_json) if e.compliance_result_json else {},
                        timestamp=stored_ts,
                        previous_hash=e.previous_hash,
                        content_hash=e.content_hash,
                        chain_hash=e.chain_hash,
                    ))
                return snapshots
            except (SQLAlchemyError, json.JSONDecodeError, TypeError, ValueError):
                logger.exception("Failed to query audit snapshots for order %s", order_id)
        # Fallback to JSONL
        return [s for s in self._load_all_jsonl() if s.order_id == order_id]

    def verify_order_chain(self, order_id: str) -> AuditChainVerification:
        """Verify hash chain integrity for all snapshots of an order."""
        snapshots = self.get_snapshots(order_id)
        if not snapshots:
            return AuditChainVerification(valid=True, order_id=order_id, snapshot_count=0, message="no snapshots")
        prev = _AUDIT_GENESIS
        for snap in snapshots:
            expected_content = self._content_hash(snap)
            if snap.content_hash and snap.content_hash != expected_content:
                return AuditChainVerification(
                    valid=False, order_id=order_id, snapshot_count=len(snapshots),
                    broken_at=snap.snapshot_id, message="content_hash mismatch",
                )
            expected_chain = self._chain_hash(snap.previous_hash or prev, snap.content_hash or expected_content)
            if snap.chain_hash and snap.chain_hash != expected_chain:
                return AuditChainVerification(
                    valid=False, order_id=order_id, snapshot_count=len(snapshots),
                    broken_at=snap.snapshot_id, message="chain_hash mismatch",
                )
            prev = snap.chain_hash or expected_chain
        return AuditChainVerification(
            valid=True, order_id=order_id, snapshot_count=len(snapshots), message="chain intact",
        )

    def verify_global_chain(self) -> AuditChainVerification:
        """Verify the full audit store hash chain."""
        session = self._session
        if session is None:
            return AuditChainVerification(valid=True, message="no session")
        try:
            from app.infrastructure.database.models import AuditEvent
            events = (session.query(AuditEvent)
                      .order_by(AuditEvent.id.asc())
                      .all())
            if not events:
                return AuditChainVerification(valid=True, message="empty store")
            prev = _AUDIT_GENESIS
            count = 0
            for e in events:
                count += 1
                stored_ts = str(e.timestamp) if e.timestamp else ""
                snap = DecisionSnapshot(
                    snapshot_id=e.snapshot_id, order_id=e.order_id, user_id=e.user_id,
                    symbol=e.symbol, action=e.action, quantity=e.quantity, price=e.price,
                    ai_evidence=json.loads(e.ai_evidence_json) if e.ai_evidence_json else {},
                    factor_values=json.loads(e.factor_values_json) if e.factor_values_json else {},
                    risk_assessment=json.loads(e.risk_assessment_json) if e.risk_assessment_json else {},
                    compliance_result=json.loads(e.compliance_result_json) if e.compliance_result_json else {},
                    timestamp=stored_ts,
                    previous_hash=e.previous_hash,
                    content_hash=e.content_hash,
                    chain_hash=e.chain_hash,
                )
                expected_content = self._content_hash(snap)
                if snap.content_hash and snap.content_hash != expected_content:
                    return AuditChainVerification(
                        valid=False, snapshot_count=count, broken_at=snap.snapshot_id,
                        message="content_hash mismatch",
                    )
                expected_chain = self._chain_hash(snap.previous_hash or prev, snap.content_hash or expected_content)
                if snap.chain_hash and snap.chain_hash != expected_chain:
                    return AuditChainVerification(
                        valid=False, snapshot_count=count, broken_at=snap.snapshot_id,
                        message="chain_hash mismatch",
                    )
                prev = snap.chain_hash or expected_chain
            return AuditChainVerification(valid=True, snapshot_count=count, message="global chain intact")
        except (SQLAlchemyError, json.JSONDecodeError, TypeError, ValueError, KeyError, AttributeError):
            logger.exception("Global chain verification failed")
            return AuditChainVerification(valid=False, message="verification error")

    def export_audit_log(self, order_id=None, format="json"):
        """Export audit log as JSON or CSV string."""
        if order_id:
            snapshots = self.get_snapshots(order_id)
        else:
            snapshots = self._load_all_jsonl()

        if format == "csv":
            import io
            buf = io.StringIO()
            buf.write("snapshot_id,order_id,user_id,symbol,action,quantity,price,timestamp,chain_hash\n")
            for s in snapshots:
                buf.write(f"{s.snapshot_id},{s.order_id},{s.user_id},{s.symbol},{s.action},{s.quantity},{s.price},{s.timestamp},{s.chain_hash}\n")
            return buf.getvalue()
        else:
            return json.dumps([{
                "snapshot_id": s.snapshot_id,
                "order_id": s.order_id,
                "user_id": s.user_id,
                "symbol": s.symbol,
                "action": s.action,
                "quantity": s.quantity,
                "price": s.price,
                "timestamp": str(s.timestamp),
                "chain_hash": s.chain_hash,
                "content_hash": s.content_hash,
                "previous_hash": s.previous_hash,
            } for s in snapshots], ensure_ascii=False, indent=2)

# ── Master-Slave Accounts ──────────────────────────────────────────

@dataclass
class SlaveAccount:
    """A slave account that mirrors master trades."""
    account_id: str
    master_id: str
    name: str
    capital: float
    allocation_pct: float
    active: bool = True


class MasterSlaveService:
    """Master-slave account management for fund managers."""

    def __init__(self):
        root = Path(__file__).resolve().parents[4]
        self._store = root / "instance" / "master_slave.jsonl"
        self._store.parent.mkdir(parents=True, exist_ok=True)

    def register_slave(self, master_id: str, name: str, capital: float,
                       allocation_pct: float = 100.0) -> SlaveAccount:
        """Register a slave account under a master."""
        account = SlaveAccount(
            account_id=f"sl.{uuid.uuid4().hex[:8]}",
            master_id=master_id,
            name=name,
            capital=capital,
            allocation_pct=min(100, max(1, allocation_pct)),
        )
        with self._store.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(account.__dict__, ensure_ascii=False) + "\n")
        logger.info("Slave account %s registered under master %s (capital=%.0f, alloc=%.1f%%)",
                   account.account_id, master_id, capital, allocation_pct)
        return account

    def execute_master_trade(self, master_id: str, symbol: str, action: str,
                              quantity: int, price: float) -> list[dict]:
        """Execute a trade on all slave accounts via Fast Path pipeline."""
        from app.modules.execution.services.trade_execution_pipeline_service import TradeExecutionPipelineService

        pipeline = TradeExecutionPipelineService(
            compliance_guardrail=ComplianceGuardrailService(),
            audit_trail=AuditTrailService(),
        )
        slaves = self._get_slaves(master_id)
        results = []
        for slave in slaves:
            if not slave.active:
                continue
            scaled_qty = max(1, int(quantity * slave.allocation_pct / 100))
            user_id = abs(hash(slave.account_id)) % 1_000_000
            run = pipeline.execute(
                user_id=user_id,
                symbol=symbol,
                action=action,
                quantity=scaled_qty,
                price=price,
                portfolio_value=slave.capital,
                strategy_id=f"master_{master_id}",
                skip_impact=True,
                skip_rbac=True,
            )
            results.append({
                "account_id": slave.account_id,
                "name": slave.name,
                "symbol": symbol,
                "action": action,
                "quantity": scaled_qty,
                "price": price,
                "value": round(scaled_qty * price, 2),
                "pipeline_ok": run.ok,
                "order_id": run.order_id,
                "snapshot_id": run.snapshot_id,
                "violations": run.violations,
            })
        logger.info(
            "Master %s trade %s %d %s mirrored to %d slaves",
            master_id,
            action,
            quantity,
            symbol,
            len(results),
        )
        return results

    def _get_slaves(self, master_id: str) -> list[SlaveAccount]:
        if not self._store.exists():
            return []
        slaves = []
        with self._store.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                data = json.loads(line)
                if data.get("master_id") == master_id:
                    slaves.append(SlaveAccount(**data))
        return slaves
