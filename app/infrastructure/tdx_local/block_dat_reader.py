from __future__ import annotations

"""读取通达信 hq_cache 下的 block_*.dat（指数/概念/风格板块）。"""


import re
from dataclasses import dataclass
from pathlib import Path

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class TdxBlockItem:
    block_kind: str  # zs/gn/fg
    block_name: str
    cn_symbol: str  # sh/sz/bj + 6位


def _norm_code6(s: str) -> str:
    d = "".join(c for c in str(s) if c.isdigit())
    return d[-6:].zfill(6) if d else ""


def _cn_symbol_from_code6(code6: str) -> str:
    """由 6 位代码推断通达信 `{market}{code6}`。"""
    if len(code6) != 6:
        return ""
    # 北交所常见前缀：8/4/9 开头（与板块文件一致）
    if code6.startswith(("8", "4", "9")):
        return f"bj{code6}"
    # 沪市：60/68（含科创板 688）
    if code6.startswith(("60", "68")):
        return f"sh{code6}"
    return f"sz{code6}"

def read_block_dat(path: Path, *, block_kind: str) -> list[TdxBlockItem]:
    """解析单个 block_*.dat 为 (板块→成分股) 扁平列表。"""
    try:
        from pytdx.reader import BlockReader
        from pytdx.reader.block_reader import BlockReader_TYPE_GROUP
    except Exception:
        return []
    fp = Path(path)
    if not fp.is_file():
        return []
    kind = (block_kind or "").strip().lower()
    if kind not in ("zs", "gn", "fg"):
        kind = "zs"
    try:
        df = BlockReader().get_df(str(fp), result_type=BlockReader_TYPE_GROUP)
    except Exception as exc:
        logger.warning("read block dat failed: %s err=%s", fp, exc)
        return []
    if df is None or df.empty:
        return []
    if "blockname" not in df.columns or "code_list" not in df.columns:
        return []
    out: list[TdxBlockItem] = []
    for _, row in df.iterrows():
        bn = str(row.get("blockname") or "").strip()
        codes = row.get("code_list")
        if not bn or not codes:
            continue
        # pytdx group 模式下 code_list 可能是 list[str] 或 str
        if isinstance(codes, str):
            # 某些环境返回形如 "['000001', '000002']" 或 "000001,000002"
            codes_list = re.findall(r"\b\d{6}\b", codes)
            if not codes_list:
                codes_list = [codes]
        elif isinstance(codes, list):
            codes_list = codes
        else:
            try:
                codes_list = list(codes)  # type: ignore[arg-type]
            except Exception:
                codes_list = []
        for c in codes_list:
            code6 = _norm_code6(c)
            if len(code6) != 6:
                continue
            sym = _cn_symbol_from_code6(code6)
            if not sym:
                continue
            out.append(TdxBlockItem(block_kind=kind, block_name=bn, cn_symbol=sym))
    return out


def read_all_block_dats(hq_cache: Path) -> list[TdxBlockItem]:
    root = Path(hq_cache)
    specs = (
        ("zs", root / "block_zs.dat"),
        ("gn", root / "block_gn.dat"),
        ("fg", root / "block_fg.dat"),
    )
    out: list[TdxBlockItem] = []
    for kind, fp in specs:
        out.extend(read_block_dat(fp, block_kind=kind))
    return out

if __name__ == "__main__":
    tdx_path = None  # Set your TDX path here
    tdxServer = read_all_block_dats(tdx_path)
    print("Block files processed successfully")
