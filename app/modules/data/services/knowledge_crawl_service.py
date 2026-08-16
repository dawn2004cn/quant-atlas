"""Orchestrate crawl → localize → classify for AI-ready knowledge base.

Reuses existing Eastmoney/AkShare/TDX-backed ingest paths; does not scrape
arbitrary websites. Materializes hits into ``KnowledgeLocalStore``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.infrastructure.storage.knowledge_local_store import CATEGORIES, KnowledgeLocalStore
from app.modules.data.services.basic_knowledge_service import _SEED_CORPUS

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class KnowledgeCrawlService:
    """Fan-in remote ingest (optional) + always materialize classified local docs."""

    def __init__(
        self,
        *,
        store: KnowledgeLocalStore | None = None,
        basic_market_data_service: Any | None = None,
        news_archive: Any | None = None,
        tool_facade: Any | None = None,
        industry_chain_service: Any | None = None,
        fundamental_access: Any | None = None,
    ) -> None:
        self._store = store or KnowledgeLocalStore()
        self._bmd = basic_market_data_service
        self._news = news_archive
        self._facade = tool_facade
        self._chain = industry_chain_service
        self._fund = fundamental_access or tool_facade

    @property
    def store(self) -> KnowledgeLocalStore:
        return self._store

    def crawl_and_localize(
        self,
        *,
        codes: list[str] | None = None,
        sources: list[str] | None = None,
        market: str = "CN",
        run_remote: bool = True,
        yanbao_max_pages: int = 3,
    ) -> dict[str, Any]:
        wanted = [s for s in (sources or list(CATEGORIES)) if s in CATEGORIES]
        if not wanted:
            wanted = list(CATEGORIES)
        codes = [str(c).strip()[-6:].zfill(6) for c in (codes or []) if str(c).strip()]
        if not codes:
            codes = ["600519", "000001", "300750"]

        remote: dict[str, Any] = {}
        errors: dict[str, str] = {}
        materialized: dict[str, int] = {s: 0 for s in CATEGORIES}

        if run_remote:
            remote, errors = self._run_remote(codes, wanted, market=market, yanbao_max_pages=yanbao_max_pages)

        if "yanbao" in wanted:
            materialized["yanbao"] = self._materialize_yanbao()
        if "news" in wanted:
            materialized["news"] = self._materialize_news(codes, market=market)
        if "financial" in wanted:
            materialized["financial"] = self._materialize_financial(codes)
        if "industry_chain" in wanted:
            materialized["industry_chain"] = self._materialize_industry_chain(codes, market=market)
        if "corpus" in wanted:
            materialized["corpus"] = self._materialize_corpus()

        stats = self._store.stats()
        return {
            "ok": True,
            "codes": codes,
            "sources": wanted,
            "run_remote": run_remote,
            "remote": remote,
            "materialized": materialized,
            "errors": errors,
            "store": stats,
            "generated_at": _now(),
            "note": "爬取复用平台已接入源；结果本地分类写入 instance/knowledge_base，供 AI 工具调用。",
        }

    def _run_remote(
        self,
        codes: list[str],
        wanted: list[str],
        *,
        market: str,
        yanbao_max_pages: int,
    ) -> tuple[dict[str, Any], dict[str, str]]:
        remote: dict[str, Any] = {}
        errors: dict[str, str] = {}
        if "yanbao" in wanted and self._bmd is not None:
            try:
                end = datetime.now().date()
                begin = end - timedelta(days=14)
                if hasattr(self._bmd, "ingest_yanbao_eastmoney_api"):
                    remote["yanbao"] = self._bmd.ingest_yanbao_eastmoney_api(
                        begin=begin.isoformat(),
                        end=end.isoformat(),
                        max_pages=max(1, min(int(yanbao_max_pages), 20)),
                        page_size=50,
                        sleep_sec=0.2,
                    )
                else:
                    remote["yanbao"] = {"ok": False, "error": "ingest_unavailable"}
            except Exception as exc:  # noqa: BLE001
                logger.warning("yanbao crawl failed: %s", exc, exc_info=True)
                errors["yanbao"] = str(exc)

        if "news" in wanted:
            try:
                remote["news"] = self._refresh_news(codes, market=market)
            except Exception as exc:  # noqa: BLE001
                logger.warning("news crawl failed: %s", exc, exc_info=True)
                errors["news"] = str(exc)

        if "financial" in wanted and self._bmd is not None and hasattr(
            self._bmd, "refresh_financial_stash_for_codes"
        ):
            try:
                remote["financial"] = self._bmd.refresh_financial_stash_for_codes(codes, sleep_sec=0.2)
            except Exception as exc:  # noqa: BLE001
                logger.warning("financial crawl failed: %s", exc, exc_info=True)
                errors["financial"] = str(exc)

        return remote, errors

    def _refresh_news(self, codes: list[str], *, market: str) -> dict[str, Any]:
        from app.domain.enums import MarketCode

        mc = MarketCode(str(market or "CN").upper())
        refreshed = 0
        details: list[dict[str, Any]] = []
        if self._facade is not None and hasattr(self._facade, "news_bundle"):
            for sym in codes:
                r = self._facade.news_bundle(sym, mc, force_refresh=True, cache_max_age_hours=0.25)
                if r.get("remote_refreshed"):
                    refreshed += 1
                details.append({"symbol": sym, "archive_total_rows": r.get("archive_total_rows")})
        return {"ok": True, "refreshed": refreshed, "details": details, "codes": codes}

    def _materialize_yanbao(self) -> int:
        if self._bmd is None or not hasattr(self._bmd, "yanbao_list"):
            return 0
        rows = self._bmd.yanbao_list(limit=120) or []
        docs: list[dict[str, Any]] = []
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            code = str(row.get("stock_code") or row.get("symbol") or "").upper()
            title = str(row.get("title") or "研报")
            content = str(
                row.get("summary") or row.get("org_name") or row.get("rating") or row.get("raw") or ""
            )[:2000]
            docs.append(
                {
                    "id": f"yanbao-{row.get('id') or i}",
                    "category": "yanbao",
                    "title": title,
                    "content": content,
                    "symbol": code or None,
                    "tags": ["研报", str(row.get("category") or "个股研报")],
                    "source": "yanbao_items",
                    "url": str(row.get("report_url") or row.get("url") or "") or None,
                    "published_at": str(row.get("pub_date") or row.get("publish_date") or "") or None,
                    "meta": {"org": row.get("org_name"), "rating": row.get("rating")},
                }
            )
        return self._store.upsert_many(docs)

    def _materialize_news(self, codes: list[str], *, market: str) -> int:
        if self._news is None:
            return 0
        docs: list[dict[str, Any]] = []
        for sym in codes:
            rows: list[dict[str, Any]] = []
            if hasattr(self._news, "list_for_symbol"):
                rows = self._news.list_for_symbol(market, sym, limit=40) or []
            for i, row in enumerate(rows):
                if not isinstance(row, dict):
                    continue
                docs.append(
                    {
                        "id": f"news-{sym}-{row.get('id') or i}",
                        "category": "news",
                        "title": str(row.get("title") or "新闻"),
                        "content": str(row.get("content") or row.get("summary") or "")[:2000],
                        "symbol": sym,
                        "tags": ["新闻", str(row.get("source") or "")],
                        "source": "news_archive",
                        "url": str(row.get("url") or "") or None,
                        "published_at": str(row.get("published_at") or row.get("pub_date") or "") or None,
                        "meta": {"source": row.get("source")},
                    }
                )
        return self._store.upsert_many(docs)

    def _materialize_financial(self, codes: list[str]) -> int:
        docs: list[dict[str, Any]] = []
        for sym in codes:
            bundle = None
            if self._fund is not None:
                if hasattr(self._fund, "cn_financial_bundle"):
                    try:
                        bundle = self._fund.cn_financial_bundle(sym)
                    except Exception as exc:  # noqa: BLE001
                        logger.debug("cn_financial_bundle %s: %s", sym, exc)
                elif hasattr(self._fund, "fetch_financial_abstract"):
                    try:
                        bundle = self._fund.fetch_financial_abstract(sym)
                    except Exception as exc:  # noqa: BLE001
                        logger.debug("fetch_financial_abstract %s: %s", sym, exc)
            if self._bmd is not None and bundle is None and hasattr(self._bmd, "get_financial_stash"):
                try:
                    bundle = self._bmd.get_financial_stash(sym)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("get_financial_stash %s: %s", sym, exc)
            if not isinstance(bundle, dict):
                continue
            abstract = bundle.get("financial_abstract") or bundle.get("abstract") or []
            parts: list[str] = []
            if isinstance(abstract, list):
                for row in abstract[:10]:
                    if isinstance(row, dict):
                        parts.append(" ".join(f"{k}:{v}" for k, v in list(row.items())[:4]))
                    else:
                        parts.append(str(row)[:80])
            elif isinstance(abstract, dict):
                parts.append(str(abstract)[:400])
            content = "；".join(parts)[:2000] or str(bundle.get("source") or "financial")
            docs.append(
                {
                    "id": f"fin-{sym}",
                    "category": "financial",
                    "title": f"{sym} 财报/财务摘要",
                    "content": content,
                    "symbol": sym,
                    "tags": ["财报", "基本面"],
                    "source": str(bundle.get("source") or "financial_stash"),
                    "meta": {"errors": bundle.get("errors")},
                }
            )
        return self._store.upsert_many(docs)

    def _materialize_industry_chain(self, codes: list[str], *, market: str) -> int:
        docs: list[dict[str, Any]] = []
        try:
            from app.modules.market_data.services.industry_chain_map_service import (
                INDUSTRY_CHAIN_CONFIG,
            )
        except Exception:  # noqa: BLE001
            INDUSTRY_CHAIN_CONFIG = {}

        for key, cfg in (INDUSTRY_CHAIN_CONFIG or {}).items():
            if not isinstance(cfg, dict):
                continue
            name = str(cfg.get("name") or key)
            up = cfg.get("upstream") or []
            down = cfg.get("downstream") or []
            related = cfg.get("related") or []
            content = (
                f"上游:{','.join(map(str, up))}；下游:{','.join(map(str, down))}；"
                f"关联标的:{','.join(map(str, related))}"
            )
            docs.append(
                {
                    "id": f"chain-cfg-{key}",
                    "category": "industry_chain",
                    "title": f"产业链逻辑 · {name}",
                    "content": content,
                    "symbol": None,
                    "tags": ["产业链", name, key],
                    "source": "industry_chain_config",
                    "meta": {"chain_key": key, "related": related},
                }
            )

        if self._chain is not None and hasattr(self._chain, "build_chain"):
            from app.domain.enums import MarketCode

            try:
                mc = MarketCode(str(market or "CN").upper())
            except ValueError:
                mc = MarketCode.CN
            for sym in codes:
                try:
                    payload = self._chain.build_chain(symbol=sym, market=mc) or {}
                except Exception as exc:  # noqa: BLE001
                    logger.debug("build_chain %s: %s", sym, exc)
                    continue
                if payload.get("ok") is False:
                    continue
                name = str(payload.get("chain_name") or payload.get("chain") or "产业链")
                up = payload.get("upstream") or []
                down = payload.get("downstream") or []
                related = payload.get("related_symbols") or []
                docs.append(
                    {
                        "id": f"chain-{sym}",
                        "category": "industry_chain",
                        "title": f"{sym} · {name}",
                        "content": (
                            f"上游:{','.join(map(str, up[:8]))}；下游:{','.join(map(str, down[:8]))}；"
                            f"关联:{','.join(map(str, related[:12]))}"
                        ),
                        "symbol": sym,
                        "tags": ["产业链", name],
                        "source": "industry_chain_service",
                        "meta": {"chain": payload.get("chain")},
                    }
                )
        return self._store.upsert_many(docs)

    def _materialize_corpus(self) -> int:
        docs = [
            {
                "id": str(row["id"]),
                "category": "corpus",
                "title": str(row["title"]),
                "content": str(row["snippet"]),
                "symbol": None,
                "tags": list(row.get("tags") or []),
                "source": "seed_corpus",
            }
            for row in _SEED_CORPUS
        ]
        return self._store.upsert_many(docs)


__all__ = ["KnowledgeCrawlService"]
