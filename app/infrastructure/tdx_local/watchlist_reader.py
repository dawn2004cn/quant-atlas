from __future__ import annotations
"""读取通达信本地自选股/自定义板块文件（`.blk`）。

默认路径约定（通达信常见目录结构）：
- `{TDX_ROOT}/T0002/blocknew/*.blk`

文件内容通常为每行一个证券代码（可能带前缀/后缀/空白），这里统一提取 6 位数字并归一到 ``sh600519`` 格式。
"""


import re
from dataclasses import dataclass
from pathlib import Path

from ..mappers.symbol_normalizer import SymbolNormalizer

_RE_CODE6 = re.compile(r"(\d{6})")


@dataclass(frozen=True)
class TdxWatchlist:
    name: str
    source_path: str
    symbols: list[str]  # DB key: sh600519 / sz000001 / bj830001


def _extract_code6_lines(text: str) -> list[str]:
    out: list[str] = []
    for line in (text or "").splitlines():
        m = _RE_CODE6.search(line)
        if not m:
            continue
        out.append(m.group(1))
    return out


def read_tdx_blk_watchlists(*, tdx_root: Path, extra_paths: list[Path] | None = None) -> list[TdxWatchlist]:
    paths: list[Path] = []
    blocknew = (tdx_root / "T0002" / "blocknew").resolve()
    if blocknew.exists():
        paths.extend(sorted(blocknew.glob("*.blk")))
    if extra_paths:
        for p in extra_paths:
            rp = Path(p).expanduser().resolve()
            if rp.is_file():
                paths.append(rp)
            elif rp.is_dir():
                paths.extend(sorted(rp.glob("*.blk")))

    watchlists: list[TdxWatchlist] = []
    seen: set[Path] = set()
    for p in paths:
        if p in seen:
            continue
        seen.add(p)
        try:
            raw = p.read_text(encoding="gbk", errors="ignore")
        except Exception:
            raw = p.read_text(encoding="utf-8", errors="ignore")

        codes6 = _extract_code6_lines(raw)
        symbols = [SymbolNormalizer.to_db_code(code6, market="CN") for code6 in codes6]
        # 去重保持顺序
        uniq: list[str] = []
        sset: set[str] = set()
        for s in symbols:
            if not s or s in sset:
                continue
            sset.add(s)
            uniq.append(s)

        name = p.stem or p.name
        watchlists.append(TdxWatchlist(name=name, source_path=str(p), symbols=uniq))
    return watchlists

