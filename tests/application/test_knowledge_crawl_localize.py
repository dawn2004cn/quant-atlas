"""Tests for local knowledge store + crawl materialization."""

from __future__ import annotations

from pathlib import Path

from app.infrastructure.storage.knowledge_local_store import KnowledgeLocalStore
from app.modules.data.services.knowledge_crawl_service import KnowledgeCrawlService


def test_local_store_upsert_and_search_by_category(tmp_path: Path) -> None:
    store = KnowledgeLocalStore(root=tmp_path / "kb")
    store.upsert(
        {
            "id": "yanbao-1",
            "category": "yanbao",
            "title": "白酒景气研报",
            "content": "维持买入，渠道健康",
            "symbol": "600519",
            "tags": ["研报", "白酒"],
            "source": "eastmoney",
        }
    )
    store.upsert(
        {
            "id": "news-1",
            "category": "news",
            "title": "机构调研",
            "content": "产业链景气",
            "symbol": "600519",
            "tags": ["新闻"],
            "source": "archive",
        }
    )
    hits = store.search("白酒", categories=["yanbao"], limit=10)
    assert len(hits) == 1
    assert hits[0]["category"] == "yanbao"
    by_cat = store.stats()
    assert by_cat["by_category"]["yanbao"] == 1
    assert by_cat["by_category"]["news"] == 1


def test_ai_pack_groups_categories(tmp_path: Path) -> None:
    store = KnowledgeLocalStore(root=tmp_path / "kb")
    store.upsert(
        {
            "id": "fin-600519",
            "category": "financial",
            "title": "600519 财报摘要",
            "content": "营收稳健",
            "symbol": "600519",
            "tags": ["财报"],
            "source": "stash",
        }
    )
    pack = store.build_ai_pack(symbol="600519", limit=20)
    assert pack["symbol"] == "600519"
    assert "financial" in pack["by_category"]
    assert "###" in pack["prompt_block"]
    assert "财报" in pack["prompt_block"] or "financial" in pack["prompt_block"]


class _FakeBmd:
    def ingest_yanbao_eastmoney_api(self, **kwargs):
        return {"ok": True, "rows": 2, "source": "eastmoney_api"}

    def yanbao_list(self, **kwargs):
        return [
            {
                "id": "y1",
                "title": "测试研报",
                "stock_code": "600519",
                "summary": "摘要",
                "org_name": "券商A",
                "pub_date": "2026-08-10",
                "category": "个股研报",
            }
        ]

    def refresh_financial_stash_for_codes(self, codes, sleep_sec: float = 0.2):
        return {"ok": True, "codes": list(codes), "rows": len(codes)}


class _FakeNews:
    def list_for_symbol(self, market, symbol, limit=80):
        return [
            {
                "id": "n1",
                "title": f"{symbol} 新闻",
                "content": "本地新闻",
                "published_at": "2026-08-11",
            }
        ]

    def list_recent(self, limit=80):
        return self.list_for_symbol("CN", "000001", limit=limit)


class _FakeFund:
    def cn_financial_bundle(self, symbol: str):
        return {"financial_abstract": [{"指标": "营收", "值": "1"}], "source": "demo"}


def test_crawl_service_materializes_local(tmp_path: Path) -> None:
    store = KnowledgeLocalStore(root=tmp_path / "kb")
    svc = KnowledgeCrawlService(
        store=store,
        basic_market_data_service=_FakeBmd(),
        news_archive=_FakeNews(),
        tool_facade=None,
        fundamental_access=_FakeFund(),
    )
    out = svc.crawl_and_localize(
        codes=["600519"],
        sources=["yanbao", "news", "financial", "industry_chain", "corpus"],
        run_remote=True,
    )
    assert out["ok"] is True
    assert out["materialized"]["yanbao"] >= 1
    assert out["materialized"]["news"] >= 1
    assert out["materialized"]["financial"] >= 1
    assert out["materialized"]["industry_chain"] >= 1
    assert out["materialized"]["corpus"] >= 1
    local = store.search("研报", limit=20)
    assert any(h["category"] == "yanbao" for h in local)
