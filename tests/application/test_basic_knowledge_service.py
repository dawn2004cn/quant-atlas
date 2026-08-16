"""Unit tests for BasicKnowledgeService fan-in search."""

from __future__ import annotations

from app.modules.data.services.basic_knowledge_service import (
    SOURCE_CORPUS,
    SOURCE_FINANCIAL,
    SOURCE_YANBAO,
    BasicKnowledgeService,
)


class _FakeYanbao:
    def yanbao_list(self, limit: int = 40):
        return [
            {
                "id": "y1",
                "title": "高端白酒景气延续",
                "stock_code": "600519",
                "org_name": "演示券商",
                "pub_date": "2026-08-10",
                "summary": "渠道库存健康，维持买入",
            }
        ][:limit]


class _FakeNews:
    def list_for_symbol(self, market, symbol, limit=20):
        return [
            {
                "id": "n1",
                "title": f"{symbol} 获机构调研",
                "content": "产业链景气上行",
                "published_at": "2026-08-11",
            }
        ][:limit]

    def list_recent(self, limit=20):
        return self.list_for_symbol("CN", "000001", limit=limit)


class _FakeFund:
    def cn_financial_bundle(self, symbol: str):
        return {
            "financial_abstract": [{"指标": "营收", "值": "100亿"}],
            "source": "demo",
        }


def test_corpus_hits_for_industry_query() -> None:
    svc = BasicKnowledgeService()
    out = svc.search("产业链", sources=[SOURCE_CORPUS], limit=20)
    assert out["count"] >= 1
    assert all(i["source_type"] == SOURCE_CORPUS for i in out["items"])
    assert "非任意站点全网爬取" in out["note"] or "非全网任意站点爬取" in out["note"]


def test_fan_in_yanbao_and_news() -> None:
    svc = BasicKnowledgeService(
        basic_market_data_service=_FakeYanbao(),
        news_archive=_FakeNews(),
    )
    out = svc.search("白酒", symbol="600519", limit=30)
    types = {i["source_type"] for i in out["items"]}
    assert SOURCE_YANBAO in types
    assert out["symbol"] == "600519"

    news_out = svc.search("调研", symbol="600519", sources=["news"], limit=10)
    assert news_out["count"] >= 1
    assert news_out["items"][0]["source_type"] == "news"


def test_financial_requires_symbol() -> None:
    svc = BasicKnowledgeService(fundamental_access=_FakeFund())
    empty = svc.search("财报", sources=[SOURCE_FINANCIAL], limit=10)
    assert empty["count"] == 0
    hit = svc.search("财报", symbol="600519", sources=[SOURCE_FINANCIAL], limit=10)
    assert hit["count"] == 1
    assert hit["items"][0]["source_type"] == SOURCE_FINANCIAL
