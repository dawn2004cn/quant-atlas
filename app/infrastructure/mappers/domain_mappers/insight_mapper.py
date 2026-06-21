"""Mapper for Agent entities."""

from app.domain.agent_entities import MarketInsight
from app.infrastructure.database.models.advanced import AgentMarketInsight
from app.infrastructure.mappers.domain_mappers.base import DataMapper
import json

class MarketInsightMapper(DataMapper[MarketInsight, AgentMarketInsight]):
    
    @staticmethod
    def to_domain(model: AgentMarketInsight) -> MarketInsight:
        return MarketInsight(
            id=model.id,
            market=model.market,
            sentiment_score=model.sentiment_score,
            sentiment_label=model.sentiment_label,
            trend_prediction=model.trend_prediction,
            hot_sectors=json.loads(model.hot_sectors) if model.hot_sectors else [],
            full_analysis=model.full_analysis,
            created_at=model.created_at
        )

    @staticmethod
    def to_model(entity: MarketInsight) -> AgentMarketInsight:
        return AgentMarketInsight(
            market=entity.market,
            sentiment_score=entity.sentiment_score,
            sentiment_label=entity.sentiment_label,
            trend_prediction=entity.trend_prediction,
            hot_sectors=json.dumps(entity.hot_sectors),
            full_analysis=entity.full_analysis
        )
