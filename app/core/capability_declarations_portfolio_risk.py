"""Capability declarations for portfolio, risk, and strategy services."""
from __future__ import annotations

from app.core.capability_registry import register_capability


@register_capability(
    name="portfolio_summary",
    description="获取投资组合总览：持仓市值、盈亏、行业分布、风险敞口",
    domain="portfolio",
    tags=["portfolio", "holdings", "pnl", "exposure"],
)
def capability_portfolio_summary(user_id: int = 1) -> dict:
    from app.modules.portfolio_risk.services.portfolio_service import PortfolioApplicationService
    svc = PortfolioApplicationService()
    return svc.get_portfolio_summary(user_id=user_id)


@register_capability(
    name="portfolio_risk_check",
    description="检查投资组合风险指标：VaR、最大回撤、波动率、集中度",
    domain="portfolio",
    tags=["portfolio", "risk", "VaR", "drawdown"],
)
def capability_portfolio_risk_check(user_id: int = 1) -> dict:
    from app.modules.portfolio_risk.services.portfolio_service import PortfolioApplicationService
    svc = PortfolioApplicationService()
    return svc.get_risk_metrics(user_id=user_id)


@register_capability(
    name="portfolio_trade_suggest",
    description="根据当前持仓和市场状态给出调仓建议：降低集中度、止损提示、再平衡信号",
    domain="portfolio",
    tags=["portfolio", "rebalance", "trade", "suggestion"],
)
def capability_portfolio_trade_suggest(user_id: int = 1) -> list[dict]:
    from app.modules.portfolio_risk.services.portfolio_service import PortfolioApplicationService
    svc = PortfolioApplicationService()
    return svc.get_trade_suggestions(user_id=user_id)


@register_capability(
    name="watchlist_risk_alerts",
    description="获取自选股风险预警列表：跌幅预警、量价背离、财报提醒",
    domain="risk",
    tags=["watchlist", "risk", "alert", "warning"],
)
def capability_watchlist_risk_alerts(user_id: int = 1) -> list[dict]:
    from app.modules.market_data.services.watchlist_risk_service import RiskAlertService
    svc = RiskAlertService()
    return svc.get_active_alerts(user_id=user_id)


@register_capability(
    name="trading_risk_check",
    description="交易前风险检查：检查仓位限制、集中度、日内风控是否触发",
    domain="risk",
    tags=["trading", "risk", "pre-trade", "compliance"],
)
def capability_trading_risk_check(symbol: str, market: str = "CN", quantity: float = 0) -> dict:
    from app.modules.execution.services.trading_risk_facade import TradingRiskFacade
    svc = TradingRiskFacade()
    return svc.pre_trade_check(symbol=symbol, market=market, quantity=quantity)


@register_capability(
    name="trading_risk_limits",
    description="获取当前交易风控阈值：最大单笔仓位、日亏损限额、行业集中度限制",
    domain="risk",
    tags=["risk", "limits", "position", "stop-loss"],
)
def capability_trading_risk_limits() -> dict:
    from app.modules.execution.services.trading_risk_facade import TradingRiskFacade
    svc = TradingRiskFacade()
    return svc.get_risk_limits()


@register_capability(
    name="strategy_backtest",
    description="对指定策略进行回测：输入策略名、标的、时间范围，返回收益率、夏普、最大回撤",
    domain="strategy",
    tags=["strategy", "backtest", "performance"],
)
def capability_strategy_backtest(strategy: str, symbol: str, start: str, end: str, market: str = "CN") -> dict:
    from app.modules.strategy.services.strategy.strategy_service import StrategyApplicationService
    svc = StrategyApplicationService()
    return svc.backtest(strategy=strategy, symbol=symbol, start=start, end=end, market=market)


@register_capability(
    name="strategy_list",
    description="列出所有可用策略及其参数说明",
    domain="strategy",
    tags=["strategy", "list", "registry"],
)
def capability_strategy_list() -> list[dict]:
    from app.modules.strategy.services.strategy.strategy_service import StrategyApplicationService
    svc = StrategyApplicationService()
    return svc.list_strategies()