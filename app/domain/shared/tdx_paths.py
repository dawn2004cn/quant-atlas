from __future__ import annotations

"""解析 ``TDX_ROOT_PATH`` 下 vipdoc / hq_cache 路径（domain 纯逻辑）。"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TdxLocalPaths:
    root: Path

    @property
    def vipdoc(self) -> Path:
        return self.root / "vipdoc"

    @property
    def hq_cache(self) -> Path:
        return self.root / "T0002" / "hq_cache"

    @property
    def gbbq_file(self) -> Path:
        return self.hq_cache / "gbbq"

    @property
    def gpcw_dir(self) -> Path:
        return self.vipdoc / "cw"

    def lday_file(self, *, market_sh: bool, code6: str) -> Path:
        c = code6.strip()[-6:].zfill(6)
        if c.startswith(("60", "68")):
            sub = "sh"
            prefix = "sh"
        elif c.startswith(("83", "43", "87", "88", "92")):
            sub = "bj"
            prefix = "bj"
        elif c.startswith(("00", "30")):
            sub = "sz"
            prefix = "sz"
        else:
            sub = "sh"
            prefix = "sh"

        return self.root / "vipdoc" / sub / "lday" / f"{prefix}{c}.day"

    def lday_file_by_market(self, *, market: str, code6: str) -> Path:
        m = (market or "").strip().lower()
        if m not in ("sh", "sz", "bj"):
            m = "sz"
        c = (code6 or "").strip()[-6:].zfill(6)
        return self.root / "vipdoc" / m / "lday" / f"{m}{c}.day"

    def lday_file_code8(self, *, market_sh: bool, code8: str) -> Path:
        c = code8.strip()[-8:].zfill(8)
        if c.startswith("sh"):
            sub = "sh"
            prefix = "sh"
        elif c.startswith("bj"):
            sub = "bj"
            prefix = "bj"
        elif c.startswith("sz"):
            sub = "sz"
            prefix = "sz"
        else:
            sub = "sh"
            prefix = "sh"

        return self.root / "vipdoc" / sub / "lday" / f"{prefix}{c}.day"


def resolve_tdx_root(raw: str | None) -> Path | None:
    if not raw or not str(raw).strip():
        return None
    p = Path(str(raw).strip()).expanduser()
    if not p.is_dir():
        return None
    return p.resolve()
