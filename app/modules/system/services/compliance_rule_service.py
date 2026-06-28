"""Compliance rule CRUD service — manage compliance_rules table."""

from __future__ import annotations

from datetime import datetime

from app.core.logger import get_logger
from app.modules.portfolio_risk.services.fund_tier_service import ComplianceGuardrailService

logger = get_logger(__name__)


class ComplianceRuleService:
    """CRUD for compliance rules persisted in the database."""

    def __init__(self, session=None, guardrail_service: ComplianceGuardrailService | None = None):
        self._session = session
        self._guardrail = guardrail_service

    def _get_session(self):
        return self._session

    def _notify_reload(self):
        """Notify the guardrail service to reload its cache."""
        if self._guardrail is not None:
            self._guardrail.reload_rules()

    def list_rules(self) -> list[dict]:
        """List all compliance rules."""
        session = self._get_session()
        if session is None:
            return []
        from app.infrastructure.database.models import ComplianceRule
        rules = session.query(ComplianceRule).order_by(ComplianceRule.id.desc()).all()
        return [
            {
                "id": r.id,
                "rule_code": r.rule_code,
                "rule_type": r.rule_type,
                "target": r.target,
                "limit_value": r.limit_value,
                "enabled": bool(r.enabled),
                "description": r.description,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in rules
        ]

    def create_rule(self, rule_code: str, rule_type: str, target: str = "*",
                    limit_value: float = 0.0, description: str | None = None,
                    enabled: bool = True) -> dict:
        """Create a new compliance rule."""
        session = self._get_session()
        if session is None:
            raise RuntimeError("ComplianceRuleService requires a SQLAlchemy session")

        from app.infrastructure.database.models import ComplianceRule
        rule = ComplianceRule(
            rule_code=rule_code,
            rule_type=rule_type,
            target=target,
            limit_value=limit_value,
            enabled=1 if enabled else 0,
            description=description,
        )
        session.add(rule)
        session.flush()
        logger.info("Compliance rule created: %s target=%s", rule_code, target)
        self._notify_reload()
        return self._to_dict(rule)

    def update_rule(self, rule_id: int, **kwargs) -> dict:
        """Update an existing compliance rule."""
        session = self._get_session()
        if session is None:
            raise RuntimeError("ComplianceRuleService requires a SQLAlchemy session")

        from app.infrastructure.database.models import ComplianceRule
        rule = session.query(ComplianceRule).filter_by(id=rule_id).first()
        if rule is None:
            raise ValueError(f"Compliance rule {rule_id} not found")

        updatable = {"target", "limit_value", "description", "enabled"}
        for key, value in kwargs.items():
            if key in updatable:
                setattr(rule, key, 1 if key == "enabled" and value else (0 if key == "enabled" else value))
        rule.updated_at = datetime.utcnow()
        session.flush()
        logger.info("Compliance rule updated: %s", rule_id)
        self._notify_reload()
        return self._to_dict(rule)

    def delete_rule(self, rule_id: int) -> bool:
        """Delete a compliance rule."""
        session = self._get_session()
        if session is None:
            raise RuntimeError("ComplianceRuleService requires a SQLAlchemy session")

        from app.infrastructure.database.models import ComplianceRule
        rule = session.query(ComplianceRule).filter_by(id=rule_id).first()
        if rule is None:
            return False
        session.delete(rule)
        session.flush()
        logger.info("Compliance rule deleted: %s", rule_id)
        self._notify_reload()
        return True

    def enable_rule(self, rule_id: int) -> dict:
        """Enable a compliance rule."""
        return self.update_rule(rule_id, enabled=True)

    def disable_rule(self, rule_id: int) -> dict:
        """Disable a compliance rule."""
        return self.update_rule(rule_id, enabled=False)

    @staticmethod
    def _to_dict(rule) -> dict:
        return {
            "id": rule.id,
            "rule_code": rule.rule_code,
            "rule_type": rule.rule_type,
            "target": rule.target,
            "limit_value": rule.limit_value,
            "enabled": bool(rule.enabled),
            "description": rule.description,
            "created_at": rule.created_at.isoformat() if rule.created_at else None,
            "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
        }
