from pathlib import Path

from app.infrastructure.repositories.news_archive_repository import NewsArchiveRepository


def test_news_archive_ingest_and_list(tmp_path: Path):
    db = tmp_path / "na.db"
    repo = NewsArchiveRepository(db)
    snap = {
        "company_name_hint": "测试公司",
        "industry_hint": "软件",
        "news": [{"title": "公告A", "url": "http://a", "published_at": "2024-01-01", "source": "t", "summary": ""}],
        "industry_news": [
            {"title": "行业动态", "url": "http://b", "published_at": "", "source": "t", "summary": "摘要"}
        ],
    }
    n = repo.ingest_snapshot("CN", "600000", snap)
    assert n >= 1
    rows = repo.list_for_symbol("CN", "600000", limit=10)
    assert len(rows) >= 2
    meta = repo.get_meta("CN", "600000")
    assert meta.get("company_name") == "测试公司"
