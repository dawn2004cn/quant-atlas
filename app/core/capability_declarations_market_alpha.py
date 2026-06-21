"""Capability declarations for remaining core services (MarketService, AlphaEngine).
Phase 5 closure: every domain service gets a capability entry."""

from __future__ import annotations

from app.core.capability_registry import register_capability, get_capability_registry

# ── MarketService capabilities ──────────────────────────────────────────

@register_capability(
    name="market_regime_detect",
    description="检测当前大盘运行状态（多头/空头/震荡/极端），返回温度分0-100及红黄绿灯信号",
    domain="market_data",
    tags=["market", "regime", "sentiment", "traffic-light"],
)
def capability_market_regime_detect(symbol: str = "000001.SH", market: str = "CN") -> dict:
    """Detect current market regime using MarketRegimeService."""
    from app.domain.services.market_regime_service import MarketRegimeService
    svc = MarketRegimeService()
    return svc.analyze_regime(symbol, market)


@register_capability(
    name="market_sentiment_summary",
    description="获取大盘情绪汇总：上涨家数比、连板高度、热点板块涨股比",
    domain="market_data",
    tags=["market", "sentiment", "summary", "breadth"],
)
def capability_market_sentiment_summary() -> dict:
    from app.modules.market_data.services.sentiment_radar import SentimentRadarService
    svc = SentimentRadarService()
    return svc.compute_market_sentiment()


@register_capability(
    name="sector_hot_map",
    description="获取全行业热点图谱，按资金流入/涨幅/涨停数排序",
    domain="market_data",
    tags=["market", "sector", "hot", "ranking"],
)
def capability_sector_hot_map() -> dict:
    from app.modules.market_data.services.hot_sector_service import HotSectorService
    svc = HotSectorService()
    return svc.get_hot_map()


@register_capability(
    name="market_breadth",
    description="获取市场宽度指标（涨跌比、新高新低数、均线占比）",
    domain="market_data",
    tags=["market", "breadth", "advance-decline"],
)
def capability_market_breadth() -> dict:
    from app.modules.market_data.services.market_breadth_service import MarketBreadthService
    svc = MarketBreadthService()
    return svc.compute_breadth()


# ── AlphaEngine capabilities ───────────────────────────────────────────

@register_capability(
    name="factor_ic_analysis",
    description="分析指定因子的IC序列（信息系数），返回IC均值、IR、衰减曲线",
    domain="alpha",
    tags=["factor", "ic", "alpha", "decay"],
)
def capability_factor_ic_analysis(factor_id: str, window: int = 252) -> dict:
    from app.domain.alpha.factor_manager import get_factor_manager
    mgr = get_factor_manager()
    return mgr.analyze_ic(factor_id, window)


@register_capability(
    name="factor_correlation",
    description="计算多个因子之间的相关性矩阵，辅助因子正交化",
    domain="alpha",
    tags=["factor", "correlation", "orthogonal"],
)
def capability_factor_correlation(factor_ids: list[str]) -> dict:
    from app.domain.alpha.portfolio_correlation import get_correlation_analyzer
    analyzer = get_correlation_analyzer()
    return analyzer.compute_factor_correlation(factor_ids)


@register_capability(
    name="alpha_strategy_search",
    description="通过遗传算法搜索最优Alpha因子组合，返回排名前N的策略",
    domain="alpha",
    tags=["alpha", "search", "genetic", "optimization"],
)
def capability_alpha_strategy_search(conditions: dict, top_n: int = 10) -> dict:
    from app.domain.alpha.dynamic_search import get_search_strategy
    searcher = get_search_strategy()
    return searcher.search(conditions, top_n)


@register_capability(
    name="factor_decay_detect",
    description="检测因子衰减状态，返回是否已失效及建议替换因子",
    domain="alpha",
    tags=["factor", "decay", "lifecycle"],
)
def capability_factor_decay_detect(factor_id: str) -> dict:
    from app.domain.alpha.factor_manager import get_factor_manager
    mgr = get_factor_manager()
    return mgr.detect_decay(factor_id)


@register_capability(
    name="factor_tokenization",
    description="将高IC因子封装为Alpha Token，可共享但隐藏底层公式",
    domain="alpha",
    tags=["token", "alpha", "economy", "marketplace"],
)
def capability_factor_tokenization(factor_id: str, owner_id: int, metadata: dict | None = None) -> dict:
    from app.modules.system.services.alpha.tokenized_alpha_service import TokenizedAlphaService
    svc = TokenizedAlphaService()
    manifest = svc.tokenize_factor(factor_id, owner_id, {}, metadata or {})
    return {
        "token_id": manifest.token_id,
        "token_name": manifest.token_name,
        "token_symbol": manifest.token_symbol,
        "visibility": manifest.visibility,
    }
