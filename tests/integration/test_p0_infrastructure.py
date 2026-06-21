"""Integration tests for P0 infrastructure — end-to-end pipeline with DB session."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..")))

os.environ.setdefault("STRICT_BOOTSTRAP", "0")
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret-integration-key-abc")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


class TestPipelineWithSession:
    """Test TradeExecutionPipelineService with a real DB session (SQLite)."""

    def _create_test_session(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_engine("sqlite:///:memory:")
        from app.infrastructure.database.orm import Base, bootstrap_schema
        bootstrap_schema(engine)
        Session = sessionmaker(bind=engine)
        return Session()

    def test_full_pipeline_pass(self):
        from app.modules.execution.services.trade_execution_pipeline_service import (
            TradeExecutionPipelineService,
        )
        from app.modules.portfolio_risk.services.fund_tier_service import (
            ComplianceGuardrailService,
            AuditTrailService,
        )
        from app.core.key_encryption import KeyEncryptionService

        session = self._create_test_session()
        audit_service = AuditTrailService(session=session)
        compliance_service = ComplianceGuardrailService(session=session)

        # Seed a default admin role so RBAC allows execution
        from app.infrastructure.database.models import Role
        admin_role = session.query(Role).filter_by(code="admin").first()
        if admin_role is None:
            admin_role = Role(code="admin", label="管理员", permissions_json="{}")
            session.add(admin_role)
            session.flush()

        # Give user 1 the admin role
        from app.infrastructure.database.models import UserRoleAssignment
        ua = UserRoleAssignment(user_id=1, role_id=admin_role.id)
        session.add(ua)
        session.flush()

        kms = KeyEncryptionService(secret_key="integration-test-key")
        pipeline = TradeExecutionPipelineService(
            compliance_guardrail=compliance_service,
            audit_trail=audit_service,
            compliance_session=session,
            audit_session=session,
        )

        result = pipeline.execute(
            user_id=1,
            symbol="600519",
            action="buy",
            quantity=100,
            price=1750.0,
            portfolio_value=10_000_000.0,
        )
        assert result.ok is True, f"Pipeline failed: {result.violations}"
        assert result.order_id
        assert result.snapshot_id

    def test_compliance_blocks_blacklist(self):
        from app.modules.execution.services.trade_execution_pipeline_service import (
            TradeExecutionPipelineService,
        )
        from app.modules.portfolio_risk.services.fund_tier_service import (
            ComplianceGuardrailService,
            AuditTrailService,
        )

        session = self._create_test_session()
        audit_service = AuditTrailService(session=session)
        compliance_service = ComplianceGuardrailService(session=session)

        # Add blacklist rule
        from app.infrastructure.database.models import ComplianceRule
        rule = ComplianceRule(
            rule_code="blacklist",
            rule_type="global",
            target="600519",
            limit_value=1.0,
            enabled=1,
        )
        session.add(rule)
        session.flush()

        # Reload guardrail to pick up the new rule
        compliance_service.reload_rules()

        pipeline = TradeExecutionPipelineService(
            compliance_guardrail=compliance_service,
            audit_trail=audit_service,
            compliance_session=session,
            audit_session=session,
        )

        result = pipeline.execute(
            user_id=1,
            symbol="600519",
            action="buy",
            quantity=100,
            price=1750.0,
        )
        assert result.ok is False
        assert result.stage == "compliance"
        assert any("禁买" in v for v in result.violations)

    def test_audit_chain_in_db(self):
        from app.modules.portfolio_risk.services.fund_tier_service import (
            AuditTrailService,
        )

        session = self._create_test_session()
        service = AuditTrailService(session=session)

        snap = service.record_snapshot(
            order_id="ord.chain-test",
            user_id=1,
            symbol="600519",
            action="buy",
            quantity=100,
            price=1750.0,
        )
        session.commit()

        # Verify it's in the DB
        from app.infrastructure.database.models import AuditEvent
        event = session.query(AuditEvent).filter_by(snapshot_id=snap.snapshot_id).first()
        assert event is not None
        assert event.content_hash == snap.content_hash
        assert event.chain_hash == snap.chain_hash

        # Verify hash chain — reconstruct snapshot using stored timestamp string
        import json
        from app.modules.portfolio_risk.services.fund_tier_service import DecisionSnapshot
        snap2 = DecisionSnapshot(
            snapshot_id=event.snapshot_id, order_id=event.order_id, user_id=event.user_id,
            symbol=event.symbol, action=event.action, quantity=event.quantity, price=event.price,
            ai_evidence=json.loads(event.ai_evidence_json) if event.ai_evidence_json else {},
            factor_values=json.loads(event.factor_values_json) if event.factor_values_json else {},
            risk_assessment=json.loads(event.risk_assessment_json) if event.risk_assessment_json else {},
            compliance_result=json.loads(event.compliance_result_json) if event.compliance_result_json else {},
            timestamp=str(event.timestamp) if event.timestamp else "",
            previous_hash=event.previous_hash,
            content_hash=event.content_hash,
            chain_hash=event.chain_hash,
        )
        # Verify content hash matches when read back
        h2 = AuditTrailService._content_hash(snap2)
        assert h2 == snap.content_hash, f"Mismatch: {h2} != {snap.content_hash}"

        # Verify hash chain
        verify = service.verify_order_chain("ord.chain-test")
        assert verify.valid is True
        assert verify.snapshot_count == 1


class TestKeyEncryptionIntegration:
    """End-to-end key encryption with a real Fernet key."""

    def test_gateway_key_flow(self):
        from app.modules.system.services.key_management_service import KeyManagementService
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_engine("sqlite:///:memory:")
        from app.infrastructure.database.orm import Base, bootstrap_schema
        bootstrap_schema(engine)
        Session = sessionmaker(bind=engine)
        session = Session()

        kms = KeyManagementService(session=session)
        kms.set_gateway_key("test-gateway", "sk-actual-api-key-12345")
        session.commit()

        retrieved = kms.get_gateway_key("test-gateway")
        assert retrieved == "sk-actual-api-key-12345"

        # List gateways should not expose keys
        gateways = kms.list_gateways()
        assert len(gateways) == 1
        assert gateways[0]["gateway_name"] == "test-gateway"
        assert "api_key" not in gateways[0]
