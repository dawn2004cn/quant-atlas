from __future__ import annotations
"""SQLAlchemy implementation of KronosRepository."""


import json
from typing import Any
from sqlalchemy import select

from app.domain.ports import KronosRepository
from app.domain.kronos_entities import KronosModel, KronosPrediction
from app.infrastructure.database.models.advanced import KronosModel as DBKronosModel, KronosPrediction as DBKronosPrediction


class MySQLKronosRepository(KronosRepository):
    def __init__(self, session_factory):
        self._session_factory = session_factory

    def save_model(self, model: Any) -> str:
        """Save Kronos model (stub for interface compatibility)."""
        if hasattr(model, 'model_id'):
            return str(model.model_id)
        return "stub_model_id"

    def get_model(self, model_id: str) -> KronosModel | None:
        session = self._session_factory()
        try:
            db_model = session.get(DBKronosModel, model_id)
            if not db_model:
                return None
            return self._map_db_to_model(db_model)
        finally:
            session.close()

    def list_active_models(self) -> list[KronosModel]:
        session = self._session_factory()
        try:
            stmt = select(DBKronosModel).where(DBKronosModel.is_active == 1)
            rows = session.scalars(stmt).all()
            return [self._map_db_to_model(r) for r in rows]
        finally:
            session.close()

    def save_prediction(self, prediction: KronosPrediction) -> int:
        session = self._session_factory()
        try:
            db_pred = DBKronosPrediction(
                ticker=prediction.ticker,
                model_id=prediction.model_id,
                prediction_date=prediction.prediction_date,
                horizon_days=prediction.horizon_days,
                forecast_json=json.dumps(prediction.forecast_data),
                metrics_json=json.dumps(prediction.metrics)
            )
            session.add(db_pred)
            session.commit()
            prediction.id = db_pred.id
            return prediction.id
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _map_db_to_model(self, r: DBKronosModel) -> KronosModel:
        return KronosModel(
            model_id=r.model_id,
            model_type=r.model_type,
            hf_path=r.hf_path,
            local_path=r.local_path,
            is_active=bool(r.is_active),
            metadata=json.loads(r.metadata_json) if r.metadata_json else {},
            created_at=r.created_at
        )
