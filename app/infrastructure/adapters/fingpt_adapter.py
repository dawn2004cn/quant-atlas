from __future__ import annotations
"""FinGPT core adapters and repository implementation."""


import json
from datetime import datetime
from typing import Any

from sqlalchemy import select, func, desc, and_, text

from app.core.circuit_breaker import CircuitBreakerOpenError, circuit_breaker

from ...domain.ports import FinGPTPersistencePort, SentimentProvider
from ..database.models.advanced import FinGPTPrediction as DBFinGPTPrediction, FinGPTSentiment as DBFinGPTSentiment

from app.core.logger import get_logger

logger = get_logger(__name__)


class FinGPTSentimentAdapter(SentimentProvider):
    """FinGPT sentiment adapter."""

    def __init__(self, llm_adapter: Any):
        self._llm = llm_adapter

    def analyze_sentiment(self, text: str) -> dict[str, Any]:
        """Analyze sentiment using LLM."""
        try:
            return self._analyze_sentiment_llm(text)
        except CircuitBreakerOpenError:
            from app.core.middleware.degraded_context import mark_system_degraded

            mark_system_degraded("fingpt")
            logger.warning("FinGPT sentiment circuit open")
            return {
                "score": 0.5,
                "factors": [],
                "concerns": [],
                "impact": "Medium",
                "degraded": True,
            }
        except Exception as e:
            logger.warning("sentiment analysis failed: %s", e)
            return {"score": 0.5, "factors": [], "concerns": [], "impact": "Medium"}

    @circuit_breaker("fingpt_sentiment", failure_threshold=3, timeout=60)
    def _analyze_sentiment_llm(self, text: str) -> dict[str, Any]:
        system_prompt = """You are a financial sentiment analyst.
Analyze the following text for:
1. Positive Factors
2. Potential Concerns
3. Sentiment Score (0-1, 1 is most bullish)
4. Impact Level (Low, Medium, High)

Return as JSON."""
        response = self._llm.chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ])
        content = response.get("content", "")
        if content.strip().startswith("{"):
            return json.loads(content)
        return {"score": 0.5, "factors": [], "concerns": []}


