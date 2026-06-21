from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""FinGPT 应用服务：应用层对 FinGPT 持久化的唯一编排入口（写与集成栈探测）。"""


from typing import Any


from app.domain.entities import FinGPTPrediction
from app.domain.ports import FinGPTPersistencePort
from app.core.base_service import BaseApplicationService

from ....core.logger import get_logger

logger = get_logger(__name__)

class FinGPTApplicationService(BaseApplicationService):
    """封装 FinGPT 落库与只读探测；业务与 LangGraph 节点应依赖本类而非具体 Repository。"""

    def __init__(
        self,
        persistence: FinGPTPersistencePort | None = None,
        *,
        write_research_sentiment: bool = True,
        write_research_prediction: bool = True,
        write_ai_analyze: bool = True,
    ) -> None:
        super().__init__()
        self._persistence = persistence
        self._write_research_sentiment = write_research_sentiment
        self._write_research_prediction = write_research_prediction
        self._write_ai_analyze = write_ai_analyze

    def is_available(self) -> bool:
        return self._persistence is not None

    def write_policy(self) -> GenericResponseDTO[str, bool]:
        """当前写入策略（与 ``AppSettings`` / 环境变量对齐，供集成栈展示）。"""
        return {
            "research_sentiment": bool(self._write_research_sentiment),
            "research_prediction": bool(self._write_research_prediction),
            "ai_analyze": bool(self._write_ai_analyze),
        }

    def can_write_research_sentiment(self) -> bool:
        return self._persistence is not None and self._write_research_sentiment

    def can_write_research_prediction(self) -> bool:
        return self._persistence is not None and self._write_research_prediction

    def can_write_ai_analyze(self) -> bool:
        return self._persistence is not None and self._write_ai_analyze

    def record_prediction(self, pred: FinGPTPrediction) -> GenericResponseDTO:
        """写入预测；MySQL 未启用或仓储缺失时返回结构化失败。"""
        if self._persistence is None:
            return {"ok": False, "error": "fingpt_persistence_unavailable"}
        try:
            self._persistence.save_prediction(pred)
            return {"ok": True}
        except Exception as exc:  # noqa: BLE001
            logger.exception("FinGPT record_prediction failed: %s", exc)
            return {"ok": False, "error": str(exc)}

    def record_sentiment(self, ticker: str, sentiment_data: dict[str, Any]) -> GenericResponseDTO:
        """写入情感摘要行。"""
        if self._persistence is None:
            return {"ok": False, "error": "fingpt_persistence_unavailable"}
        try:
            self._persistence.save_sentiment(ticker, sentiment_data)
            return {"ok": True}
        except Exception as exc:  # noqa: BLE001
            logger.exception("FinGPT record_sentiment failed: %s", exc)
            return {"ok": False, "error": str(exc)}

    def recent_tickers(self, *, limit: int = 5) -> GenericResponseDTO:
        """只读：最近预测/情感 ticker（用于运维与轻 UI 展示）。"""
        policy = self.write_policy()
        if self._persistence is None:
            return {"ok": False, "skipped": True, "reason": "mysql_disabled_or_no_repository", "write_policy": policy}
        try:
            lim = max(1, min(int(limit), 50))
        except Exception:  # noqa: BLE001
            lim = 5
        try:
            return {
                "ok": True,
                "limit": lim,
                "recent_prediction_tickers": self._persistence.recent_prediction_tickers(lim),
                "recent_sentiment_tickers": self._persistence.recent_sentiment_tickers(lim),
                "write_policy": policy,
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("FinGPT recent_tickers failed: %s", exc)
            return {"ok": False, "error": str(exc), "limit": lim, "write_policy": policy}

    def list_recent_predictions(
        self,
        *,
        limit: int = 20,
        ticker: str | None = None,
        source: str | None = None,
        since_hours: int | None = None,
    ) -> GenericResponseDTO:
        policy = self.write_policy()
        if self._persistence is None:
            return {"ok": False, "skipped": True, "reason": "mysql_disabled_or_no_repository", "write_policy": policy}
        try:
            rows = self._persistence.list_recent_predictions(
                limit=limit,
                ticker=ticker,
                source=source,
                since_hours=since_hours,
            )
            return {"ok": True, "items": rows, "limit": int(min(max(int(limit), 1), 200)), "write_policy": policy}
        except Exception as exc:  # noqa: BLE001
            logger.warning("FinGPT list_recent_predictions failed: %s", exc)
            return {"ok": False, "error": str(exc), "items": [], "write_policy": policy}

    def list_recent_sentiments(
        self,
        *,
        limit: int = 20,
        ticker: str | None = None,
        source: str | None = None,
        since_hours: int | None = None,
    ) -> GenericResponseDTO:
        policy = self.write_policy()
        if self._persistence is None:
            return {"ok": False, "skipped": True, "reason": "mysql_disabled_or_no_repository", "write_policy": policy}
        try:
            rows = self._persistence.list_recent_sentiments(
                limit=limit,
                ticker=ticker,
                source=source,
                since_hours=since_hours,
            )
            return {"ok": True, "items": rows, "limit": int(min(max(int(limit), 1), 200)), "write_policy": policy}
        except Exception as exc:  # noqa: BLE001
            logger.warning("FinGPT list_recent_sentiments failed: %s", exc)
            return {"ok": False, "error": str(exc), "items": [], "write_policy": policy}

    def dupes_preview(self, *, ticker: str | None = None, sample: int = 20) -> GenericResponseDTO:
        """只读：返回预测/情感的重复组数量与样本（用于运维判断是否需要跑去重脚本）。"""
        policy = self.write_policy()
        if self._persistence is None:
            return {"ok": False, "skipped": True, "reason": "mysql_disabled_or_no_repository", "write_policy": policy}
        try:
            return {
                "ok": True,
                "ticker_filter": (ticker or "").strip() or None,
                "predictions": self._persistence.duplicate_prediction_groups(ticker=ticker, sample=sample),
                "sentiments": self._persistence.duplicate_sentiment_groups(ticker=ticker, sample=sample),
                "write_policy": policy,
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("FinGPT dupes_preview failed: %s", exc)
            return {"ok": False, "error": str(exc), "write_policy": policy}

    def dedupe_apply(self, *, ticker: str | None = None) -> GenericResponseDTO:
        """写：执行去重（保留最新 id），用于运维修复历史脏数据。"""
        policy = self.write_policy()
        if self._persistence is None:
            return {"ok": False, "skipped": True, "reason": "mysql_disabled_or_no_repository", "write_policy": policy}
        t = (ticker or "").strip() or None
        try:
            pred = self._persistence.dedupe_predictions(ticker=t)
            sent = self._persistence.dedupe_sentiments(ticker=t)
            return {"ok": True, "ticker_filter": t, "predictions": pred, "sentiments": sent, "write_policy": policy}
        except Exception as exc:  # noqa: BLE001
            logger.exception("FinGPT dedupe_apply failed: %s", exc)
            return {"ok": False, "error": str(exc), "write_policy": policy}

    def probe_integration_stack_layer(self) -> GenericResponseDTO:
        """供 IntegrationStackService 聚合的轻量只读探测（与 Port 统计语义一致）。"""
        policy = self.write_policy()
        if self._persistence is None:
            return {"ok": False, "skipped": True, "reason": "mysql_disabled_or_no_repository", "write_policy": policy}
        try:
            pc = self._persistence.count_predictions()
            sc = self._persistence.count_sentiment_rows()
            if pc < 0 or sc < 0:
                return {
                    "ok": False,
                    "error": "fingpt_count_failed",
                    "prediction_rows": pc,
                    "sentiment_rows": sc,
                    "write_policy": policy,
                }
            tickers = self._persistence.recent_prediction_tickers(5)
            s_tickers = self._persistence.recent_sentiment_tickers(5)
            return {
                "ok": True,
                "prediction_rows": pc,
                "sentiment_rows": sc,
                "recent_prediction_tickers": tickers,
                "recent_sentiment_tickers": s_tickers,
                "write_policy": policy,
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("FinGPT probe_integration_stack_layer failed: %s", exc)
            return {"ok": False, "error": str(exc), "write_policy": policy}
