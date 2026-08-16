"""Basic knowledge base — aggregate 研报 / 财报 / 新闻 / 产业链 into searchable hits.

Inspired by retail “全网情报” workflows: fan-in platform sources that already
pull Eastmoney/AkShare/local archives, plus a curated industry-logic corpus.
Does not scrape arbitrary websites or embed a new vector DB.
"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

SOURCE_YANBAO = "yanbao"
SOURCE_NEWS = "news"
SOURCE_FINANCIAL = "financial"
SOURCE_CHAIN = "industry_chain"
SOURCE_CORPUS = "corpus"

ALL_SOURCES = (SOURCE_YANBAO, SOURCE_NEWS, SOURCE_FINANCIAL, SOURCE_CHAIN, SOURCE_CORPUS)


@dataclass
class KnowledgeHit:
    id: str
    source_type: str
    title: str
    snippet: str = ""
    symbol: str | None = None
    published_at: str | None = None
    url: str | None = None
    score: float = 0.0
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Curated industry / research logic seeds (基础知识 — not live crawl).
_SEED_CORPUS: list[dict[str, Any]] = [
    {
        "id": "corpus-ai-chain",
        "title": "AI 算力产业链逻辑：上游芯片 → 中游服务器/光模块 → 下游云与应用",
        "snippet": "需求从大模型训练/推理拉动 GPU/ASIC；中游关注服务器、交换机与光模块；下游看云厂商资本开支与行业应用落地节奏。",
        "tags": ["AI", "算力", "光模块", "GPU", "产业链"],
    },
    {
        "id": "corpus-ev-chain",
        "title": "新能源车产业链：锂电材料 → 电芯 → 整车与充电",
        "snippet": "景气度沿锂/正极/隔膜向上游传导；中游电芯看出货与开工率；下游整车看销量结构与价格战对利润的挤压。",
        "tags": ["新能源", "锂电", "整车", "产业链"],
    },
    {
        "id": "corpus-pv-chain",
        "title": "光伏产业链：硅料 → 硅片 → 电池组件 → 电站",
        "snippet": "产能出清阶段关注一体化龙头成本曲线；组件排产与海外装机决定短期弹性；电站侧看收益率与消纳。",
        "tags": ["光伏", "硅料", "组件", "产业链"],
    },
    {
        "id": "corpus-finance-read",
        "title": "财报速读框架：收入质量 → 利润结构 → 现金流 → 资产负债表风险",
        "snippet": "先核对收入增速与应收/存货；再看毛利率与费用率；经营现金流是否覆盖净利；有息负债与或有事项决定下行空间。",
        "tags": ["财报", "基本面", "现金流"],
    },
    {
        "id": "corpus-yanbao-use",
        "title": "研报使用纪律：评级迁移 + 目标价假设 + 证据链",
        "snippet": "优先看评级变动与核心假设（量价、份额、毛利率）；交叉验证公司公告与新闻，避免单篇研报定仓。",
        "tags": ["研报", "评级", "证据"],
    },
    {
        "id": "corpus-news-filter",
        "title": "新闻过滤：政策/订单/人事/诉讼对定价的差异",
        "snippet": "政策与订单类信息影响中期预期；人事与诉讼需验证是否影响经营连续性；短线情绪新闻权重应低于基本面证据。",
        "tags": ["新闻", "政策", "订单"],
    },
]


def _tokenize(text: str) -> set[str]:
    text = (text or "").lower()
    parts = re.split(r"[\s,，。；;、/|+\-_:：]+", text)
    return {p for p in parts if len(p) >= 2}


def _score(query: str, *fields: str) -> float:
    q = (query or "").strip().lower()
    if not q:
        return 1.0
    blob = " ".join(str(f or "") for f in fields).lower()
    score = 0.0
    if q in blob:
        score += 5.0
    for tok in _tokenize(q):
        if tok in blob:
            score += 1.0
    return score


class BasicKnowledgeService:
    """Fan-in search across yanbao, news, financials, industry chain, corpus."""

    def __init__(
        self,
        *,
        basic_market_data_service: Any | None = None,
        news_archive: Any | None = None,
        industry_chain_service: Any | None = None,
        fundamental_access: Any | None = None,
        local_store: Any | None = None,
    ) -> None:
        self._bmd = basic_market_data_service
        self._news = news_archive
        self._chain = industry_chain_service
        self._fund = fundamental_access
        self._local = local_store

    def search(
        self,
        query: str = "",
        *,
        symbol: str | None = None,
        sources: list[str] | None = None,
        market: str = "CN",
        limit: int = 30,
        prefer_local: bool = True,
    ) -> dict[str, Any]:
        q = (query or "").strip()
        sym = (symbol or "").strip().upper() or None
        wanted = {s for s in (sources or list(ALL_SOURCES)) if s in ALL_SOURCES}
        if not wanted:
            wanted = set(ALL_SOURCES)
        limit = max(1, min(int(limit or 30), 80))

        hits: list[KnowledgeHit] = []
        errors: dict[str, str] = {}
        local_count = 0

        if prefer_local and self._local is not None:
            try:
                local_hits = self._local.search(
                    q,
                    categories=sorted(wanted),
                    symbol=sym,
                    limit=limit,
                )
                for row in local_hits:
                    hits.append(
                        KnowledgeHit(
                            id=str(row.get("id") or ""),
                            source_type=str(row.get("category") or SOURCE_CORPUS),
                            title=str(row.get("title") or ""),
                            snippet=str(row.get("content") or "")[:320],
                            symbol=row.get("symbol") or sym,
                            published_at=row.get("published_at"),
                            url=row.get("url"),
                            score=float(row.get("score") or 0) + 0.5,
                            meta={"local": True, "tags": row.get("tags") or [], "source": row.get("source")},
                        )
                    )
                local_count = len(local_hits)
            except Exception as exc:  # noqa: BLE001
                logger.warning("local knowledge search failed: %s", exc, exc_info=True)
                errors["local"] = str(exc)

        if SOURCE_CORPUS in wanted:
            hits.extend(self._search_corpus(q, sym))
        if SOURCE_YANBAO in wanted:
            try:
                hits.extend(self._search_yanbao(q, sym, limit=limit))
            except Exception as exc:  # noqa: BLE001
                logger.warning("yanbao search failed: %s", exc, exc_info=True)
                errors[SOURCE_YANBAO] = str(exc)
        if SOURCE_NEWS in wanted:
            try:
                hits.extend(self._search_news(q, sym, market=market, limit=limit))
            except Exception as exc:  # noqa: BLE001
                logger.warning("news search failed: %s", exc, exc_info=True)
                errors[SOURCE_NEWS] = str(exc)
        if SOURCE_FINANCIAL in wanted and sym:
            try:
                hits.extend(self._search_financial(q, sym, market=market))
            except Exception as exc:  # noqa: BLE001
                logger.warning("financial search failed: %s", exc, exc_info=True)
                errors[SOURCE_FINANCIAL] = str(exc)
        if SOURCE_CHAIN in wanted:
            try:
                hits.extend(self._search_chain(q, sym, market=market))
            except Exception as exc:  # noqa: BLE001
                logger.warning("industry chain search failed: %s", exc, exc_info=True)
                errors[SOURCE_CHAIN] = str(exc)

        # Deduplicate by id keeping highest score
        by_id: dict[str, KnowledgeHit] = {}
        for h in hits:
            prev = by_id.get(h.id)
            if prev is None or h.score > prev.score:
                by_id[h.id] = h
        hits = list(by_id.values())
        hits.sort(key=lambda h: h.score, reverse=True)
        if q:
            hits = [h for h in hits if h.score > 0] or hits[:limit]
        truncated = hits[:limit]
        by_source: dict[str, int] = {}
        for h in truncated:
            by_source[h.source_type] = by_source.get(h.source_type, 0) + 1

        return {
            "query": q,
            "symbol": sym,
            "market": market,
            "sources": sorted(wanted),
            "items": [h.to_dict() for h in truncated],
            "count": len(truncated),
            "by_source": by_source,
            "local_hits": local_count,
            "errors": errors,
            "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "note": "优先本地分类库 instance/knowledge_base，并聚合平台已接入源；非任意站点全网爬取。",
        }

    def _search_corpus(self, query: str, symbol: str | None) -> list[KnowledgeHit]:
        out: list[KnowledgeHit] = []
        for row in _SEED_CORPUS:
            tags = " ".join(row.get("tags") or [])
            score = _score(query, row["title"], row["snippet"], tags, symbol or "")
            if not query:
                score = 2.0
            if score <= 0:
                continue
            out.append(
                KnowledgeHit(
                    id=str(row["id"]),
                    source_type=SOURCE_CORPUS,
                    title=str(row["title"]),
                    snippet=str(row["snippet"]),
                    symbol=symbol,
                    score=score,
                    meta={"tags": row.get("tags") or []},
                )
            )
        return out

    def _search_yanbao(self, query: str, symbol: str | None, *, limit: int) -> list[KnowledgeHit]:
        if self._bmd is None or not hasattr(self._bmd, "yanbao_list"):
            return []
        rows = self._bmd.yanbao_list(limit=min(200, max(limit * 4, 40))) or []
        out: list[KnowledgeHit] = []
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            code = str(row.get("stock_code") or row.get("symbol") or "").upper()
            if symbol and code and symbol not in code and code not in symbol:
                # soft filter: still allow title match without code
                title_blob = str(row.get("title") or "")
                if symbol not in title_blob:
                    continue
            title = str(row.get("title") or "研报")
            snippet = str(
                row.get("summary")
                or row.get("org_name")
                or row.get("rating")
                or row.get("raw")
                or ""
            )[:240]
            score = _score(query, title, snippet, code, str(row.get("org_name") or ""))
            if symbol and (symbol in code or symbol in title):
                score += 2
            if score <= 0 and query:
                continue
            out.append(
                KnowledgeHit(
                    id=f"yanbao-{row.get('id') or i}",
                    source_type=SOURCE_YANBAO,
                    title=title,
                    snippet=snippet,
                    symbol=code or symbol,
                    published_at=str(row.get("pub_date") or row.get("publish_date") or "") or None,
                    url=str(row.get("report_url") or row.get("url") or "") or None,
                    score=score or 1.0,
                    meta={"org": row.get("org_name"), "category": row.get("category")},
                )
            )
        return out

    def _search_news(
        self, query: str, symbol: str | None, *, market: str, limit: int
    ) -> list[KnowledgeHit]:
        if self._news is None:
            return []
        rows: list[dict[str, Any]] = []
        if symbol and hasattr(self._news, "list_for_symbol"):
            rows = self._news.list_for_symbol(market, symbol, limit=min(80, limit * 3)) or []
        elif hasattr(self._news, "list_recent"):
            rows = self._news.list_recent(limit=min(80, limit * 3)) or []
        out: list[KnowledgeHit] = []
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            title = str(row.get("title") or "新闻")
            snippet = str(row.get("content") or row.get("summary") or row.get("source") or "")[:240]
            score = _score(query, title, snippet, symbol or "")
            if score <= 0 and query:
                continue
            out.append(
                KnowledgeHit(
                    id=f"news-{row.get('id') or i}",
                    source_type=SOURCE_NEWS,
                    title=title,
                    snippet=snippet,
                    symbol=symbol or str(row.get("symbol") or "") or None,
                    published_at=str(row.get("published_at") or row.get("pub_date") or "") or None,
                    url=str(row.get("url") or "") or None,
                    score=score or 1.0,
                    meta={"source": row.get("source")},
                )
            )
        return out

    def _search_financial(self, query: str, symbol: str, *, market: str) -> list[KnowledgeHit]:
        del market  # reserved for multi-market fundamentals
        if self._fund is None:
            return []
        bundle = None
        if hasattr(self._fund, "cn_financial_bundle"):
            bundle = self._fund.cn_financial_bundle(symbol)
        elif hasattr(self._fund, "fetch_financial_abstract"):
            bundle = self._fund.fetch_financial_abstract(symbol)
        if not isinstance(bundle, dict):
            return []
        abstract = bundle.get("financial_abstract") or bundle.get("abstract") or []
        title = f"{symbol} 财报/财务摘要"
        snippet_parts: list[str] = []
        if isinstance(abstract, list):
            for row in abstract[:8]:
                if isinstance(row, dict):
                    snippet_parts.append(
                        " ".join(f"{k}:{v}" for k, v in list(row.items())[:4])
                    )
                else:
                    snippet_parts.append(str(row)[:80])
        elif isinstance(abstract, dict):
            snippet_parts.append(str(abstract)[:240])
        snippet = "；".join(snippet_parts)[:320] or str(bundle.get("source") or "financial")
        score = _score(query, title, snippet, "财报", "财务", symbol) or 1.5
        return [
            KnowledgeHit(
                id=f"fin-{symbol}",
                source_type=SOURCE_FINANCIAL,
                title=title,
                snippet=snippet,
                symbol=symbol,
                score=score,
                meta={"errors": bundle.get("errors"), "source": bundle.get("source")},
            )
        ]

    def _search_chain(self, query: str, symbol: str | None, *, market: str) -> list[KnowledgeHit]:
        out: list[KnowledgeHit] = []
        # Always surface matching seed chain titles via corpus; plus live map when symbol set
        if symbol and self._chain is not None and hasattr(self._chain, "build_chain"):
            from app.domain.enums import MarketCode

            try:
                mc = MarketCode(market.upper())
            except ValueError:
                mc = MarketCode.CN
            payload = self._chain.build_chain(symbol=symbol, market=mc) or {}
            if payload.get("ok") is not False and (payload.get("chain") or payload.get("chain_name")):
                name = str(payload.get("chain_name") or payload.get("chain") or "产业链")
                up = payload.get("upstream") or []
                down = payload.get("downstream") or []
                related = payload.get("related_symbols") or []
                snippet = (
                    f"上游:{','.join(map(str, up[:6]))}；下游:{','.join(map(str, down[:6]))}；"
                    f"关联:{','.join(map(str, related[:8]))}"
                )
                score = _score(query, name, snippet, symbol, "产业链") or 2.0
                out.append(
                    KnowledgeHit(
                        id=f"chain-{symbol}",
                        source_type=SOURCE_CHAIN,
                        title=f"{symbol} · {name}",
                        snippet=snippet[:320],
                        symbol=symbol,
                        score=score,
                        meta={"chain": payload.get("chain"), "ok": payload.get("ok", True)},
                    )
                )
        return out


__all__ = [
    "BasicKnowledgeService",
    "KnowledgeHit",
    "ALL_SOURCES",
    "SOURCE_YANBAO",
    "SOURCE_NEWS",
    "SOURCE_FINANCIAL",
    "SOURCE_CHAIN",
    "SOURCE_CORPUS",
]
