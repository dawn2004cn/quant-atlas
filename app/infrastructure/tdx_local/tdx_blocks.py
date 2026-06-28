from __future__ import annotations

"""通达信 ``hq_cache`` 板块文件（pytdx BlockReader）。"""


from pathlib import Path


def _norm_code6(s: str) -> str:
    d = "".join(c for c in s if c.isdigit())
    return d[-6:].zfill(6) if len(d) >= 4 else ""


def list_blocks_for_code(
    hq_cache: Path,
    code6: str,
    *,
    cfg_names: tuple[str, ...] = ("blockname.cfg", "blocknew.cfg"),
    max_block_names: int = 30,
) -> tuple[list[str], str]:
    """返回标的所属板块名称列表（扫描常见板块配置文件）。"""
    try:
        from pytdx.reader.block_reader import BlockReader
    except ImportError:
        return [], "pytdx_not_installed"

    target = _norm_code6(code6)
    if len(target) != 6:
        return [], "bad_code"

    found: list[str] = []
    for name in cfg_names:
        fp = hq_cache / name
        if not fp.is_file():
            continue
        try:
            df = BlockReader().get_df(str(fp))
        except Exception:
            continue
        if df is None or df.empty:
            continue
        if "code" not in df.columns or "blockname" not in df.columns:
            continue
        for _, row in df.iterrows():
            rc = _norm_code6(str(row.get("code") or ""))
            if rc == target:
                bn = str(row.get("blockname") or "").strip()
                if bn and bn not in found:
                    found.append(bn)
                if len(found) >= max_block_names:
                    return found, "ok"
    return found, "ok" if found else "no_match"
