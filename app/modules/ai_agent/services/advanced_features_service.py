from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Advanced Features Package - 16-24高级功能合集.

包含：影子操盘、投研乐高、哨兵推送、深度年报审计、
全球套利、反向思维实验室、一键调仓、暗池监测"""


from datetime import datetime
from typing import Any


import logging
logger = logging.getLogger(__name__)


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


class ShadowMirroringService:
    """影子操盘服务 - 按大师风格结合行情与持仓给出差异化建议."""

    MASTERS = {
        "buffett": {"name": "巴菲特", "style": "价值投资", "criteria": "低PE高股息"},
        "lynch": {"name": "彼得·林奇", "style": "成长投资", "criteria": "高增长小市值"},
        "sorres": {"name": "索罗斯", "style": "趋势投资", "criteria": "顺势而为"},
    }

    def mirror_with_masters(
        self,
        symbols: list[str],
        *,
        quotes: list[dict[str, Any]] | None = None,
        holding_codes: list[str] | None = None,
        position_weights: dict[str, float] | None = None,
        investor_profile: dict[str, Any] | None = None,
        cost_basis: dict[str, dict[str, Any]] | None = None,
    ) -> GenericResponseDTO:
        """按大师风格对自选/持仓标的给出持有、减仓或观望建议。"""
        clean_symbols = [str(s).strip() for s in symbols if str(s).strip()][:24]
        quote_map: dict[str, dict[str, Any]] = {}
        for row in quotes or []:
            code = str(row.get("code") or row.get("symbol") or "").strip()
            if code:
                quote_map[code] = row
        holdings = {str(c).strip().upper() for c in (holding_codes or []) if str(c).strip()}
        weights = {
            str(k).strip().upper(): _safe_float(v)
            for k, v in (position_weights or {}).items()
            if str(k).strip()
        }
        profile = investor_profile or {}
        risk = str(profile.get("risk_level") or "balanced").lower()
        max_pos = _safe_float(profile.get("max_single_position_pct"), 15.0)
        heavy_threshold = min(25.0, max(12.0, max_pos * 1.35))
        costs = {
            str(k).strip().upper(): dict(v)
            for k, v in (cost_basis or {}).items()
            if str(k).strip()
        }

        results: list[dict[str, Any]] = []
        for master_id, master in self.MASTERS.items():
            picks: list[dict[str, Any]] = []
            for sym in clean_symbols:
                q = quote_map.get(sym) or quote_map.get(sym.upper()) or {}
                sym_key = sym.upper()
                weight_pct = weights.get(sym_key, 0.0)
                basis = costs.get(sym_key) or {}
                rec, logic = self._master_verdict(
                    master_id,
                    symbol=sym,
                    change_pct=_safe_float(q.get("change_pct")),
                    pe=_safe_float(q.get("pe") or q.get("pe_ttm")),
                    in_portfolio=sym_key in holdings,
                    name=str(q.get("name") or sym),
                    weight_pct=weight_pct,
                    risk_level=risk,
                    heavy_threshold=heavy_threshold,
                    pnl_pct=_safe_float(basis.get("pnl_pct")),
                    avg_cost=_safe_float(basis.get("avg_cost")),
                )
                picks.append(
                    {
                        "symbol": sym,
                        "name": q.get("name") or sym,
                        "recommendation": rec,
                        "logic": logic,
                        "change_pct": _safe_float(q.get("change_pct")),
                        "in_portfolio": sym_key in holdings,
                        "weight_pct": round(weight_pct, 2) if weight_pct > 0 else None,
                        "avg_cost": basis.get("avg_cost") or None,
                        "pnl_pct": basis.get("pnl_pct") if basis else None,
                    }
                )
            summary_rec, summary_logic = self._aggregate_master_view(master_id, picks)
            results.append(
                {
                    "master": master["name"],
                    "style": master["style"],
                    "recommendation": summary_rec,
                    "logic": summary_logic,
                    "picks": picks,
                }
            )

        return {
            "ok": True,
            "symbol_count": len(clean_symbols),
            "holding_overlap": len([s for s in clean_symbols if s.upper() in holdings]),
            "investor_profile": {
                "risk_level": risk,
                "horizon": profile.get("horizon"),
                "max_single_position_pct": max_pos,
            },
            "position_weights": {
                k: weights[k] for k in sorted(weights, key=weights.get, reverse=True)[:12]
            },
            "mirrors": results,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def _master_verdict(
        self,
        master_id: str,
        *,
        symbol: str,
        change_pct: float,
        pe: float,
        in_portfolio: bool,
        name: str,
        weight_pct: float = 0.0,
        risk_level: str = "balanced",
        heavy_threshold: float = 20.0,
        pnl_pct: float = 0.0,
        avg_cost: float = 0.0,
    ) -> tuple[str, str]:
        trim = "减仓"
        watch = "观望"
        add = "关注"
        heavy = weight_pct >= heavy_threshold
        weight_hint = f"（仓位约 {weight_pct:.1f}%）" if weight_pct > 0 else ""
        risk = (risk_level or "balanced").lower()
        chase_cut = 6.0 if risk == "aggressive" else 8.0 if risk == "balanced" else 10.0
        dip_cut = -4.0 if risk == "conservative" else -6.0
        cost_hint = ""
        if in_portfolio and avg_cost > 0:
            cost_hint = f" · 成本约 {avg_cost:.2f}，浮盈 {pnl_pct:+.1f}%"
        if in_portfolio and pnl_pct >= 28:
            return trim, f"{name}：浮盈较高{weight_hint}{cost_hint}，建议分批兑现锁定收益"
        if in_portfolio and pnl_pct <= -15 and risk != "aggressive":
            return trim, f"{name}：浮亏扩大{weight_hint}{cost_hint}，稳健型宜审视止损纪律"

        if master_id == "buffett":
            if pe > 35 and change_pct > chase_cut:
                msg = f"{name}：估值偏高(PE≈{pe:.0f})且短线涨幅大，价值派倾向获利了结"
                if heavy:
                    msg += f"{weight_hint}，重仓宜优先降敞口"
                return trim, msg
            if pe > 0 and pe < 18 and change_pct < -3:
                return add, f"{name}：估值合理且回调，可考虑分批布局（需核对股息与现金流）"
            if in_portfolio:
                return "持有", f"{name}：持仓中{weight_hint}，维持价值纪律，关注基本面是否恶化"
            return watch, f"{name}：未持仓，等待更好安全边际或财报确认"

        if master_id == "lynch":
            if change_pct > chase_cut + 4:
                msg = f"{name}：短线涨幅过大，成长猎手警惕情绪溢价"
                if heavy:
                    msg += f"{weight_hint}，建议分批兑现"
                return trim, msg
            if 3 < change_pct <= 12:
                return ("持有" if in_portfolio else add), f"{name}：趋势向上{weight_hint}，可跟踪业绩能否兑现"
            if change_pct < dip_cut - 2:
                return watch, f"{name}：急跌需区分杀估值还是逻辑破坏"
            return ("持有" if in_portfolio else watch), f"{name}：波动中性{weight_hint}，等待成长催化剂"

        # sorres — trend / macro style
        if change_pct > chase_cut - 2:
            return ("持有" if in_portfolio else add), f"{name}：动量偏强{weight_hint}，趋势跟随者可持有/轻仓试多"
        if change_pct < dip_cut:
            msg = f"{name}：跌破短期动能，对冲思维下宜减仓或止损"
            if heavy:
                msg += f"{weight_hint}，优先处理高仓位"
            return trim, msg
        return watch, f"{name}：方向不明{weight_hint}，等待突破信号"

    @staticmethod
    def _aggregate_master_view(
        master_id: str,
        picks: list[dict[str, Any]],
    ) -> tuple[str, str]:
        if not picks:
            return "观望", "暂无标的，请先添加自选股"
        trim_n = sum(1 for p in picks if p.get("recommendation") == "减仓")
        add_n = sum(1 for p in picks if p.get("recommendation") in ("关注",))
        hold_n = sum(1 for p in picks if p.get("recommendation") == "持有")
        trim_weight = sum(
            float(p.get("weight_pct") or 0)
            for p in picks
            if p.get("recommendation") == "减仓"
        )
        if trim_weight >= 35:
            return "组合偏防守", f"减仓建议涉及约 {trim_weight:.0f}% 仓位，优先处理重仓标的"
        if trim_n >= max(2, len(picks) // 2):
            return "组合偏防守", f"多数标的建议减仓({trim_n}/{len(picks)})，控制回撤优先"
        if add_n >= 2:
            return "组合偏进攻", f"多只标的可关注/试仓({add_n}/{len(picks)})，注意分散"
        if hold_n >= len(picks) // 2:
            return "组合持有", f"以持有为主({hold_n}/{len(picks)})，纪律性调仓"
        return "组合观望", "标的信号分化，宜降低换手、等待主线清晰"


class QuantLegoService:
    """投研乐高服务 - 可视化拖拽选股."""

    def parse_natural_language(
        self,
        query: str,
    ) -> GenericResponseDTO:
        """将自然语言转换为筛选条件."""
        criteria = {"conditions": [], "logical_operator": "AND"}

        if "金叉" in query:
            criteria["conditions"].append({"field": "macd_signal", "operator": ">", "value": 0})
        if "PE" in query:
            if "<" in query:
                pe_val = 20
                try:
                    pe_val = int("".join(filter(str.isdigit, query.split("PE")[1].split(",")[0])))
                except (ValueError, IndexError) as e:
                    logger.warning("advanced_features_service.py.parse_natural_language: %s", e)
                criteria["conditions"].append({"field": "pe", "operator": "<", "value": pe_val})

        return criteria

    def build_lego_blocks(
        self,
        criteria: dict,
    ) -> list[dict]:
        """构建乐高积木块."""
        blocks = []
        for cond in criteria.get("conditions", []):
            blocks.append(
                {
                    "type": "filter",
                    "field": cond.get("field"),
                    "operator": cond.get("operator"),
                    "value": cond.get("value"),
                }
            )
        return blocks
