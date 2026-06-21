from app.modules.ai_agent.services.ai_analysis_service import AiAnalysisService
from app.modules.system.services.system.pool_service import PoolApplicationService
from app.domain.enums import MarketCode


class _MarketService:
    def list_quotes(self, market, symbols=None):
        return [{"code": s, "price": 10.0, "change_pct": 1.2} for s in (symbols or [])]


class _StrategyService:
    def select_stocks(self, strategy_name, market, top_n):
        return {"candidates": [{"code": "600519", "name": "贵州茅台", "score": 88, "reason": "动量强"}][:top_n]}


class _StockService:
    def get_stock_detail(self, symbol, market):
        class MockDetail:
            profile = {"realtime": {"updated_at": "2026-01-01 10:00:00"}}
            indicators = {"rsi14": 55}
            news = [{"title": "news"}]
            industry_news = [{"title": "industry"}]
        return MockDetail()


class _AiAdapter:
    def analyze(self, **kwargs):
        return {"analysis": "看多"}


def test_pool_service_builds_pool():
    service = PoolApplicationService(_MarketService(), _StrategyService())
    result = service.get_live_pool(MarketCode.CN, top_n=1)
    assert result["market"] == "CN"
    assert result["count"] == 1
    assert result["pool"][0]["code"] == "600519"


def test_ai_service_returns_payload():
    service = AiAnalysisService(_StockService(), _AiAdapter())
    result = service.analyze("600519", MarketCode.CN)
    assert result["symbol"] == "600519"
    assert result["ai"]["analysis"] == "看多"
    assert "decision_id" in result
    assert result["decision"]["subject"] == "CN:600519"
    assert result["decision"]["schema_version"] == "v1"
