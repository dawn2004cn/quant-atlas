from __future__ import annotations
"""读取通达信市场股票列表 `.tnf`（hq_cache/shm.tnf, szm.tnf, bjm.tnf）。"""


from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TnfStockBasic:
    cn_symbol: str  # sh600519 / sz000001 / bj430047
    name: str


def read_tnf_file(path: Path, *, market: str) -> list[TnfStockBasic]:
    p = Path(path)
    if not p.is_file():
        return []
    m = (market or "").strip().lower()
    if m not in ("sh", "sz", "bj"):
        raise ValueError("market must be sh/sz/bj")

    out: list[TnfStockBasic] = []
    buf = p.read_bytes()
    # 通达信 tnf 头部固定 50 字节；每条记录 314 字节（见脚本实现）
    offset = 50
    rec_len = 314
    n = (len(buf) - offset) // rec_len if len(buf) > offset else 0
    for i in range(max(0, n)):
        base = offset + i * rec_len
        rec = buf[base : base + rec_len]
        if len(rec) < rec_len:
            break
        try:
            code = rec[0:6].decode("utf-8", errors="ignore").strip("\x00").strip()
        except Exception:  # noqa: BLE001
            continue
        if not code or not code.isdigit() or len(code) != 6:
            continue
        raw = rec[23:31]
        name = ""
        try:
            name = raw.decode("gbk").strip("\x00").strip()
        except UnicodeDecodeError:
            name = raw.decode("utf-8", errors="ignore").strip("\x00").strip()
        if not name:
            continue
        out.append(TnfStockBasic(cn_symbol=f"{m}{code}", name=name))
    return out


def read_all_tnf_from_hq_cache(hq_cache: Path) -> list[TnfStockBasic]:
    """从 hq_cache 目录读取三市场 tnf。"""
    root = Path(hq_cache)
    specs = (("sh", root / "shm.tnf"), ("sz", root / "szm.tnf"), ("bj", root / "bjm.tnf"))
    out: list[TnfStockBasic] = []
    for m, fp in specs:
        out.extend(read_tnf_file(fp, market=m))
    # 去重：同 symbol 以最后一次为准
    by_sym: dict[str, TnfStockBasic] = {}
    for r in out:
        by_sym[r.cn_symbol] = r
    return [by_sym[k] for k in sorted(by_sym.keys())]

