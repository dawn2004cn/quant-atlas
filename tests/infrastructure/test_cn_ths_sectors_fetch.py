"""THS sector fetch smoke tests (network optional)."""

from __future__ import annotations

import pytest

from app.infrastructure.providers.cn_ths_sectors import (
    _index_ajax_url,
    _parse_board_index_html,
    _parse_pct,
    fetch_ths_concept_boards,
    is_ths_sector_code,
    normalize_ths_board_kind,
)


def test_index_ajax_url_uses_listing_path_not_bare_detail():
    url = _index_ajax_url("concept", 1)
    assert "/index/field/" in url
    assert "/ajax/1" in url
    assert "/code/" not in url


def test_normalize_ths_board_kind_aliases():
    assert normalize_ths_board_kind("dy") == "region"
    assert normalize_ths_board_kind("zjhhy") == "csrc"


def test_parse_pct_handles_percent_sign():
    assert _parse_pct("+3.25%") == 3.25
    assert _parse_pct("-1.1％") == -1.1


def test_parse_board_index_html_extracts_sector_rows():
    html = """
    <table class="m-table">
      <tr><th>名称</th><th>涨跌幅</th></tr>
      <tr>
        <td><a href="/gn/detail/code/885800/">人工智能</a></td>
        <td class="c-rise">+5.12%</td>
      </tr>
    </table>
    """
    rows = _parse_board_index_html(html, ths_kind="concept", source_label="同花顺概念")
    assert len(rows) == 1
    assert rows[0]["sector_code"] == "885800"
    assert rows[0]["name"] == "人工智能"
    assert rows[0]["change_pct"] == pytest.approx(5.12)
    assert rows[0]["kind"] == "concept"
    assert rows[0]["provider"] == "ths"


def test_is_ths_sector_code_rejects_eastmoney_bk():
    assert is_ths_sector_code("BK0475") is False
    assert is_ths_sector_code("885800") is False  # 开盘啦 885 前缀
    assert is_ths_sector_code("300800") is True
    assert is_ths_sector_code("A") is True


@pytest.mark.integration
def test_fetch_ths_concept_boards_returns_rows():
    rows = fetch_ths_concept_boards(limit=3)
    assert len(rows) >= 1
    assert rows[0].get("sector_code")
    assert rows[0].get("provider") == "ths"
