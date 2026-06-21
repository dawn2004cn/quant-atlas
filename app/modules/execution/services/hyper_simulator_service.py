from __future__ import annotations
"""Hyper-Simulator — Monte Carlo + Backtest fusion (Quant Atlas 9.0 Step Three)."""

import json
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from app.core.logger import get_logger
from app.domain.enums import MarketCode
from app.domain.simulation.hyper_sim_schema import HyperSimEvidence, HyperSimRunRequest
from app.domain.simulation.monte_carlo_engine import (
    estimate_drift_vol,
    monte_carlo_permutation,
    simulate_gbm_paths,
)

logger = get_logger(__name__)

_MODES = [
    {"id": "backtest_mc", "label": "回测 + 交易序 Monte Carlo", "description": "先跑策略回测，再对成交序列做置换检验"},
    {"id": "price_path", "label": "GBM 价格路径", "description": "基于历史波动率模拟未来财富分布与 VaR/CVaR"},
    {"id": "combined", "label": "组合模式", "description": "回测 MC + GBM 路径双轨输出"},
]


class HyperSimulatorService:
    """Fuse StrategyApplicationService backtest with Monte Carlo validation."""

    def __init__(
        self,
        *,
        strategy_service: Any | None = None,
        tool_facade_service: Any | None = None,
        simulation_gateway_service: Any | None = None,
        store_path: str | Path | None = None,
    ) -> None:
        self._strategy = strategy_service
        self._facade = tool_facade_service
        self._war_room = simulation_gateway_service
        root = Path(__file__).resolve().parents[4]
        default_store = root / "instance" / "hyper_sim" / "runs.jsonl"
        self._store_path = Path(store_path) if store_path else default_store
        self._store_path.parent.mkdir(parents=True, exist_ok=True)

    def get_manifest(self) -> dict[str, Any]:
        return {
            "ok": True,
            "modes": _MODES,
            "max_simulations": 20_000,
            "default_mode": "combined",
            "backtest_linked": self._strategy is not None or self._facade is not None,
            "war_room_linked": self._war_room is not None,
        }

    def list_recent(self, user_id: int, *, limit: int = 20) -> dict[str, Any]:
        rows = self._read_runs(user_id=user_id, limit=limit)
        return {"ok": True, "runs": rows, "count": len(rows)}

    def run(self, user_id: int, request: HyperSimRunRequest) -> dict[str, Any]:
        run_id = str(uuid.uuid4())
        symbol = request.symbol.strip()
        if not symbol:
            return {"ok": False, "error": "symbol_required"}

        market = self._parse_market(request.market)
        start, end = self._resolve_period(request)
        backtest_block: dict[str, Any] | None = None
        monte_carlo_block: dict[str, Any] | None = None
        price_paths_block: dict[str, Any] | None = None
        war_room_block: dict[str, Any] | None = None

        pnls: list[float] = []
        if request.mode in ("backtest_mc", "combined"):
            backtest_block = self._run_backtest(
                symbol=symbol,
                market=market,
                strategy_name=request.strategy_name,
                start=start,
                end=end,
                initial_capital=request.initial_capital,
                params=request.params,
            )
            if backtest_block.get("ok"):
                pnls = self._extract_pnls(backtest_block.get("result") or {})
                if pnls:
                    monte_carlo_block = monte_carlo_permutation(
                        pnls,
                        initial_capital=request.initial_capital,
                        n_simulations=request.n_simulations,
                        seed=request.seed,
                    )
                else:
                    monte_carlo_block = {"error": "no_trades_for_monte_carlo", "n_trades": 0}

        if request.mode in ("price_path", "combined"):
            closes = self._fetch_closes(symbol, market, start, end)
            mu, sigma = estimate_drift_vol(closes)
            s0 = closes[-1] if closes else request.initial_capital
            price_paths_block = simulate_gbm_paths(
                s0=float(s0),
                mu=mu,
                sigma=sigma,
                horizon_days=request.horizon_days,
                n_paths=min(request.n_simulations, 10_000),
                seed=request.seed,
            )

        if request.inject_war_room and self._war_room is not None and request.scenario_id:
            war_room_block = self._overlay_war_room(user_id, request, price_paths_block)

        evidence = self._build_evidence(
            request,
            backtest_block=backtest_block,
            monte_carlo=monte_carlo_block,
            price_paths=price_paths_block,
        )
        payload = {
            "ok": True,
            "run_id": run_id,
            "symbol": symbol,
            "market": market.value,
            "mode": request.mode,
            "period": {"start": start, "end": end},
            "backtest": backtest_block,
            "monte_carlo": monte_carlo_block,
            "price_paths": price_paths_block,
            "war_room_overlay": war_room_block,
            "evidence": evidence.evidence,
            "confidence": evidence.confidence,
            "sources": evidence.sources,
        }
        self._append_run(user_id, payload)
        return payload

    def _run_backtest(
        self,
        *,
        symbol: str,
        market: MarketCode,
        strategy_name: str,
        start: str,
        end: str,
        initial_capital: float,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        merged = {**(params or {}), "start": start, "end": end, "initial_capital": initial_capital}
        try:
            if self._facade is not None:
                result, note = self._facade.run_backtest(
                    strategy_name=strategy_name,
                    ticker=symbol,
                    market=market,
                    params=merged,
                )
                return {"ok": bool(result.get("ok", True) and "error" not in result), "result": result, "note": note}
            if self._strategy is not None:
                raw = self._strategy.backtest(
                    symbol=symbol,
                    strategy_name=strategy_name,
                    start=start,
                    end=end,
                    initial_capital=initial_capital,
                )
                if isinstance(raw, dict):
                    err = raw.get("error")
                    return {"ok": err is None, "result": raw, "note": "strategy_service.backtest"}
                return {"ok": True, "result": getattr(raw, "__dict__", raw), "note": "strategy_service.backtest"}
        except Exception as exc:  # noqa: BLE001
            logger.warning("hyper_sim backtest failed: %s", exc)
            return {"ok": False, "error": str(exc)}
        return {"ok": False, "error": "backtest_provider_unavailable"}

    def _fetch_closes(self, symbol: str, market: MarketCode, start: str, end: str) -> list[float]:
        try:
            from app.modules.system.services.helpers.market_data_provider import get_market_data_provider

            provider = get_market_data_provider()
            history = provider.get_stock_history(symbol, market, start, end)
            closes: list[float] = []
            for row in history or []:
                for key in ("close", "Close", "收盘"):
                    if key in row and row[key] is not None:
                        closes.append(float(row[key]))
                        break
            return closes
        except Exception as exc:  # noqa: BLE001
            logger.debug("hyper_sim fetch_closes: %s", exc)
            return []

    def _overlay_war_room(
        self,
        user_id: int,
        request: HyperSimRunRequest,
        price_paths: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        presets = (self._war_room.list_scenarios() or {}).get("presets") or []
        preset = next((p for p in presets if p.get("id") == request.scenario_id), None)
        if preset is None:
            return {"ok": False, "error": "scenario_not_found"}
        from app.domain.simulation_scenario import SimulationScenario, WarRoomRunRequest

        scenario = SimulationScenario.from_preset(preset)
        notional = float((price_paths or {}).get("terminal_p50") or request.initial_capital)
        wr = WarRoomRunRequest(
            scenario=scenario,
            positions=[],
            cash=notional,
            use_watchlist_fallback=True,
            run_arbiter=False,
            inject_virtual_events=False,
        )
        try:
            out = self._war_room.run_war_room(user_id, wr)
            return {"ok": out.get("ok", False), "scenario_id": request.scenario_id, "portfolio": out.get("portfolio")}
        except Exception as exc:  # noqa: BLE001
            logger.warning("hyper_sim war_room overlay: %s", exc)
            return {"ok": False, "error": str(exc)}

    @staticmethod
    def _extract_pnls(result: dict[str, Any]) -> list[float]:
        trades = result.get("trades") or []
        pnls: list[float] = []
        for trade in trades:
            if not isinstance(trade, dict):
                continue
            raw = trade.get("pnl")
            if raw is None:
                raw = trade.get("profit") or trade.get("net_pnl") or 0
            try:
                pnls.append(float(raw))
            except (TypeError, ValueError):
                continue
        return pnls

    @staticmethod
    def _build_evidence(
        request: HyperSimRunRequest,
        *,
        backtest_block: dict[str, Any] | None,
        monte_carlo: dict[str, Any] | None,
        price_paths: dict[str, Any] | None,
    ) -> HyperSimEvidence:
        sources: list[str] = []
        parts: list[str] = []
        confidence = 0.55

        if backtest_block and backtest_block.get("ok"):
            sources.append("strategy_backtest")
            result = backtest_block.get("result") or {}
            metrics = result.get("metrics") or result
            sharpe = metrics.get("sharpe_ratio") or metrics.get("sharpe")
            if sharpe is not None:
                parts.append(f"回测 Sharpe={sharpe}")
            confidence += 0.1

        if monte_carlo and "error" not in monte_carlo:
            sources.append("monte_carlo_permutation")
            pval = monte_carlo.get("p_value_sharpe")
            parts.append(f"MC p-value(Sharpe)={pval}")
            if pval is not None and float(pval) < 0.05:
                confidence += 0.15
            elif pval is not None and float(pval) < 0.1:
                confidence += 0.08

        if price_paths and "error" not in price_paths:
            sources.append("gbm_price_paths")
            parts.append(
                f"GBM VaR95={price_paths.get('var_95')} CVaR95={price_paths.get('cvar_95')}"
            )
            confidence += 0.1

        if not parts:
            return HyperSimEvidence(
                evidence="Hyper-Simulator 未能收集足够证据，请检查标的数据或策略成交。",
                confidence=0.3,
                sources=sources,
            )
        return HyperSimEvidence(
            evidence=f"{request.symbol} {request.mode}: " + "; ".join(parts),
            confidence=min(0.95, round(confidence, 2)),
            sources=sources,
        )

    @staticmethod
    def _parse_market(raw: str) -> MarketCode:
        try:
            return MarketCode((raw or "CN").strip().upper())
        except ValueError:
            return MarketCode.CN

    @staticmethod
    def _resolve_period(request: HyperSimRunRequest) -> tuple[str, str]:
        end = (request.end or "").strip() or date.today().isoformat()
        start = (request.start or "").strip() or (date.today() - timedelta(days=365)).isoformat()
        return start, end

    def _append_run(self, user_id: int, payload: dict[str, Any]) -> None:
        row = {"user_id": user_id, **payload}
        try:
            with self._store_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        except Exception as exc:  # noqa: BLE001
            logger.warning("hyper_sim store append: %s", exc)

    def _read_runs(self, *, user_id: int, limit: int) -> list[dict[str, Any]]:
        if not self._store_path.exists():
            return []
        rows: list[dict[str, Any]] = []
        try:
            for line in self._store_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if int(row.get("user_id") or 0) != user_id:
                    continue
                rows.append(row)
        except Exception as exc:  # noqa: BLE001
            logger.warning("hyper_sim store read: %s", exc)
            return []
        rows.sort(key=lambda r: r.get("run_id", ""), reverse=True)
        return rows[:limit]


__all__ = ["HyperSimulatorService"]
