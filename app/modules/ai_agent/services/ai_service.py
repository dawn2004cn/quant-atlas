from __future__ import annotations

"""AI Services - AI and analysis services."""


from app.core.base_service import BaseApplicationService
from app.core.logger import get_logger
from app.domain.dto.ai_service_dto import AIAnalysisResultDTO, CommandResultDTO, DebateResultDTO, ResearchReportDTO

logger = get_logger(__name__)

try:
    from .ai_analysis_service import AiAnalysisService as RealAiAnalysisService
    from .ai_research_service import AiResearchService as RealAiResearchService
    _HAS_REAL_IMPL = True
except ImportError as e:
    logger.warning(f"Real AI service implementations not available: {e}")
    _HAS_REAL_IMPL = False


class AIAnalysisService(BaseApplicationService):
    def __init__(self, stock_service, llm_adapter=None, fingpt_application_service=None):
        super().__init__()
        self._stock_service = stock_service
        self._llm_adapter = llm_adapter
        self._fingpt_service = fingpt_application_service
        self._real_service = None
        if _HAS_REAL_IMPL:
            self._real_service = RealAiAnalysisService(
                stock_service=stock_service,
                ai_adapter=llm_adapter,
                fingpt_application_service=fingpt_application_service,
            )
        self.logger.info("AIAnalysisService initialized")

    def analyze(self, code: str, market: str = "CN") -> AIAnalysisResultDTO:
        if self._real_service:
            from ....domain.enums import MarketCode
            try:
                market_code = MarketCode(market.upper())
            except ValueError:
                market_code = MarketCode.CN
            res = self._real_service.analyze(code, market_code)
            return AIAnalysisResultDTO(code=res.get("code", code), analysis=res.get("analysis", ""))
        return AIAnalysisResultDTO(code=code, analysis="AI service not configured")


class AiResearchService(BaseApplicationService):
    def __init__(self, fingpt_application_service=None):
        super().__init__()
        self._fingpt_service = fingpt_application_service
        self._real_service = None
        if _HAS_REAL_IMPL:
            self._real_service = RealAiResearchService(
                fingpt_application_service=fingpt_application_service
            )
        self.logger.info("AiResearchService initialized")

    async def run_research(self, ticker: str, query: str, user_id: int, **kwargs) -> ResearchReportDTO:
        if self._real_service:
            res = await self._real_service.run_research(ticker, query, user_id, **kwargs)
            return ResearchReportDTO(code=ticker, report=res.get("report", ""))
        return ResearchReportDTO(code=ticker, report="Research service not configured")


class AICommitteeService(BaseApplicationService):
    def __init__(self, stock_service, llm_adapter):
        super().__init__()
        self._stock_service = stock_service
        self._llm_adapter = llm_adapter
        self._agents = []
        self.logger.info("AICommitteeService initialized")

    def run_debate(self, symbol: str, market_code: str) -> DebateResultDTO:
        return DebateResultDTO(symbol=symbol, decision="hold", votes=[])


class CommandService(BaseApplicationService):
    def __init__(self, llm_adapter):
        super().__init__()
        self._llm_adapter = llm_adapter
        self.logger.info("CommandService initialized")

    def execute(self, command: str) -> CommandResultDTO:
        return CommandResultDTO(result="executed", command=command)


__all__ = [
    "AIAnalysisService",
    "AiResearchService",
    "AICommitteeService",
    "CommandService",
]
