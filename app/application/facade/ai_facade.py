from __future__ import annotations

from typing import Any

from pydantic import ValidationError as PydanticValidationError

from app.application.errors import ValidationError
from app.domain.enums import MarketCode
from app.application.facade._helpers import observe_facade, parse_market, validation_error_from_pydantic
from app.application.facade.dto.ai_facade_dto import AIAnalysisRequestDTO, AIAnalysisResultDTO

_MAX_USER_PROMPT_LEN = 4000
_FORBIDDEN_PROMPT_SNIPPETS = (
    "ignore previous instructions",
    "ignore all previous",
    "system prompt",
    "jailbreak",
    "developer mode",
)


def sanitize_user_prompt(text: str | None) -> str | None:
    """Basic prompt-injection guard for user-supplied hypothesis text."""
    if text is None:
        return None
    cleaned = text.strip()[:_MAX_USER_PROMPT_LEN]
    if not cleaned:
        return None
    lowered = cleaned.lower()
    for snippet in _FORBIDDEN_PROMPT_SNIPPETS:
        if snippet in lowered:
            raise ValidationError("Prompt contains disallowed instructions")
    return cleaned


class AIFacade:
    """Facade for AI analysis entry points."""

    _FACADE_NAME = "ai"

    def __init__(self, ai_analysis_service: Any):
        self._ai_analysis_service = ai_analysis_service

    def analyze(
        self,
        symbol: str,
        market: str | MarketCode,
        *,
        user_hypothesis: str | None = None,
        hypothesis_id: str | None = None,
        depth: str = "standard",
        evidence_depth: str | None = None,
    ) -> dict[str, Any]:
        """Run AI analysis with validated market code and sanitized user text."""
        with observe_facade(self._FACADE_NAME, "analyze"):
            if self._ai_analysis_service is None:
                raise ValidationError("AI analysis service not configured")

            market_value = market.value if isinstance(market, MarketCode) else str(market)
            try:
                request = AIAnalysisRequestDTO(
                    symbol=symbol,
                    market=market_value,
                    analysis_type=depth or "standard",
                    user_hypothesis=user_hypothesis,
                    hypothesis_id=hypothesis_id,
                    evidence_depth=evidence_depth or depth or "standard",
                )
            except PydanticValidationError as exc:
                raise validation_error_from_pydantic(exc) from exc

            mc = parse_market(request.market)
            hypothesis = sanitize_user_prompt(request.user_hypothesis)

            if request.analysis_type == "deep" and hasattr(self._ai_analysis_service, "deep_analyze"):
                result = self._ai_analysis_service.deep_analyze(
                    request.symbol,
                    mc,
                    depth=request.analysis_type,
                    user_hypothesis=hypothesis,
                    hypothesis_id=request.hypothesis_id,
                )
            else:
                result = self._ai_analysis_service.analyze(
                    request.symbol,
                    mc,
                    user_hypothesis=hypothesis,
                    hypothesis_id=request.hypothesis_id,
                )

            normalized = AIAnalysisResultDTO.from_service(result)
            payload = normalized.model_dump()
            payload["raw"] = normalized.raw
            return payload
