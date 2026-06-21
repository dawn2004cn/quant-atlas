"""通达信本地 lday 解析与基础数据服务快照（无真实 TDX 目录）。"""

from struct import pack

from app.application.services.basic_market_data_service import BasicMarketDataService
from app.infrastructure.tdx_local.lday_reader import parse_lday_bytes, read_lday_file


def test_parse_lday_bytes_two_bars():
    r1 = pack("IIIIIfII", 20240102, 1000, 1100, 900, 1050, 10000.0, 1000, 0)
    r2 = pack("IIIIIfII", 20240103, 1050, 1150, 1040, 1120, 20000.0, 2000, 0)
    rows = parse_lday_bytes(r1 + r2)
    assert len(rows) == 2
    assert rows[0]["date"] == "2024-01-02"
    assert rows[0]["open"] == 10.0
    assert rows[1]["close"] == 11.2


def test_read_lday_file_tail(tmp_path):
    p = tmp_path / "x.day"
    body = b""
    for i in range(5):
        d = 20240101 + i
        body += pack("IIIIIfII", d, 1000, 1000, 1000, 1000, 1.0, 100, 0)
    p.write_bytes(body)
    rows = read_lday_file(p, tail=2)
    assert len(rows) == 2


def test_tdx_snapshot_requires_root(tmp_path):
    svc = BasicMarketDataService(base_dir=tmp_path, tdx_root_path="")
    out = svc.get_tdx_local_cn_snapshot("600519")
    assert out.get("ok") is False
    assert out.get("error") == "tdx_root_not_configured"
