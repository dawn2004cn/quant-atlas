from __future__ import annotations

from app.domain.dto.service_result import GenericResponseDTO

"""Daily recommendation service for retail users."""








from datetime import datetime
from typing import Any

from app.core.logger import get_logger
from app.domain.enums import MarketCode

logger = get_logger(__name__)








def _safe_float(value: object, default: float = 0.0) -> float:


    try:


        return float(value or default)


    except (TypeError, ValueError):


        return default








class RecommendationService:


    """Compose daily Top-N recommendations from existing strategy evidence."""





    def __init__(


        self,


        *,


        selection_source_service: object,


        signal_flag_service: Any | None,


        trade_plan_service: object,


        ai_evidence_service: object,


        signal_observation_service: Any | None = None,


    ) -> None:


        self._selection = selection_source_service


        self._signal_flag = signal_flag_service


        self._trade_plan = trade_plan_service


        self._ai_evidence = ai_evidence_service


        self._observations = signal_observation_service





    def daily_top(


        self,


        *,


        market: MarketCode = MarketCode.CN,


        top_n: int = 3,


        account_equity: float = 100000.0,


        user_id: int | None = None,


    ) -> GenericResponseDTO:


        """Return daily Top-N actionable recommendations."""


        top_n = max(1, min(int(top_n or 3), 5))


        candidates = self._candidate_rows(market, limit=max(top_n * 4, 12))


        staged: list[tuple[float, dict[str, Any]]] = []


        for row in candidates:


            code = str(row.get("code") or row.get("symbol") or "").strip()


            if not code:


                continue


            try:


                trade_plan = self._trade_plan.build_plan(


                    symbol=code,


                    market=market,


                    account_equity=account_equity,


                    cash_available=account_equity,


                    risk_per_trade_pct=1.0,


                    max_position_pct=15.0,


                    entry_price=_safe_float(row.get("price")) or None,


                )


            except Exception as exc:


                logger.warning("recommendation trade plan failed for %s: %s", code, exc)


                continue


            evidence = self._safe_evidence(code, market)


            agent_cal = self._agent_calibration(code)


            composite_score = self._score(row, evidence, agent_cal)


            plan_dict = trade_plan.model_dump() if hasattr(trade_plan, "model_dump") else {}


            plan = plan_dict.get("plan") or {}


            core_logic = self._core_logic(row, evidence)


            industry_position = self._industry_position(row)


            item = {


                "code": code,


                "name": row.get("name") or plan_dict.get("name") or code,


                "market": market.value,


                "industry": row.get("industry") or industry_position.get("industry") or "",


                "source": row.get("source") or "recommendation",


                "score": composite_score,


                "agent_calibration": agent_cal,


                "one_line_verdict": self._one_line_verdict(row, core_logic, evidence),


                "core_logic": core_logic,


                "industry_position": industry_position,


                "buy_zone": {


                    "low": round(_safe_float(plan.get("entry_price")) * 0.985, 2),


                    "high": round(_safe_float(plan.get("entry_price")) * 1.015, 2),


                },


                "stop_loss": plan.get("stop_loss"),


                "take_profit_1": plan.get("take_profit_1"),


                "target_price": plan.get("target_price"),


                "risk_reward_ratio": plan.get("risk_reward_ratio"),


                "recommended_shares": plan.get("recommended_shares"),


                "position_weight_pct": plan.get("position_weight_pct"),


                "estimated_win_rate": self._estimated_win_rate(


                    code, agent_cal, user_id=user_id


                ),


                "evidence": {


                    "trust": evidence.get("trust", {}),


                    "calibration": evidence.get("calibration", {}),


                    "signals": row.get("signal_strategies") or row.get("buy_signals") or [],


                },


                "links": {


                    "detail": f"/stock/{code}?m={market.value}",


                    "decision_brief": f"/stock/{code}?m={market.value}#decision-brief-strip",


                    "trade_plan": f"/stock/{code}?m={market.value}#section-trade-plan",


                    "diagnosis": f"/ai-analysis?symbol={code}&market={market.value}",


                    "industry_chain": f"/stock/{code}?m={market.value}#section-industry-chain",


                },


            }


            staged.append((composite_score, item))


        staged.sort(key=lambda pair: pair[0], reverse=True)


        items = []


        for rank, (_score_val, item) in enumerate(staged[:top_n], start=1):


            item["rank"] = rank


            items.append(item)


        return {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "market": market.value,
            "top_n": top_n,
            "items": items,
            "disclaimer": "For research purposes only. Not investment advice.",
        }

    def _candidate_rows(self, market: MarketCode, *, limit: int) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if self._signal_flag is not None and market == MarketCode.CN:
            try:
                pool_date = datetime.now().strftime("%Y-%m-%d")
                pool = self._signal_flag.get_pool(pool_date) or []
                if isinstance(pool, dict):
                    rows = []
                    return rows
                for item in pool:
                    code = str(item.get("code") or item.get("symbol") or "").strip()
                    if not code:
                        continue
                    rows.append(
                        {
                            "code": code,
                            "name": item.get("name") or code,
                            "score": item.get("score"),
                            "safety_score": item.get("safety_score") or item.get("score"),
                            "amount": item.get("amount"),
                            "industry": item.get("industry"),
                            "source": "signal_flag",
                            "signal_strategies": item.get("signal_strategies")
                            or item.get("buy_signals"),
                            "price": item.get("price") or item.get("current_price"),
                        }
                    )
            except Exception as exc:
                logger.warning("recommendation signal_flag pool: %s", exc)

        if not rows:
            try:
                selected = self._selection.select_stocks(
                    strategy="horizon:mid",
                    market=market,
                    top_n=limit,
                    data_source="legacy",
                    enable_qlib=False,
                )
                rows = list(selected.get("candidates") or [])
                for row in rows:
                    row.setdefault("source", "selection")
            except Exception as exc:
                logger.warning("recommendation selection fallback unavailable: %s", exc)

        rows.sort(
            key=lambda x: (
                _safe_float(x.get("safety_score") or x.get("score")),
                _safe_float(x.get("amount")),
            ),
            reverse=True,
        )
        return rows[:limit]

    def _safe_evidence(self, code: str, market: MarketCode) -> GenericResponseDTO:


        try:


            return self._ai_evidence.build_bundle(symbol=code, market=market, include_news=True)


        except Exception as exc:


            logger.warning("recommendation evidence failed for %s: %s", code, exc)


            return {"trust": {"score": 0, "level": ""}, "calibration": {}}





    def _agent_calibration(self, code: str) -> dict[str, Any]:


        """Blend AutoValidator agent-memory accuracy into ranking."""


        try:


            from app.agents.agent_memory import get_agent_memory





            patterns = get_agent_memory().get_historical_patterns(code)


            if patterns.get("pattern") == "insufficient_data":


                return {"boost": 0.0, "samples": 0, "avg_accuracy": 0.0, "source": "auto_validator"}


            samples = int(patterns.get("total_decisions") or 0)


            avg_accuracy = float(patterns.get("avg_accuracy") or 0.5)


            boost = round((avg_accuracy - 0.5) * 14.0, 2) if samples >= 2 else 0.0


            return {


                "boost": boost,


                "samples": samples,


                "avg_accuracy": round(avg_accuracy, 4),


                "source": "auto_validator",


            }


        except Exception as exc:


            logger.debug("recommendation agent calibration %s: %s", code, exc)


            return {"boost": 0.0, "samples": 0, "avg_accuracy": 0.0, "source": "auto_validator"}





    def _score(


        self,


        row: dict[str, Any],


        evidence: dict[str, Any],


        agent_cal: dict[str, Any] | None = None,


    ) -> float:


        base = _safe_float(row.get("safety_score") or row.get("score"), 50)


        trust = _safe_float((evidence.get("trust") or {}).get("score"), 50)


        composite = base * 0.65 + trust * 0.35


        boost = _safe_float((agent_cal or {}).get("boost"), 0.0)


        return round(composite + boost, 2)





    def _core_logic(self, row: dict[str, Any], evidence: dict[str, Any]) -> list[str]:


        logic = []


        signals = row.get("signal_strategies") or row.get("buy_signals") or []


        if signals:


            names = []


            for item in signals[:3]:


                if isinstance(item, dict):


                    names.append(str(item.get("name") or item.get("id") or item))


                else:


                    names.append(str(item))


            logic.append(", ".join(names))


        change = _safe_float(row.get("change_pct"))


        if change:


            logic.append(f"?{change:+.2f}%")


        for reason in (evidence.get("trust") or {}).get("reasons", [])[:2]:


            logic.append(str(reason))


        return logic[:4] or [""]





    @staticmethod


    def _one_line_verdict(


        row: dict[str, Any],


        core_logic: list[str],


        evidence: dict[str, Any],


    ) -> str:


        name = str(row.get("name") or row.get("code") or "")


        change = _safe_float(row.get("change_pct"))


        trust = (evidence.get("trust") or {}).get("level") or "medium"


        hook = core_logic[0] if core_logic else ""


        if change:


            return f"{name}{hook}{change:+.2f}%{trust}"


        return f"{name}{hook} {trust}"





    def _industry_position(self, row: dict[str, Any]) -> dict[str, str]:


        industry = str(row.get("industry") or "")


        chain_name = industry


        position = "unknown"


        upstream_hint = ""


        downstream_hint = ""


        try:


            from app.modules.market_data.services.industry_chain_map_service import (
                INDUSTRY_CHAIN_CONFIG,
                IndustryChainAnalyzer,
            )





            matched_key = None


            for key, cfg in INDUSTRY_CHAIN_CONFIG.items():


                name = str(cfg.get("name") or "")


                if industry == key or industry == name or key in industry or industry in key:


                    matched_key = key


                    break


            if matched_key:


                cfg = INDUSTRY_CHAIN_CONFIG[matched_key]


                chain_name = str(cfg.get("name") or matched_key)


                up = IndustryChainAnalyzer.get_upstream(matched_key)[:3]


                down = IndustryChainAnalyzer.get_downstream(matched_key)[:3]


                upstream_hint = ", ".join(up) if up else ""


                downstream_hint = ", ".join(down) if down else ""


                position = f" {upstream_hint} -> {chain_name} -> {downstream_hint}"


        except Exception as exc:


            logger.debug("recommendation industry chain map: %s", exc)


        return {


            "industry": industry,


            "chain_name": chain_name,


            "position": position,


            "opportunity": f" {chain_name} ecosystem",


            "linkage": f"{upstream_hint or ''}  {downstream_hint or ''}",


        }





    def _estimated_win_rate(


        self,


        code: str,


        agent_cal: dict[str, Any] | None = None,


        *,


        user_id: int | None = None,


    ) -> GenericResponseDTO:


        base: dict[str, Any] = {"rate": 0.0, "samples": 0, "source": "no_observation_data"}


        if self._observations is not None:


            try:


                uid = int(user_id) if user_id else 1


                rows = self._observations.list_observations(


                    user_id=uid, status="all", refresh=True


                ).get("items") or []


            except Exception:


                rows = []


            matched = [r for r in rows if str(r.get("symbol") or "").upper() == code.upper()]


            if matched:


                wins = len(


                    [


                        r


                        for r in matched


                        if _safe_float(r.get("return_pct")) > 0


                        or r.get("trigger_status") == "target_hit"


                    ]


                )


                base = {


                    "rate": round(wins / len(matched) * 100, 2),


                    "samples": len(matched),


                    "source": "symbol_observation",


                }


            else:


                stats = self._observations.stats().get("items") or []


                signal_stats = next(


                    (x for x in stats if x.get("source") in ("signal_flag", "daily_workbench")),


                    None,


                )


                base = {


                    "rate": signal_stats.get("target_hit_rate", 0) if signal_stats else 0,


                    "samples": signal_stats.get("count", 0) if signal_stats else 0,


                    "source": "source_level_observation",


                }


        cal = agent_cal or {}


        agent_samples = int(cal.get("samples") or 0)


        if agent_samples >= 2:


            agent_rate = round(float(cal.get("avg_accuracy") or 0.0) * 100, 2)


            obs_rate = _safe_float(base.get("rate"))


            obs_n = int(base.get("samples") or 0)


            if obs_n > 0:


                blended = round(obs_rate * 0.6 + agent_rate * 0.4, 2)


            else:


                blended = agent_rate


            base["rate"] = blended


            base["agent_accuracy_pct"] = agent_rate


            base["agent_samples"] = agent_samples


            base["source"] = f"{base.get('source', 'obs')}+auto_validator"


        return base


