from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
from datetime import datetime
from typing import Any, Dict, List, Optional
from ..base import BaseApplicationService
from app.domain.sniper_entities import SniperSelection, MarketRegime

class TenKingsSniperService(BaseApplicationService):
    """天王狙击系统指挥中心：协调 7+1 Agent 与 10 大天王策略。"""

    def __init__(
        self,
        repo: object,
        market_service: object,
        strategy_service: object,
        ai_service: object,
        regime_manager: object,
        total_capital: float = 500000.0
    ):
        super().__init__()
        self._repo = repo
        self._market = market_service
        self._strategy = strategy_service
        self._ai = ai_service
        self._regime = regime_manager
        self._total_capital = total_capital

    async def run_daily_scan(self) -> GenericResponseDTO:
        """执行每日狙击扫描。"""
        self.logger.info("启动天王狙击系统扫描...")
        
        # 1. 判定市场状态 (Regime Analysis)
        regime_enum = self._regime.get_market_regime()
        regime_val = regime_enum.value
        self.logger.info(f"当前市场状态判定为: {regime_val}")

        # 2. 确定武器库 (Weapon Array)
        strategies = self._get_strategies_by_regime(regime_enum)
        
        # 3. 初始池筛选 (全 A 扫描)
        candidates = []
        for strat in strategies:
            try:
                # 调用现有的策略服务，如果策略未实现则跳过
                res = self._strategy.select_stocks(strat, "CN", top_n=10)
                for item in res.get("candidates", []):
                    item["strategy_origin"] = strat
                    candidates.append(item)
            except Exception as e:
                self.logger.warning(f"策略 {strat} 执行失败或未实现: {e}")
        
        if not candidates:
            self.logger.info("全 A 扫描未发现符合天王策略的标的。")
            return {"ok": True, "message": "未发现符合天王策略的标的", "count": 0}

        # 4. 7+1 AI 投委会评审 (Multi-Agent Consensus)
        # 异步调用投委会评审逻辑
        committee_results = await self._ai.run_committee_debate(candidates, regime_val)
        
        # 5. 模拟盘入场 (Execution)
        final_picks = committee_results.get("final_picks", [])[:5]
        # ... (后续入场记录代码保持不变)
        new_positions = []
        for pick in final_picks:
            # 资金管理：平分 50w，每只标的 10w
            entry_price = pick.get("price")
            if not entry_price: continue
            
            shares = int((self._total_capital / 5) / (entry_price * 100)) * 100
            if shares == 0: continue
            
            selection = SniperSelection(
                symbol=pick["code"],
                name=pick["name"],
                strategy_name=pick["strategy_origin"],
                regime=regime_enum,
                commander_reason=pick.get("reason", ""),
                agent_consensus=pick.get("agent_details", {}),
                initial_price=entry_price,
                current_price=entry_price,
                shares=shares,
                stop_loss=entry_price * 0.93, # 默认 7% 止损
                take_profit=entry_price * 1.15 # 默认 15% 止盈
            )
            id = self._repo.save(selection)
            new_positions.append(pick["code"])
            
        return {"ok": True, "count": len(new_positions), "picks": new_positions}

    def list_active_holdings(self) -> List[SniperSelection]:
        """当前持仓（供 API 层使用，避免直接访问仓储）。"""
        return self._repo.list_active()

    def get_selection_detail(self, selection_id: int) -> Optional[Dict[str, Any]]:
        """按 ID 获取选股记录摘要；不存在返回 None。"""
        getter = getattr(self._repo, "get_selection_summary", None)
        if callable(getter):
            return getter(selection_id)
        return None

    def track_positions(self):
        """持续追踪持仓盈亏与止损止盈。"""
        active = self._repo.list_active()
        for pos in active:
            quote = self._market.get_quote(pos.symbol)
            if not quote: continue
            
            curr_price = float(quote.get("price", pos.current_price))
            pnl_amount = (curr_price - pos.initial_price) * pos.shares
            pnl_pct = (curr_price / pos.initial_price - 1) * 100
            
            status = "holding"
            if curr_price <= pos.stop_loss:
                status = "sold_loss"
            elif curr_price >= pos.take_profit:
                status = "sold_win"
                
            self._repo.update_status(pos.id, curr_price, status, pnl_amount, pnl_pct)

    def _map_regime(self, data: object) -> MarketRegime:
        # 逻辑：根据 regime_manager 的输出映射到三色状态
        # 简化版：如果 data 包含 bull 则牛，bear 则熊，否则震荡
        s = str(data).lower()
        if "bull" in s: return MarketRegime.BULL
        if "bear" in s: return MarketRegime.BEAR
        return MarketRegime.SIDEWAYS

    def _get_strategies_by_regime(self, regime: MarketRegime) -> List[str]:
        if regime == MarketRegime.BULL:
            return ["MinerviniVCPStrategy", "ProGapMomentumStrategy", "IchimokuCloudStrategy"]
        if regime == MarketRegime.BEAR:
            return ["ConnorsRSI2Strategy", "VSAStoppingVolumeStrategy", "Sperandeo2BReversalStrategy"]
        return ["TTMSqueezeBreakoutStrategy", "VWAPPullbackStrategy", "SuperTrendStrategy", "BollingerRSIReversionStrategy"]
