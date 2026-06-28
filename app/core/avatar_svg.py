from __future__ import annotations

"""确定性 SVG 头像（渐变 + 首字），不依赖外网图床。"""


import hashlib
import html
import re


def _rgb_from_seed(seed: str) -> tuple[int, int, int, int, int, int]:
    h = hashlib.md5(seed.encode("utf-8")).hexdigest()
    a = int(h[:6], 16)
    b = int(h[6:12], 16)
    r1, g1, b1 = (a >> 16) & 255, (a >> 8) & 255, a & 255
    r2, g2, b2 = (b >> 16) & 255, (b >> 8) & 255, b & 255
    # 提亮，避免过暗
    r1, g1, b1 = max(40, r1), max(40, g1), max(40, b1)
    r2, g2, b2 = min(255, r2 + 40), min(255, g2 + 40), min(255, b2 + 40)
    return r1, g1, b1, r2, g2, b2


def _two_chars(label: str) -> str:
    s = re.sub(r"\s+", "", (label or "").strip())
    if not s:
        return "?"
    # 取末尾「姓+名」或前两个 Unicode 字符（兼容中文）
    if "·" in s:
        parts = [p for p in s.split("·") if p]
        if parts:
            s = parts[-1]
    if len(s) >= 2:
        return s[:2]
    return s[0] + s[0]


def build_round_avatar_svg(*, seed: str, label: str, size: int = 128) -> str:
    """圆形渐变底 + 居中二字（或单字重复）。"""
    r1, g1, b1, r2, g2, b2 = _rgb_from_seed(seed)
    ch = _two_chars(label)
    ch_esc = html.escape(ch, quote=True)
    fs = int(size * 0.36)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">
<defs>
  <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="rgb({r1},{g1},{b1})"/>
    <stop offset="100%" stop-color="rgb({r2},{g2},{b2})"/>
  </linearGradient>
</defs>
<circle cx="{size/2}" cy="{size/2}" r="{size/2}" fill="url(#g)"/>
<text x="50%" y="50%" dominant-baseline="central" text-anchor="middle"
  font-family="'Noto Sans SC','Microsoft YaHei',sans-serif" font-size="{fs}" font-weight="800" fill="rgba(255,255,255,0.95)">{ch_esc}</text>
</svg>"""
