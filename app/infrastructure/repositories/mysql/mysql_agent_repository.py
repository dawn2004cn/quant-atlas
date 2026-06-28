from __future__ import annotations
"""SQLAlchemy implementation of AgentRepository."""


import json
from typing import Any
from sqlalchemy import select, desc
from app.infrastructure.redis_client import RedisClientPool

from app.domain.ports import AgentRepository
from app.domain.agent_entities import MarketInsight, ReportInterpretation
from app.infrastructure.database.models.advanced import AgentMarketInsight, AgentReportInterpretation


from app.infrastructure.repositories.factory import register_repo, RepositoryType


import logging
logger = logging.getLogger(__name__)
@register_repo(RepositoryType.MYSQL, "agent")
class MySQLAgentRepository(AgentRepository):
    def __init__(self, session_factory, redis_url: str | None = None):
        self._session_factory = session_factory
        self._redis = None
        if redis_url:
            try:
                self._redis = RedisClientPool.get(redis_url).client
            except Exception as e:
                logger.warning("mysql_agent_repository.py.__init__: %s", e)

    def save_state(self, agent_id: str, state: dict[str, Any]) -> bool:
        """Save agent state to Redis."""
        if self._redis:
            try:
                self._redis.set(f"agent_state:{agent_id}", json.dumps(state), ex=86400)
                return True
            except Exception as e:
                logger.warning("mysql_agent_repository.py.save_state: %s", e)
        return False

    def get_state(self, agent_id: str) -> dict[str, Any] | None:
        """Get agent state from Redis."""
        if self._redis:
            try:
                data = self._redis.get(f"agent_state:{agent_id}")
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.warning("mysql_agent_repository.py.get_state: %s", e)
        return None

    def save_market_insight(self, insight: MarketInsight) -> int:
        session = self._session_factory()
        try:
            db_insight = AgentMarketInsight(
                market=insight.market,
                sentiment_score=insight.sentiment_score,
                sentiment_label=insight.sentiment_label,
                trend_prediction=insight.trend_prediction,
                hot_sectors=json.dumps(insight.hot_sectors),
                full_analysis=insight.full_analysis
            )
            session.add(db_insight)
            session.commit()
            insight.id = db_insight.id
            return insight.id
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_market_insights(self, market: str, limit: int = 10) -> list[MarketInsight]:
        session = self._session_factory()
        try:
            stmt = (
                select(AgentMarketInsight)
                .where(AgentMarketInsight.market == market)
                .order_by(desc(AgentMarketInsight.created_at))
                .limit(limit)
            )
            rows = session.scalars(stmt).all()
            return [self._map_db_to_insight(r) for r in rows]
        finally:
            session.close()

    def save_report_interpretation(self, interpretation: ReportInterpretation) -> int:
        session = self._session_factory()
        try:
            db_report = AgentReportInterpretation(
                report_title=interpretation.report_title,
                source=interpretation.source,
                report_date=interpretation.report_date,
                summary=interpretation.summary,
                key_takeaways=json.dumps(interpretation.key_takeaways),
                market_impact=interpretation.market_impact,
                full_interpretation=interpretation.full_interpretation,
                created_at=interpretation.created_at,
            )
            session.add(db_report)
            session.commit()
            return db_report.id
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _map_db_to_insight(self, r: AgentMarketInsight) -> MarketInsight:
        return MarketInsight(
            id=r.id,
            market=r.market,
            sentiment_score=r.sentiment_score,
            sentiment_label=r.sentiment_label,
            trend_prediction=r.trend_prediction,
            hot_sectors=json.loads(r.hot_sectors) if r.hot_sectors else [],
            full_analysis=r.full_analysis,
            created_at=r.created_at
        )

    def _map_db_to_report(self, r: AgentReportInterpretation) -> ReportInterpretation:
        return ReportInterpretation(
            id=r.id,
            report_title=r.report_title,
            source=r.source,
            report_date=r.report_date,
            summary=r.summary,
            key_takeaways=json.loads(r.key_takeaways) if r.key_takeaways else [],
            market_impact=r.market_impact,
            full_interpretation=r.full_interpretation,
            metadata=json.loads(r.metadata_json) if r.metadata_json else {},
            created_at=r.created_at
        )
