from __future__ import annotations

from app.domain.dto.service_result import GenericResponseDTO

"""Daily trading workbench application service.

Aggregates market, watchlist, signal flag, observations, reviews, recommendations,
task messages, integration stack and headlines into one snapshot for the home page.
"""


from datetime import datetime
from typing import Any

from app.core.logger import get_logger
from app.domain.dto.daily_workbench_dto import DailyWorkbenchSnapshotDTO
from app.domain.enums import MarketCode
from app.domain.services.market_regime_service import MarketRegimeService
from app.modules.strategy.services.analytics.headline_signal_enrichment_service import (
    HeadlineSignalEnrichmentService,
)

logger = get_logger(__name__)


def _to_dict(value: object) -> GenericResponseDTO:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return value if isinstance(value, dict) else {}


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


def _health_score_from_change(change_pct: object) -> int:
    ch = _safe_float(change_pct)
    raw = 55.0 + min(18.0, max(-18.0, ch * 2.8))
    return int(max(22, min(96, round(raw))))


class DailyWorkbenchService:
    """Assemble a single JSON snapshot for `/api/v1/daily-workbench`."""

    def __init__(
        self,
        *,
        market_service: object,
        watchlist_service: object,
        signal_flag_service: Any | None = None,
        fingpt_application_service: Any | None = None,
        signal_observation_service: Any | None = None,
        basic_market_data_service: Any | None = None,
        news_provider: Any | None = None,
        task_message_store: Any | None = None,
        integration_stack_service: Any | None = None,
        recommendation_service: Any | None = None,
        review_tracking_service: Any | None = None,
        trade_plan_service: Any | None = None,
        headline_signal_enrichment_service: Any | None = None,
        health_banner_service: Any | None = None,
          market_regime_service: Any | None = None,
    ) -> None:
        self._market_service = market_service
        self._watchlist_service = watchlist_service
        self._signal_flag_service = signal_flag_service
        self._fingpt_application_service = fingpt_application_service
        self._signal_observation_service = signal_observation_service
        self._basic_market_data_service = basic_market_data_service
        self._news_provider = news_provider
        self._task_message_store = task_message_store
        self._integration_stack_service = integration_stack_service
        self._recommendation_service = recommendation_service
        self._review_tracking_service = review_tracking_service
        self._trade_plan_service = trade_plan_service
        self._headline_signal = headline_signal_enrichment_service or HeadlineSignalEnrichmentService()
        self._health_banner_service = health_banner_service
        self._market_regime_service = market_regime_service or MarketRegimeService()
        self._recommendation_service_alias: Any = None

    def set_recommendation_service(self, service: object) -> None:
        self._recommendation_service_alias = service

    def build_snapshot(
        self,
        user_id: int = 1,
        *,
        market: MarketCode = MarketCode.CN,
        watchlist_limit: int = 12,
        signal_limit: int = 12,
        focus_symbol: str | None = None,
    ) -> DailyWorkbenchSnapshotDTO:
        panorama = self._safe_panorama(market)
        sentiment = self._safe_sentiment(market)
        panorama = self._merge_panorama_breadth(panorama, sentiment)
        watchlist = self._build_watchlist_health(user_id, market, watchlist_limit)
        obs_cards = self._observation_cards(user_id, min(signal_limit, 24))
        limit_ups = self._build_limit_up_stocks(market)
        pool_date = datetime.now().strftime("%Y-%m-%d")
        signal_preview = self._signal_flag_preview(pool_date, min(signal_limit, 24))
        rec_svc = self._recommendation_service or self._recommendation_service_alias
        integration = self._integration_digest()
        task_digest = self._task_digest()

        decision = self._compute_decision(
            panorama=panorama,
            sentiment=sentiment,
            observation_cards=obs_cards,
            watchlist_items=(watchlist.get("items") or []),
        )
        health_banner = self._build_health_banner(integration=integration, task_digest=task_digest)
        morning_call = self._build_morning_call(
            health=health_banner,
            decision=decision,
            panorama=panorama,
            observation_cards=obs_cards,
            limit_ups=limit_ups,
            integration=integration,
        )
        focus_context = self._build_focus_context(focus_symbol, market)

        rec = self._recommend_preview(rec_svc, market)
        macro_indices = self._macro_indices(market)

        payload: dict[str, Any] = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "market": market.value,
            "focus_context": focus_context,
            "health_banner": health_banner,
            "morning_call": morning_call,
            "decision": decision,
            "market_panorama": panorama,
            "market_sentiment": sentiment,
            "macro_indices": macro_indices,
            "watchlist_health": watchlist,
            "limit_up_stocks": limit_ups,
            "limit_up_stats": {"limit_up": len(limit_ups)},
            "dragon_list": self._build_dragon_list(),
            "observation_cards": obs_cards,
            "signal_flag_preview": signal_preview,
            "task_digest": task_digest,
            "integration_digest": integration,
            "recommendations_preview": rec,
            "review_strip": self._review_strip(user_id),
            "headlines": self._headlines(market, n=6),
            "trade_plan_strip": self._trade_plan_strip(user_id, market),
            "fingpt_available": self._fingpt_application_service is not None,
        }
        return payload

    def _compute_decision(
        self,
        *,
        panorama: dict[str, Any],
        sentiment: dict[str, Any],
        observation_cards: list[dict[str, Any]],
        watchlist_items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Delegate stance calculation to MarketRegimeService (pure domain logic)."""
        base = int(round(_safe_float(sentiment.get("score"), 50.0)))
        regime_svc = self._market_regime_service
        if regime_svc is None:
            return {
                "ok": True,
                "stance": "neutral",
                "score": base,
                "action": "观望",
                "reasons": ["市场状态服务不可用，默认中性评估"],
                "decision": "neutral",
                "confidence": 0.3,
                "evidence": [],
            }
        result = regime_svc.evaluate_stance(
            sentiment_score=sentiment.get("score", 50.0),
            up_count=panorama.get("up", 0),
            down_count=panorama.get("down", 0),
            flat_count=panorama.get("flat", 0),
            observation_cards=observation_cards,
            watchlist_items=watchlist_items,
        )
        wl_chg = [_safe_float(x.get("change_pct")) for x in watchlist_items]
        wl_avg = sum(wl_chg) / len(wl_chg) if wl_chg else 0.0
        reasons: list[str] = []
        reasons.append(
            f"Sentiment ~{base}, up/down ratio {panorama.get('up',0)}:{panorama.get('down',0)}:{panorama.get('flat',0)} (estimated structure)."
        )
        if observation_cards:
            stop_n = sum(1 for o in observation_cards if o.get("trigger_status") == "stop_hit")
            tgt_n = sum(1 for o in observation_cards if o.get("trigger_status") == "target_hit")
            reasons.append(
                f"Open cards {len(observation_cards)}; stop hit {stop_n}, target hit {tgt_n}."
            )
        else:
            reasons.append("No open cards; add from signal flags or watchlist.")
        if wl_chg:
            reasons.append(f"Watchlist avg change {wl_avg:+.2f}% (current sample).")

        return {
            "ok": True,
            "stance": result["stance"],
            "score": result["score"],
            "action": result["action"],
            "reasons": reasons,
            "decision": result["stance"],
            "confidence": result["confidence"],
            "evidence": result["evidence"],
        }


    def _safe_panorama(self, market: MarketCode) -> GenericResponseDTO:
        if not self._market_service:
            return {"up": 0, "down": 0, "flat": 0}
        try:
            return _to_dict(self._market_service.get_panorama(market.value))
        except Exception:
            return {"up": 0, "down": 0, "flat": 0}

    def _merge_panorama_breadth(
        self,
        panorama: dict[str, Any],
        sentiment: dict[str, Any],
    ) -> dict[str, Any]:
        stats = sentiment.get("stats") if isinstance(sentiment, dict) else None
        if not isinstance(stats, dict):
            return panorama
        total = int(stats.get("total") or 0)
        if total <= 0:
            return panorama
        merged = dict(panorama)
        merged["up"] = int(stats.get("gainers") or merged.get("up") or 0)
        merged["down"] = int(stats.get("losers") or merged.get("down") or 0)
        merged["flat"] = int(stats.get("neutral") or merged.get("flat") or 0)
        merged["total"] = total
        return merged

    def _safe_sentiment(self, market: MarketCode) -> GenericResponseDTO:
        if not self._market_service:
            return {"score": 50, "level": "中性", "stats": {"gainers": 0, "losers": 0, "neutral": 0}}
        try:
            return _to_dict(self._market_service.get_sentiment(market.value))
        except Exception:
            return {"score": 50, "level": "中性", "stats": {"gainers": 0, "losers": 0, "neutral": 0}}

    def _macro_indices(self, market: MarketCode) -> list[dict[str, Any]]:
        if not self._market_service or market != MarketCode.CN:
            return []
        specs = (
            ("上证指数", "SH000001"),
            ("深证成指", "SZ399001"),
            ("沪深300", "SH000300"),
            ("创业板指", "SZ399006"),
            ("科创50", "SH000688"),
            ("北证50", "BJ899050"),
        )
        out: list[dict[str, Any]] = []
        for label, code in specs:
            try:
                rows = self._market_service.list_quotes(MarketCode.CN, [code])
                if not rows:
                    continue
                q = rows[0] if isinstance(rows[0], dict) else _to_dict(rows[0])
                out.append(
                    {
                        "label": label,
                        "code": str(q.get("code") or code).upper(),
                        "price": q.get("price"),
                        "change_pct": q.get("change_pct"),
                    }
                )
            except Exception:
                continue
        return out

    def _build_watchlist_health(self, user_id: int, market: MarketCode, limit: int = 12) -> GenericResponseDTO:
        if not self._watchlist_service or not self._market_service:
            return {"items": [], "summary": "服务未就绪"}
        try:
            symbols = [
                str(s).strip()
                for s in self._watchlist_service.list_symbols(user_id=user_id)
                if str(s).strip()
            ]
            quotes = self._market_service.list_quotes(market, symbols)
            items = []
            for q in quotes[:limit]:
                qd = q if isinstance(q, dict) else _to_dict(q)
                ch = qd.get("change_pct")
                items.append(
                    {
                        "code": qd.get("code"),
                        "name": qd.get("name"),
                        "price": qd.get("price"),
                        "change_pct": ch,
                        "health_score": _health_score_from_change(ch),
                    }
                )
            return {"items": items, "summary": f"自选股 {len(symbols)} 只 · 展示前 {len(items)} 条"}
        except Exception:
            return {"items": [], "summary": "暂无数据"}

    def _build_limit_up_stocks(self, market: MarketCode) -> list[dict[str, Any]]:
        if not self._market_service or market != MarketCode.CN:
            return []
        try:
            quotes = self._market_service.list_quotes(MarketCode.CN)
            out: list[dict[str, Any]] = []
            for q in quotes:
                qd = q if isinstance(q, dict) else _to_dict(q)
                if _safe_float(qd.get("change_pct")) >= 9.9:
                    out.append(
                        {
                            "code": qd.get("code"),
                            "name": qd.get("name"),
                            "change_pct": qd.get("change_pct"),
                        }
                    )
                if len(out) >= 20:
                    break
            return out
        except Exception:
            return []

    def _build_dragon_list(self) -> GenericResponseDTO:
        bmd = self._basic_market_data_service
        if not bmd or not getattr(bmd, "repository", None):
            return {}
        try:
            ds = bmd.repository.list_longhu_latest_dates(limit=1)
            if not ds:
                return {}
            _, items = bmd.longhu_day(ds[0])
            inflow = sorted(
                [
                    {
                        "code": i.get("code"),
                        "name": i.get("name"),
                        "inflow": float(i.get("buy_amt", 0)) / 100000000,
                    }
                    for i in items
                    if float(i.get("buy_amt", 0)) > 0
                ],
                key=lambda x: x["inflow"],
                reverse=True,
            )
            return {"inflow_stocks": inflow[:10]}
        except Exception:
            return {}

    def _observation_cards(self, user_id: int, limit: int) -> list[dict[str, Any]]:
        obs = self._signal_observation_service
        if not obs:
            return []
        try:
            data = obs.list_observations(user_id=user_id, status="open", refresh=False)
            rows = (data or {}).get("items") or []
        except Exception as exc:
            logger.warning("workbench observation_cards: %s", exc)
            return []
        out: list[dict[str, Any]] = []
        for row in rows[:limit]:
            sym = str(row.get("symbol") or "").strip().upper()
            if not sym:
                continue
            out.append(
                {
                    "code": sym,
                    "name": row.get("name") or sym,
                    "entry_price": row.get("entry_price"),
                    "current_price": row.get("current_price"),
                    "trigger_status": row.get("trigger_status"),
                    "source": row.get("source"),
                }
            )
        return out

    def _signal_flag_preview(self, pool_date: str, limit: int) -> GenericResponseDTO:
        svc = self._signal_flag_service
        if not svc:
            return {"pool_date": pool_date, "count": 0, "items": []}
        try:
            items = svc.get_pool(pool_date) or []
        except Exception as exc:
            logger.warning("workbench signal_flag preview: %s", exc)
            return {"pool_date": pool_date, "count": 0, "items": []}
        slim: list[dict[str, Any]] = []
        for it in items[:limit]:
            code = it.get("code") or it.get("symbol")
            if not code:
                continue
            slim.append(
                {
                    "code": str(code).upper(),
                    "name": it.get("name") or code,
                    "score": it.get("score"),
                    "source": it.get("source"),
                }
            )
        return {"pool_date": pool_date, "count": len(items), "items": slim}

    def _task_digest(self) -> GenericResponseDTO:
        store = self._task_message_store
        if not store:
            return {"backend": "none", "recent_total": 0, "fail_or_warn": 0, "last_items": []}
        try:
            items = store.list_recent(limit=50)
        except Exception:
            items = []
        fail = 0
        for m in items:
            ev = str(m.get("event") or "").lower()
            if "fail" in ev or "error" in ev:
                fail += 1
        return {
            "backend": getattr(store, "enabled_backend", "unknown"),
            "recent_total": len(items),
            "fail_or_warn": fail,
            "last_items": items[:8],
        }

    def _timeseries_beat_digest(self) -> GenericResponseDTO:
        try:
            from app.infrastructure.timeseries.sync_snapshot import describe_questdb_sync_beat

            beat = describe_questdb_sync_beat()
        except Exception as exc:
            logger.debug("workbench timeseries beat digest: %s", exc, exc_info=True)
            return {"available": False, "error": str(exc)[:120]}
        last = beat.get("last_sync") or {}
        return {
            "available": True,
            "enabled": bool(beat.get("enabled")),
            "schedule_label": beat.get("schedule_label"),
            "last_run_at": beat.get("last_beat_run_at") or last.get("recorded_at"),
            "last_ok": beat.get("last_beat_run_ok")
            if beat.get("last_beat_run_ok") is not None
            else last.get("ok"),
            "sync_in_progress": bool(beat.get("sync_in_progress")),
            "history_count": len(beat.get("recent_beat_runs") or []),
        }

    def _integration_digest(self) -> GenericResponseDTO:
        timeseries_beat = self._timeseries_beat_digest()
        svc = self._integration_stack_service
        if not svc:
            return {
                "available": False,
                "summary": "集成栈未注入",
                "issues": [],
                "issue_count": 0,
                "timeseries_beat": timeseries_beat,
            }
        try:
            raw = svc.get_stack_status()
        except Exception as exc:
            return {
                "available": False,
                "summary": str(exc)[:200],
                "issues": [],
                "issue_count": 0,
                "timeseries_beat": timeseries_beat,
            }
        issues: list[str] = []
        layers = raw.get("layers") or {}
        for name, blob in layers.items():
            if isinstance(blob, dict) and blob.get("ok") is False:
                reason = blob.get("reason") or blob.get("hint") or "不可用"
                issues.append(f"{name}: {reason}")
        return {
            "available": True,
            "mysql_enabled": raw.get("mysql_enabled"),
            "issues": issues[:10],
            "issue_count": len(issues),
            "timeseries_beat": timeseries_beat,
        }

    def _recommend_preview(self, rec_svc: object, market: MarketCode) -> GenericResponseDTO:
        if not rec_svc:
            return {"items": [], "message": "推荐服务未就绪，请检查策略与证据链路配置"}
        try:
            return rec_svc.daily_top(market=market, top_n=3, account_equity=100000.0)
        except Exception as exc:
            logger.warning("workbench recommendations: %s", exc)
            return {"items": [], "message": str(exc)[:160]}

    def _review_strip(self, user_id: int) -> GenericResponseDTO:
        rv = self._review_tracking_service
        if not rv:
            return {"daily": None, "weekly": None}
        try:
            daily = rv.daily_review(user_id=user_id)
        except Exception:
            daily = None
        try:
            weekly = rv.weekly_review(user_id=user_id)
        except Exception:
            weekly = None
        return {"daily": daily, "weekly": weekly}

    def _headlines(self, market: MarketCode, *, n: int) -> list[dict[str, Any]]:
        prov = self._news_provider
        if not prov:
            return []
        try:
            items = prov.get_market_headlines(market, limit=max(n, 8))
        except Exception:
            return []
        out: list[dict[str, Any]] = []
        for it in items[:n]:
            out.append(
                {
                    "title": getattr(it, "title", "") or "",
                    "source": getattr(it, "source", "") or "",
                    "published_at": str(getattr(it, "published_at", "") or ""),
                    "url": getattr(it, "url", "") or "",
                    "summary": getattr(it, "summary", "") or "",
                }
            )
        try:
            return self._headline_signal.enrich_headlines(out, market=market.value)
        except Exception as exc:
            logger.warning("workbench headline enrichment: %s", exc)
            return out

    def _build_focus_context(self, symbol: str | None, market: MarketCode) -> dict[str, Any]:
        sym = str(symbol or "").strip().upper()
        if not sym:
            return {"symbol": None, "market": market.value, "symbol_label": None}
        label = sym
        if self._market_service:
            try:
                rows = self._market_service.list_quotes(market, [sym])
                if rows:
                    qd = rows[0] if isinstance(rows[0], dict) else _to_dict(rows[0])
                    label = str(qd.get("name") or sym)
            except Exception:
                logger.warning("Suppressed exception", exc_info=True)
                pass
        return {"symbol": sym, "market": market.value, "symbol_label": label}

    def _build_health_banner(
        self,
        *,
        integration: dict[str, Any],
        task_digest: dict[str, Any],
    ) -> dict[str, Any]:
        if self._health_banner_service is None:
            return {
                "level": "ok",
                "message": "系统运行正常，数据与任务链路未发现阻断项",
                "allow_live_trading": True,
                "critical_count": 0,
                "warning_count": 0,
                "stale_data": False,
            }
        return self._health_banner_service.build_banner(
            integration=integration,
            task_digest=task_digest,
        )

    def _build_morning_call(
        self,
        *,
        health: dict[str, Any],
        decision: dict[str, Any],
        panorama: dict[str, Any],
        observation_cards: list[dict[str, Any]],
        limit_ups: list[dict[str, Any]],
        integration: dict[str, Any],
    ) -> dict[str, Any]:
        risk_items: list[str] = []
        if health.get("critical_count"):
            risk_items.append(f"严重告警 {health['critical_count']} 条")
        if health.get("warning_count"):
            risk_items.append(f"预警 {health['warning_count']} 条")
        stop_n = sum(1 for o in observation_cards if o.get("trigger_status") == "stop_hit")
        if stop_n:
            risk_items.append(f"观察单止损触达 {stop_n} 条")
        down = int(_safe_float(panorama.get("down")))
        up = int(_safe_float(panorama.get("up")))
        if down > up * 1.2 and down > 0:
            risk_items.append(f"跌多涨少（约 {up}:{down}）")
        if not risk_items:
            risk_items.append("暂无显著风险信号，保持常规风控纪律")

        opp_items: list[str] = []
        tgt_n = sum(1 for o in observation_cards if o.get("trigger_status") == "target_hit")
        if tgt_n:
            opp_items.append(f"观察单目标触达 {tgt_n} 条")
        if limit_ups:
            opp_items.append(f"涨停样本 {len(limit_ups)} 只")
        score = int(decision.get("score") or 50)
        if score >= 62:
            opp_items.append(str(decision.get("action") or "环境偏积极"))
        if not opp_items:
            opp_items.append("暂无突出机会，可优先跟踪自选与信号旗")

        sys_items: list[str] = []
        if health.get("level") == "ok":
            sys_items.append("告警中心未发现阻断项")
        if integration.get("issue_count"):
            for iss in (integration.get("issues") or [])[:3]:
                sys_items.append(str(iss))
        elif integration.get("summary"):
            sys_items.append(str(integration.get("summary")))
        if not sys_items:
            sys_items.append("系统链路正常")

        stop_confirm_cards: list[dict[str, Any]] = []

        slides = [
            {
                "id": "risk",
                "title": "今日风险",
                "level": "warning" if health.get("level") != "ok" else "info",
                "items": risk_items[:5],
            },
            {
                "id": "opportunity",
                "title": "今日机会",
                "level": "info",
                "items": opp_items[:5],
            },
            {
                "id": "system",
                "title": "系统健康",
                "level": str(health.get("level") or "ok"),
                "items": sys_items[:5],
            },
        ]
        return {
            "slides": slides,
            "active_index": 0,
            "stop_confirm_cards": stop_confirm_cards,
            "has_stop_confirm": len(stop_confirm_cards) > 0,
        }

    def _trade_plan_strip(self, user_id: int, market: MarketCode) -> GenericResponseDTO:
        svc = self._trade_plan_service
        wl = self._watchlist_service
        ms = self._market_service
        if not svc or not wl or not ms:
            return {"symbol": None, "name": None, "entry_price": None, "stop_loss": None}
        try:
            symbols = [str(s).strip() for s in wl.list_symbols(user_id=user_id) if str(s).strip()]
            if not symbols:
                return {"symbol": None, "name": None, "entry_price": None, "stop_loss": None}
            sym = symbols[0]
            plan = svc.build_plan(
                symbol=sym,
                market=market,
                account_equity=100000.0,
                cash_available=100000.0,
            )

            # Handle TradePlanDTO - convert to dict if needed
            if hasattr(plan, "model_dump"):
                plan_dict = plan.model_dump()
            elif hasattr(plan, "dict"):
                plan_dict = plan.dict()
            else:
                plan_dict = {"name": getattr(plan, "symbol", sym), "plan": {}}

            core = plan_dict.get("plan") or plan_dict if isinstance(plan_dict, dict) else {}

            return {
                "symbol": sym,
                "name": plan_dict.get("name") or plan_dict.get("symbol") or sym,
                "entry_price": core.get("entry_price") if isinstance(core, dict) else None,
                "stop_loss": core.get("stop_loss") if isinstance(core, dict) else None,
                "take_profit_1": core.get("take_profit_1") if isinstance(core, dict) else None,
                "risk_reward_ratio": core.get("risk_reward_ratio") if isinstance(core, dict) else None,
            }
        except Exception as exc:
            logger.warning("workbench trade_plan_strip: %s", exc)
            return {"symbol": None, "name": None, "error": str(exc)[:120]}
