from datetime import datetime

from pydantic import BaseModel, Field


class FactorContributionDTO(BaseModel):
    factor_name: str
    contribution_pct: float
    contribution_amount: float
    description: str = ""


class StyleContributionDTO(BaseModel):
    """Brinson-style or factor-model style decomposition."""

    component: str
    contribution_pct: float
    description: str = ""


class SlippageContributionDTO(BaseModel):
    """Execution drag from real fills vs intended prices."""

    avg_slippage_pct: float = 0.0
    quality: str = "unknown"
    contribution_pct: float = 0.0
    latency_ms: float | None = None
    order_count: int = 0
    notes: str = ""


class SectorContributionDTO(BaseModel):
    sector: str
    weight: float
    return_pct: float
    contribution_pct: float

class StockContributionDTO(BaseModel):
    symbol: str
    name: str
    weight: float
    return_pct: float
    contribution_pct: float

class MarketEffectDTO(BaseModel):
    market_return: float
    alpha: float
    beta: float = 1.0

class AttributionReportDTO(BaseModel):
    strategy_name: str
    period: str
    scope: str = "portfolio"
    symbol: str | None = None
    total_return: float
    market_effect: MarketEffectDTO
    factors: list[FactorContributionDTO] = Field(default_factory=list)
    style_contributions: list[StyleContributionDTO] = Field(default_factory=list)
    slippage: SlippageContributionDTO | None = None
    sectors: list[SectorContributionDTO] = Field(default_factory=list)
    stocks: list[StockContributionDTO] = Field(default_factory=list)
    top_contributors: list[StockContributionDTO] = Field(default_factory=list)
    bottom_contributors: list[StockContributionDTO] = Field(default_factory=list)
    summary: str = ""
    generated_at: datetime = Field(default_factory=datetime.now)


class FactorCompareRowDTO(BaseModel):
    factor_name: str
    base_pct: float
    peer_pct: float
    delta_pct: float


class AttributionCompareDTO(BaseModel):
    base_symbol: str
    peer_symbol: str
    base_name: str = ""
    peer_name: str = ""
    market: str = "CN"
    period: str = "30d"
    base_total_return: float = 0.0
    peer_total_return: float = 0.0
    base_alpha: float = 0.0
    peer_alpha: float = 0.0
    base_beta: float = 1.0
    peer_beta: float = 1.0
    factor_rows: list[FactorCompareRowDTO] = Field(default_factory=list)
    summary: str = ""


class PreTradeIssueDTO(BaseModel):
    code: str
    message: str
    severity: str = "blocking"


class RiskConfigDTO(BaseModel):
    """Account-level risk limits for pre-trade checks."""

    account_equity: float = 0.0
    risk_per_trade: float = Field(default=0.02, ge=0.0, le=1.0)
    max_trade_amount: float = 0.0
    portfolio_value: float = 0.0
    current_position_pct: float = Field(default=0.0, ge=0.0, le=1.0)
    current_sector_pct: float = Field(default=0.0, ge=0.0, le=1.0)
    sector: str = "unknown"


class PositionSizingDTO(BaseModel):
    """ATR-based position sizing output."""

    atr_value: float = 0.0
    suggested_quantity: int = 0
    suggested_stop_loss: float = 0.0
    suggested_take_profit: float = 0.0
    max_expected_loss: float = 0.0
    risk_per_trade_pct: float = 0.0

    @classmethod
    def from_atr(
        cls,
        *,
        entry_price: float,
        atr: float,
        account_equity: float,
        risk_per_trade: float,
    ) -> "PositionSizingDTO":
        if entry_price <= 0 or atr <= 0 or account_equity <= 0:
            return cls()
        suggested_sl = round(entry_price - 2.0 * atr, 2)
        suggested_tp = round(entry_price + 3.0 * atr, 2)
        risk_per_share = entry_price - suggested_sl
        if risk_per_share <= 0:
            return cls(atr_value=round(atr, 4), suggested_stop_loss=suggested_sl, suggested_take_profit=suggested_tp)
        risk_amount = account_equity * risk_per_trade
        qty = max(0, int(risk_amount / risk_per_share / 100) * 100)
        if qty < 100 and risk_amount / risk_per_share >= 100:
            qty = 100
        return cls(
            atr_value=round(atr, 4),
            suggested_quantity=qty,
            suggested_stop_loss=suggested_sl,
            suggested_take_profit=suggested_tp,
            max_expected_loss=round(qty * risk_per_share, 2),
            risk_per_trade_pct=round(risk_per_trade * 100, 1),
        )


class PreTradePreflightDTO(BaseModel):
    passed: bool
    allow_execute: bool
    risk_score: int = 0
    trade_amount: float = 0.0
    max_trade_amount: float = 0.0
    issues: list[PreTradeIssueDTO] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)
    suggested_quantity: int = 0
    atr_value: float = 0.0
    suggested_stop_loss: float = 0.0
    suggested_take_profit: float = 0.0
    max_expected_loss: float = 0.0
    risk_per_trade_pct: float = 0.0
    review_queued: bool = False
    review_decision_id: str = ""
