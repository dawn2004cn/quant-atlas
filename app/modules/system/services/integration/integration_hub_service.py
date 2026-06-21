from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""集成中枢页面上下文组装（应用层，薄封装）。"""


from typing import Any

from app.config import AppSettings, get_settings
from app.domain.integration_catalog import LAYER_LABELS, IntegrationLayer, cards_by_layer


def build_integration_hub_context(*, settings: AppSettings | None = None) -> GenericResponseDTO:
    s = settings or get_settings()
    grouped = cards_by_layer()
    layer_order: tuple[IntegrationLayer, ...] = (
        "data",
        "execution",
        "analytics",
        "agents",
        "payments",
        "ops",
    )
    sections: list[dict[str, Any]] = []
    for layer in layer_order:
        rows = grouped.get(layer) or []
        if not rows:
            continue
        sections.append({"layer": layer, "title": LAYER_LABELS[layer], "cards": rows})

    return {
        "sections": sections,
        "enable_qlib": s.enable_qlib,
        "enable_celery": s.enable_celery,
        "enable_rd_agent": s.enable_rd_agent,
        "use_mysql": s.use_mysql,
        "database_backend": s.database_backend,
        "fingpt_write_research_sentiment": s.fingpt_write_research_sentiment,
        "fingpt_write_research_prediction": s.fingpt_write_research_prediction,
        "fingpt_write_ai_analyze": s.fingpt_write_ai_analyze,
    }
