from app.infrastructure.providers.cn_portal_news import filter_headlines_for_symbol


def test_filter_headlines_for_symbol():
    rows = [
        {"title": "贵州茅台600519发布业绩说明会", "url": "http://x"},
        {"title": "大盘综述", "url": "http://y"},
    ]
    out = filter_headlines_for_symbol(rows, "600519")
    assert len(out) == 1
    assert "600519" in out[0]["title"]
