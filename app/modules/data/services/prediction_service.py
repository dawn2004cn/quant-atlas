from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""阶段 3：模型注册与截面打分（占位实现可对接真实权重文件）。"""


import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import BASE_DIR, DEFAULT_MODEL_REGISTRY_PATH
from app.core.logger import get_logger
from app.domain.enums import MarketCode
from .model_predict_lab_service import ModelPredictLabService

logger = get_logger(__name__)

_DEFAULT_REGISTRY: dict[str, Any] = {
    "models": [
        {
            "id": "default_momentum",
            "label": "中期动量（启发式）",
            "version": "0.1.0",
            "path": None,
            "features": ["lookahead_return_N"],
        },
        {
            "id": "lstm_style_momentum",
            "label": "LSTM 占位标签动量",
            "version": "0.1.0",
            "path": None,
            "features": ["lookahead_return_N"],
        },
    ],
    "updated_at": "",
}


class PredictionApplicationService:
    """``config/model_registry.json`` + ``ModelPredictLabService`` 截面排序。"""

    def __init__(self, predictor: ModelPredictLabService, *, base_dir: Path | None = None) -> None:
        self._predictor = predictor
        self._base = Path(base_dir or BASE_DIR)
        self._registry_path = (
            DEFAULT_MODEL_REGISTRY_PATH if self._base == BASE_DIR else self._base / "config" / "model_registry.json"
        ).resolve()

    def _ensure_registry_file(self) -> None:
        if self._registry_path.is_file():
            return
        legacy = (self._base / "instance" / "model_registry.json").resolve()
        if legacy.is_file():
            self._registry_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(legacy, self._registry_path)
            logger.info("prediction: migrated model registry %s -> %s", legacy, self._registry_path)
            return
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        data = dict(_DEFAULT_REGISTRY)
        data["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        self._registry_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("prediction: seeded default model registry %s", self._registry_path)

    def list_models(self) -> list[dict[str, Any]]:
        self._ensure_registry_file()
        try:
            raw = json.loads(self._registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("model_registry read failed: %s", exc)
            return list(_DEFAULT_REGISTRY["models"])
        models = raw.get("models")
        if not isinstance(models, list):
            return list(_DEFAULT_REGISTRY["models"])
        return [m for m in models if isinstance(m, dict)]

    def get_model(self, model_id: str) -> GenericResponseDTO | None:
        mid = (model_id or "").strip()
        for m in self.list_models():
            if str(m.get("id", "")).strip() == mid:
                return m
        return None

    def scores_cross_section(
        self,
        symbols: list[str],
        market: MarketCode,
        *,
        model_id: str | None = None,
        horizon_days: int = 20,
    ) -> GenericResponseDTO:
        mid = (model_id or "default_momentum").strip()
        model_meta = self.get_model(mid)
        if model_meta is None:
            model_meta = {"id": mid, "label": mid, "version": "?", "features": [], "path": None}

        out = self._predictor.predict_rank(
            symbols=symbols,
            market=market,
            model_id=mid,
            horizon_days=horizon_days,
        )
        return {
            "model": model_meta,
            "market": market.value,
            "ranking": out.get("ranking") or [],
            "source": out.get("source"),
            "model_label": out.get("model_label"),
            "evidence": out.get("evidence"),
            "horizon_days": out.get("horizon_days"),
        }
