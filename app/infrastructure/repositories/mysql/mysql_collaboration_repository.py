from __future__ import annotations
"""MySQL repository for tenants, teams and tenant-scoped user settings."""

import json
from datetime import datetime
from typing import Any, Callable

from sqlalchemy import select

from app.core.logger import get_logger
from app.core.query_limits import MAX_USER_TEAMS
from app.domain.entities import Team, TeamMembership, Tenant
from app.infrastructure.database.models.collaboration import (
    Team as DBTeam,
    TeamBlackboardEntry,
    TeamMembership as DBMembership,
    Tenant as DBTenant,
    UserKnowledgeProfile,
    UserLifecycleSettings,
)

logger = get_logger(__name__)


class MySQLCollaborationRepository:
    """Row-level tenant isolation for lifecycle and knowledge stores."""

    def __init__(self, session_factory: Callable[[], Any]) -> None:
        self._session_factory = session_factory

    def ensure_personal_tenant(self, user_id: int) -> Tenant:
        slug = f"personal-u{user_id}"
        session = self._session_factory()
        try:
            row = session.execute(select(DBTenant).where(DBTenant.slug == slug)).scalar_one_or_none()
            if row is None:
                row = DBTenant(slug=slug, name=f"个人空间 #{user_id}", plan="personal")
                session.add(row)
                session.commit()
                session.refresh(row)
            return Tenant(id=row.id, slug=row.slug, name=row.name, plan=row.plan, created_at=row.created_at)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_tenant_by_slug(self, slug: str) -> Tenant | None:
        session = self._session_factory()
        try:
            row = session.execute(select(DBTenant).where(DBTenant.slug == slug)).scalar_one_or_none()
            if row is None:
                return None
            return Tenant(id=row.id, slug=row.slug, name=row.name, plan=row.plan, created_at=row.created_at)
        finally:
            session.close()

    def create_team(self, *, tenant_id: int, slug: str, name: str) -> Team:
        session = self._session_factory()
        try:
            row = DBTeam(tenant_id=tenant_id, slug=slug, name=name)
            session.add(row)
            session.commit()
            session.refresh(row)
            return Team(id=row.id, tenant_id=row.tenant_id, slug=row.slug, name=row.name, created_at=row.created_at)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def add_team_member(self, *, team_id: int, user_id: int, role: str = "member") -> TeamMembership:
        session = self._session_factory()
        try:
            row = DBMembership(team_id=team_id, user_id=user_id, role=role)
            session.add(row)
            session.commit()
            session.refresh(row)
            return TeamMembership(
                id=row.id,
                team_id=row.team_id,
                user_id=row.user_id,
                role=row.role,
                joined_at=row.joined_at,
            )
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_user_teams(self, user_id: int) -> list[dict[str, Any]]:
        session = self._session_factory()
        try:
            rows = session.execute(
                select(DBTeam, DBMembership)
                .join(DBMembership, DBMembership.team_id == DBTeam.id)
                .where(DBMembership.user_id == user_id)
                .limit(MAX_USER_TEAMS)
            ).all()
            return [
                {
                    "team_id": team.id,
                    "team_slug": team.slug,
                    "team_name": team.name,
                    "tenant_id": team.tenant_id,
                    "role": membership.role,
                }
                for team, membership in rows
            ]
        finally:
            session.close()

    def get_lifecycle_row(self, user_id: int, tenant_id: int) -> dict[str, Any] | None:
        session = self._session_factory()
        try:
            row = session.execute(
                select(UserLifecycleSettings).where(
                    UserLifecycleSettings.user_id == user_id,
                    UserLifecycleSettings.tenant_id == tenant_id,
                )
            ).scalar_one_or_none()
            if row is None:
                return None
            return {
                "notifications": self._loads(row.notifications_json),
                "privacy_consent": self._loads(row.privacy_consent_json),
                "deletion_request": self._loads(row.deletion_request_json),
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
        finally:
            session.close()

    def upsert_lifecycle_row(
        self,
        user_id: int,
        tenant_id: int,
        *,
        notifications: dict[str, Any] | None = None,
        privacy_consent: dict[str, Any] | None = None,
        deletion_request: dict[str, Any] | None = None,
    ) -> None:
        session = self._session_factory()
        try:
            row = session.execute(
                select(UserLifecycleSettings).where(
                    UserLifecycleSettings.user_id == user_id,
                    UserLifecycleSettings.tenant_id == tenant_id,
                )
            ).scalar_one_or_none()
            if row is None:
                row = UserLifecycleSettings(user_id=user_id, tenant_id=tenant_id)
                session.add(row)
            if notifications is not None:
                row.notifications_json = json.dumps(notifications, ensure_ascii=False)
            if privacy_consent is not None:
                row.privacy_consent_json = json.dumps(privacy_consent, ensure_ascii=False)
            if deletion_request is not None:
                row.deletion_request_json = json.dumps(deletion_request, ensure_ascii=False)
            row.updated_at = datetime.utcnow()
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_knowledge_profile(self, user_id: int, tenant_id: int) -> dict[str, Any] | None:
        session = self._session_factory()
        try:
            row = session.execute(
                select(UserKnowledgeProfile).where(
                    UserKnowledgeProfile.user_id == user_id,
                    UserKnowledgeProfile.tenant_id == tenant_id,
                )
            ).scalar_one_or_none()
            if row is None:
                return None
            data = self._loads(row.profile_json)
            return data if isinstance(data, dict) else None
        finally:
            session.close()

    def upsert_knowledge_profile(
        self, user_id: int, tenant_id: int, profile: dict[str, Any]
    ) -> None:
        session = self._session_factory()
        try:
            row = session.execute(
                select(UserKnowledgeProfile).where(
                    UserKnowledgeProfile.user_id == user_id,
                    UserKnowledgeProfile.tenant_id == tenant_id,
                )
            ).scalar_one_or_none()
            if row is None:
                row = UserKnowledgeProfile(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    profile_json=json.dumps(profile, ensure_ascii=False),
                )
                session.add(row)
            else:
                row.profile_json = json.dumps(profile, ensure_ascii=False)
            row.updated_at = datetime.utcnow()
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def add_blackboard_entry(
        self,
        *,
        team_id: int,
        user_id: int,
        agent_role: str,
        evidence_key: str,
        evidence_value: str,
        symbol: str | None = None,
        strength: str = "moderate",
        narrative: str = "",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        session = self._session_factory()
        try:
            row = TeamBlackboardEntry(
                team_id=team_id,
                user_id=user_id,
                agent_role=agent_role,
                symbol=(symbol or "").strip().lower() or None,
                evidence_key=evidence_key,
                evidence_value=evidence_value,
                strength=strength,
                narrative=narrative,
                payload_json=json.dumps(payload or {}, ensure_ascii=False),
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return self._blackboard_to_dict(row)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_blackboard_entries(
        self,
        team_id: int,
        *,
        symbol: str | None = None,
        limit: int = 80,
    ) -> list[dict[str, Any]]:
        session = self._session_factory()
        try:
            stmt = select(TeamBlackboardEntry).where(TeamBlackboardEntry.team_id == team_id)
            if symbol:
                stmt = stmt.where(TeamBlackboardEntry.symbol == symbol.strip().lower())
            stmt = stmt.order_by(TeamBlackboardEntry.created_at.desc()).limit(max(1, limit))
            rows = session.execute(stmt).scalars().all()
            return [self._blackboard_to_dict(r) for r in rows]
        finally:
            session.close()

    @staticmethod
    def _blackboard_to_dict(row: TeamBlackboardEntry) -> dict[str, Any]:
        return {
            "id": row.id,
            "team_id": row.team_id,
            "user_id": row.user_id,
            "agent_role": row.agent_role,
            "symbol": row.symbol,
            "evidence_key": row.evidence_key,
            "evidence_value": row.evidence_value,
            "strength": row.strength,
            "narrative": row.narrative,
            "payload": MySQLCollaborationRepository._loads(row.payload_json),
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    @staticmethod
    def _loads(raw: str | None) -> Any:
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}
