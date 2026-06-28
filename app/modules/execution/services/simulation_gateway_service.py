from __future__ import annotations

"""SimulationGateway — virtual scenario injection and portfolio War Room stress tests."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.logger import get_logger
from app.domain.simulation_scenario import (
    SimulationScenario,
    SimulationScenarioType,
    WarRoomPosition,
    WarRoomRunRequest,
)

logger = get_logger(__name__)

_RATE_HIKE_SENSITIVITY: dict[str, float] = {
    "financial": 0.12,
    "finance": 0.12,
    "bank": 0.12,
    "金融": 0.12,
    "银行": 0.12,
    "technology": -0.60,
    "tech": -0.60,
    "科技": -0.60,
    "growth": -0.60,
    "real_estate": -0.48,
    "地产": -0.48,
    "房地产": -0.48,
    "consumer": -0.20,
    "消费": -0.20,
    "default": -0.32,
}

_SCENARIO_PRESETS: list[dict[str, Any]] = [
    {
        "id": "rate_hike_50bp",
        "label": "加息 50bp",
        "scenario_type": "rate_hike",
        "rate_hike_bps": 50,
        "description": "模拟央行意外加息 50 个基点，成长板块承压、金融相对受益。",
    },
    {
        "id": "market_crash_8pct",
        "label": "全市场急跌 -8%",
        "scenario_type": "market_shock",
        "market_shock_pct": -8.0,
        "description": "宽基指数单日暴跌 8%，按持仓 beta 加权冲击估值。",
    },
    {
        "id": "sector_tech_swan",
        "label": "科技板块黑天鹅 -25%",
        "scenario_type": "sector_black_swan",
        "sector": "科技",
        "sector_shock_pct": -25.0,
        "contagion_pct": -3.0,
        "description": "科技板块监管/业绩黑天鹅，其余板块受 contagion 拖累。",
    },
    {
        "id": "vol_spike_2x",
        "label": "波动率飙升 ×2",
        "scenario_type": "volatility_spike",
        "volatility_multiplier": 2.0,
        "description": "VIX 式波动率翻倍，高 beta 持仓估值折损加剧。",
    },
    {
        "id": "custom_hypothesis",
        "label": "自定义假设",
        "scenario_type": "custom_hypothesis",
        "hypothesis_text": "若美联储维持高利率更久，A股外资流出加速",
        "description": "文本假设驱动 Agent 重估，不施加数值冲击。",
    },
]


class SimulationGatewayService:
    """Inject virtual macro events and revalue holdings under counterfactual stress."""

    def __init__(
        self,
        *,
        portfolio_service: Any | None = None,
        watchlist_service: Any | None = None,
        swarm_arbiter_service: Any | None = None,
        store_path: str | Path | None = None,
    ) -> None:
        self._portfolio = portfolio_service
        self._watchlist = watchlist_service
        self._arbiter = swarm_arbiter_service
        root = Path(__file__).resolve().parents[4]
        default_store = root / "instance" / "war_room" / "runs.jsonl"
        self._store_path = Path(store_path) if store_path else default_store
        self._store_path.parent.mkdir(parents=True, exist_ok=True)

    def list_scenarios(self) -> dict[str, Any]:
        return {"ok": True, "presets": list(_SCENARIO_PRESETS)}

    def list_recent_runs(self, user_id: int, *, limit: int = 20) -> dict[str, Any]:
        rows = self._read_runs(user_id=user_id, limit=limit)
        return {"ok": True, "runs": rows, "count": len(rows)}

    def run_war_room(self, user_id: int, request: WarRoomRunRequest) -> dict[str, Any]:
        scenario = request.scenario
        positions = self._resolve_positions(user_id, request)
        if not positions:
            return {"ok": False, "error": "no_positions", "hint": "提供 positions 或开启 use_watchlist_fallback"}

        valued = self._value_positions(positions, cash=request.cash)
        stressed = self._apply_scenario_shocks(valued, scenario)
        portfolio = self._aggregate_portfolio(stressed, cash=request.cash)

        injected: list[dict[str, Any]] = []
        if request.inject_virtual_events:
            injected = self._inject_virtual_events(scenario, stressed)

        arbiter_views: list[dict[str, Any]] = []
        if request.run_arbiter and self._arbiter is not None:
            arbiter_views = self._run_arbiter_pass(
                stressed,
                scenario,
                top_n=request.arbiter_top_n,
            )

        run_id = str(uuid.uuid4())
        risk_grade = self._risk_grade(portfolio.get("delta_pct", 0.0))
        result = {
            "ok": True,
            "run_id": run_id,
            "user_id": user_id,
            "scenario": scenario.model_dump(),
            "scenario_label": scenario.display_label(),
            "portfolio": portfolio,
            "positions": stressed,
            "virtual_events_injected": len(injected),
            "injected_events": injected,
            "arbiter_views": arbiter_views,
            "risk_grade": risk_grade,
            "recommendations": self._build_recommendations(portfolio, stressed, risk_grade),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._append_run(user_id, result)
        logger.info(
            "War room run user=%s scenario=%s delta_pct=%.2f risk=%s",
            user_id,
            scenario.scenario_type.value,
            portfolio.get("delta_pct", 0.0),
            risk_grade,
        )
        return result

    def _resolve_positions(self, user_id: int, request: WarRoomRunRequest) -> list[WarRoomPosition]:
        if request.positions:
            return list(request.positions)
        if not request.use_watchlist_fallback or self._watchlist is None:
            return []
        try:
            symbols = self._watchlist.list_symbols(user_id)
        except Exception as exc:
            logger.warning("war_room watchlist fallback failed: %s", exc)
            return []
        if not symbols:
            return []
        return [
            WarRoomPosition(symbol=sym, shares=100.0, sector=None, beta=1.0)
            for sym in symbols[:20]
        ]

    def _value_positions(
        self,
        positions: list[WarRoomPosition],
        *,
        cash: float,
    ) -> list[dict[str, Any]]:
        symbols = [p.symbol for p in positions]
        quote_map: dict[str, Any] = {}
        if self._portfolio is not None and symbols:
            try:
                from app.domain.enums import MarketCode

                quotes = self._portfolio._market_provider.get_realtime_quotes(
                    symbols=symbols,
                    market=MarketCode.CN,
                )
                quote_map = {q.code.lower(): q for q in quotes}
            except Exception as exc:
                logger.warning("war_room quote fetch failed: %s", exc)

        rows: list[dict[str, Any]] = []
        for pos in positions:
            sym = pos.symbol
            q = quote_map.get(sym)
            price = pos.current_price
            if price is None and q is not None:
                price = float(q.price)
            if price is None:
                price = 10.0
            value = pos.current_value
            if value is None:
                value = float(pos.shares) * float(price)
            rows.append(
                {
                    "symbol": sym,
                    "shares": pos.shares,
                    "sector": pos.sector,
                    "beta": pos.beta,
                    "current_price": round(float(price), 4),
                    "base_value": round(float(value), 2),
                    "stressed_value": round(float(value), 2),
                    "shock_pct": 0.0,
                    "shock_reason": "baseline",
                }
            )
        _ = cash
        return rows

    def _apply_scenario_shocks(
        self,
        positions: list[dict[str, Any]],
        scenario: SimulationScenario,
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for row in positions:
            shock_pct, reason = self._shock_for_position(row, scenario)
            base = float(row["base_value"])
            stressed = base * (1.0 + shock_pct / 100.0)
            out.append(
                {
                    **row,
                    "stressed_value": round(stressed, 2),
                    "shock_pct": round(shock_pct, 4),
                    "shock_reason": reason,
                }
            )
        return out

    def _shock_for_position(
        self,
        row: dict[str, Any],
        scenario: SimulationScenario,
    ) -> tuple[float, str]:
        sector = (row.get("sector") or "default").strip().lower()
        beta = float(row.get("beta") or 1.0)

        if scenario.scenario_type == SimulationScenarioType.CUSTOM_HYPOTHESIS:
            return 0.0, "hypothesis_only"

        if scenario.scenario_type == SimulationScenarioType.MARKET_SHOCK:
            pct = float(scenario.market_shock_pct or 0.0)
            applied = pct * beta
            return applied, f"market_shock beta={beta}"

        if scenario.scenario_type == SimulationScenarioType.RATE_HIKE:
            bps = int(scenario.rate_hike_bps or 25)
            unit = bps / 25.0
            sens = _RATE_HIKE_SENSITIVITY.get(sector, _RATE_HIKE_SENSITIVITY["default"])
            applied = sens * unit * beta
            return applied, f"rate_hike {bps}bp sector={sector}"

        if scenario.scenario_type == SimulationScenarioType.SECTOR_BLACK_SWAN:
            target = (scenario.sector or "").strip().lower()
            sector_hit = target and (target in sector or sector in target)
            if sector_hit:
                pct = float(scenario.sector_shock_pct or -20.0)
                return pct * beta, f"sector_black_swan hit={scenario.sector}"
            contagion = float(scenario.contagion_pct or -2.0)
            return contagion * beta, "sector_contagion"

        if scenario.scenario_type == SimulationScenarioType.VOLATILITY_SPIKE:
            mult = float(scenario.volatility_multiplier or 1.5)
            penalty = -2.5 * (mult - 1.0) * beta
            return penalty, f"volatility_spike x{mult}"

        return 0.0, "unknown_scenario"

    def _aggregate_portfolio(
        self,
        positions: list[dict[str, Any]],
        *,
        cash: float,
    ) -> dict[str, Any]:
        base_total = sum(float(p["base_value"]) for p in positions) + cash
        stressed_total = sum(float(p["stressed_value"]) for p in positions) + cash
        delta_value = stressed_total - base_total
        delta_pct = (delta_value / base_total * 100.0) if base_total > 0 else 0.0
        return {
            "cash": round(cash, 2),
            "base_total": round(base_total, 2),
            "stressed_total": round(stressed_total, 2),
            "delta_value": round(delta_value, 2),
            "delta_pct": round(delta_pct, 4),
            "position_count": len(positions),
        }

    def _inject_virtual_events(
        self,
        scenario: SimulationScenario,
        positions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        try:
            from app.agents.research.debate_bus import publish_debate_round
        except Exception as exc:
            logger.warning("virtual event injection unavailable: %s", exc)
            return []

        brief = self._scenario_brief(scenario)
        injected: list[dict[str, Any]] = []
        sorted_pos = sorted(positions, key=lambda p: float(p.get("base_value") or 0), reverse=True)
        for idx, row in enumerate(sorted_pos[:5]):
            shock = float(row.get("shock_pct") or 0)
            role = "bear" if shock < -1.0 else "bull" if shock > 1.0 else "bull"
            chunk = (
                f"[WAR ROOM 虚拟事件] {brief} | 标的 {row['symbol']} "
                f"估值冲击 {shock:+.2f}% — 请全量重估持仓风险。"
            )
            publish_debate_round(
                ticker=row["symbol"],
                agent_role=role,
                chunk=chunk,
                round_num=900 + idx,
                debate_phase="war_room",
                market="CN",
            )
            injected.append({"symbol": row["symbol"], "agent_role": role, "shock_pct": shock})
        return injected

    def _run_arbiter_pass(
        self,
        positions: list[dict[str, Any]],
        scenario: SimulationScenario,
        *,
        top_n: int,
    ) -> list[dict[str, Any]]:
        if top_n <= 0 or self._arbiter is None:
            return []
        sorted_pos = sorted(positions, key=lambda p: float(p.get("base_value") or 0), reverse=True)
        views: list[dict[str, Any]] = []
        for row in sorted_pos[:top_n]:
            sym = str(row.get("symbol") or "").upper()
            if not sym:
                continue
            try:
                consensus = self._arbiter.consensus_only(sym, "CN", use_llm=False)
            except Exception as exc:
                logger.warning("war_room arbiter sym=%s: %s", sym, exc)
                consensus = {"ok": False, "error": str(exc)}
            views.append(
                {
                    "symbol": sym,
                    "shock_pct": row.get("shock_pct"),
                    "scenario": scenario.display_label(),
                    "consensus": consensus,
                }
            )
        return views

    def _scenario_brief(self, scenario: SimulationScenario) -> str:
        if scenario.scenario_type == SimulationScenarioType.CUSTOM_HYPOTHESIS:
            return scenario.hypothesis_text or "自定义宏观假设"
        return scenario.display_label()

    @staticmethod
    def _risk_grade(delta_pct: float) -> str:
        if delta_pct <= -15:
            return "critical"
        if delta_pct <= -8:
            return "high"
        if delta_pct <= -3:
            return "elevated"
        if delta_pct < 0:
            return "watch"
        return "stable"

    @staticmethod
    def _build_recommendations(
        portfolio: dict[str, Any],
        positions: list[dict[str, Any]],
        risk_grade: str,
    ) -> list[str]:
        recs: list[str] = []
        delta = float(portfolio.get("delta_pct") or 0)
        if delta <= -10:
            recs.append("组合在压力情景下回撤超 10%，建议降低高 beta 敞口或增加对冲。")
        elif delta <= -5:
            recs.append("中度压力回撤，关注集中度最高的持仓是否过度暴露。")
        worst = sorted(positions, key=lambda p: float(p.get("shock_pct") or 0))[:3]
        for row in worst:
            if float(row.get("shock_pct") or 0) < -5:
                recs.append(
                    f"{row['symbol']} 冲击 {row['shock_pct']:+.2f}%（{row.get('shock_reason')}），优先复核。"
                )
        if risk_grade == "critical":
            recs.append("风险等级 critical：建议触发 War Room 二次辩论或暂停加仓。")
        if not recs:
            recs.append("当前情景下组合韧性尚可，可维持观察。")
        return recs[:6]

    def _append_run(self, user_id: int, result: dict[str, Any]) -> None:
        record = {
            "user_id": user_id,
            "run_id": result.get("run_id"),
            "scenario_type": (result.get("scenario") or {}).get("scenario_type"),
            "scenario_label": result.get("scenario_label"),
            "delta_pct": (result.get("portfolio") or {}).get("delta_pct"),
            "risk_grade": result.get("risk_grade"),
            "created_at": result.get("created_at"),
        }
        try:
            with self._store_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.warning("war_room persist failed: %s", exc)

    def _read_runs(self, user_id: int, *, limit: int) -> list[dict[str, Any]]:
        if not self._store_path.exists():
            return []
        rows: list[dict[str, Any]] = []
        try:
            lines = self._store_path.read_text(encoding="utf-8").splitlines()
        except Exception as exc:
            logger.warning("war_room read failed: %s", exc)
            return []
        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if int(row.get("user_id") or 0) != user_id:
                continue
            rows.append(row)
            if len(rows) >= limit:
                break
        return rows


__all__ = ["SimulationGatewayService"]