class FinGPTRepository(FinGPTPersistencePort):
    """FinGPT repository."""

    def __init__(self, session_factory):
        self._session_factory = session_factory

    def save_prediction(self, prediction: dict[str, Any]) -> str:
        return "stub_prediction_id"

    def list_predictions(self, limit: int = 100) -> list[dict[str, Any]]:
        return []

    def save_sentiment(self, ticker: str, data: dict[str, Any]) -> bool:
        """Save sentiment data."""
        session = self._session_factory()
        try:
            from datetime import datetime
            sentiment = DBFinGPTSentiment(
                ticker=ticker,
                news_id=data.get("news_id", ""),
                summary_hash=data.get("summary_hash", ""),
                source=data.get("source", "unknown"),
                source_ref=data.get("source_ref", ""),
                sentiment_score=data.get("sentiment_score", 0.0),
                key_entities=data.get("key_entities", ""),
                impact_level=data.get("impact_level", "Medium"),
                summary=data.get("summary", ""),
                created_at=datetime.now(),
            )
            session.add(sentiment)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.warning(f"save_sentiment failed: {e}")
            return False
        finally:
            session.close()

    def count_predictions(self) -> int:
        session = self._session_factory()
        try:
            return session.query(func.count(DBFinGPTPrediction.id)).scalar() or 0
        except Exception as exc:
            logger.warning("fingpt count_predictions failed: %s", exc)
            return -1
        finally:
            session.close()

    def count_sentiment_rows(self) -> int:
        session = self._session_factory()
        try:
            return session.query(func.count(DBFinGPTSentiment.id)).scalar() or 0
        except Exception as exc:
            logger.warning("fingpt count_sentiment_rows failed: %s", exc)
            return -1
        finally:
            session.close()

    def list_recent_predictions(
        self,
        *,
        limit: int = 20,
        ticker: str | None = None,
        source: str | None = None,
        since_hours: int | None = None,
    ) -> list[dict[str, Any]]:
        session = self._session_factory()
        try:
            cols = ["id", "ticker", "prediction_date", "source_ref", "predicted_movement", "positive_factors", "potential_concerns", "analysis_summary", "confidence", "actual_movement", "is_correct", "created_at"]
            col_str = ", ".join(cols)
            sql = f"SELECT {col_str} FROM fingpt_predictions WHERE 1=1"
            params = {}
            if ticker:
                sql += " AND ticker = :ticker"
                params["ticker"] = ticker
            if since_hours:
                sql += " AND created_at >= DATE_SUB(NOW(), INTERVAL :hours HOUR)"
                params["hours"] = since_hours
            sql += " ORDER BY id DESC LIMIT :limit"
            params["limit"] = limit
            
            result = session.execute(text(sql), params)
            return [row[0] for row in result.fetchall() if row[0]]
        except Exception as exc:
            logger.warning("fingpt recent_sentiment_tickers failed: %s", exc)
            return []
        finally:
            session.close()

    def recent_prediction_tickers(self, limit: int = 10) -> list[str]:
        """Get distinct tickers from recent predictions."""
        session = self._session_factory()
        try:
            sql = "SELECT ticker FROM fingpt_predictions GROUP BY ticker ORDER BY MAX(id) DESC LIMIT :limit"
            result = session.execute(text(sql), {"limit": limit})
            return [row[0] for row in result.fetchall() if row[0]]
        except Exception as exc:
            logger.warning("fingpt recent_prediction_tickers failed: %s", exc)
            return []

    def recent_sentiment_tickers(self, limit: int = 10) -> list[str]:
        """Get distinct tickers from recent sentiment data."""
        session = self._session_factory()
        try:
            sql = "SELECT ticker FROM fingpt_sentiment GROUP BY ticker ORDER BY MAX(id) DESC LIMIT :limit"
            result = session.execute(text(sql), {"limit": limit})
            return [row[0] for row in result.fetchall() if row[0]]
        except Exception as exc:
            logger.warning("fingpt recent_sentiment_tickers failed: %s", exc)
            return []

    def _map_prediction_to_dict(self, r: DBFinGPTPrediction) -> dict[str, Any]:
        return {
            "id": r.id,
            "ticker": r.ticker,
            "prediction_date": str(r.prediction_date),
            "source": getattr(r, "source", "unknown"),
            "source_ref": r.source_ref,
            "predicted_movement": r.predicted_movement,
            "positive_factors": r.positive_factors or "",
            "potential_concerns": r.potential_concerns or "",
            "analysis_summary": r.analysis_summary,
            "confidence": r.confidence,
            "actual_movement": r.actual_movement,
            "is_correct": r.is_correct,
            "created_at": str(r.created_at)
        }

    def list_recent_sentiments(
        self,
        *,
        limit: int = 20,
        ticker: str | None = None,
        source: str | None = None,
        since_hours: int | None = None,
    ) -> list[dict[str, Any]]:
        session = self._session_factory()
        try:
            cols = ["id", "ticker", "news_id", "summary_hash", "source_ref", "sentiment_score", "key_entities", "impact_level", "summary", "created_at"]
            col_str = ", ".join(cols)
            sql = f"SELECT {col_str} FROM fingpt_sentiment WHERE 1=1"
            params = {}
            if ticker:
                sql += " AND ticker = :ticker"
                params["ticker"] = ticker
            if since_hours:
                sql += " AND created_at >= DATE_SUB(NOW(), INTERVAL :hours HOUR)"
                params["hours"] = since_hours
            sql += " ORDER BY id DESC LIMIT :limit"
            params["limit"] = limit
            
            result = session.execute(text(sql), params)
            return [dict(zip(cols, row)) for row in result.fetchall()]
        except Exception as exc:
            logger.warning("fingpt list_recent_sentiments failed: %s", exc)
            return []
        finally:
            session.close()

    def _map_sentiment_to_dict(self, r: DBFinGPTSentiment) -> dict[str, Any]:
        return {
            "id": r.id,
            "ticker": r.ticker,
            "news_id": r.news_id,
            "summary_hash": r.summary_hash,
            "source": getattr(r, "source", "unknown"),
            "source_ref": r.source_ref,
            "sentiment_score": r.sentiment_score,
            "key_entities": r.key_entities,
            "impact_level": r.impact_level,
            "summary": r.summary,
            "created_at": str(r.created_at)
        }

    def duplicate_prediction_groups(self, *, ticker: str | None = None, sample: int = 20) -> dict[str, Any]:
        session = self._session_factory()
        try:
            stmt = select(DBFinGPTPrediction.ticker, func.count(DBFinGPTPrediction.id).label("count")).group_by(DBFinGPTPrediction.ticker).having(func.count(DBFinGPTPrediction.id) > 1)
            rows = session.execute(stmt).fetchall()
            return {"groups": [{"ticker": r[0], "count": r[1]} for r in rows]}
        except Exception as exc:
            logger.warning("duplicate prediction groups failed: %s", exc)
            return {"groups": []}
        finally:
            session.close()

    def get_ticker_summary(self, *, ticker: str) -> dict[str, Any]:
        predictions = self.list_recent_predictions(ticker=ticker, limit=100)
        correct = sum(1 for p in predictions if p.get("is_correct") == 1)
        return {"ticker": ticker, "total": len(predictions), "correct": correct, "accuracy": correct / max(len(predictions), 1)}

    def save_prediction_batch(self, predictions: list[dict[str, Any]]) -> int:
        session = self._session_factory()
        saved = 0
        try:
            for p in predictions:
                session.add(DBFinGPTPrediction(**p))
            session.commit()
            saved = len(predictions)
        except Exception as e:
            session.rollback()
            logger.error(f"save prediction batch failed: {e}")
        finally:
            session.close()
        return saved

    def delete_old_predictions(self, days: int = 90) -> int:
        session = self._session_factory()
        try:
            from datetime import timedelta
            cutoff = datetime.now() - timedelta(days=days)
            result = session.query(DBFinGPTPrediction).filter(DBFinGPTPrediction.created_at < cutoff).delete()
            session.commit()
            return result
        except Exception as e:
            session.rollback()
            logger.warning(f"delete old predictions failed: {e}")
            return 0
        finally:
            session.close()