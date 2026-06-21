"""Remove static display:none inline styles; add qa-is-hidden outside <script> blocks."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "app/presentation/web/templates"

SCRIPT_SPLIT = re.compile(r"(<script\b[^>]*>.*?</script>)", re.IGNORECASE | re.DOTALL)
TAG_WITH_STYLE = re.compile(
    r"<([a-zA-Z][\w-]*)\b([^>]*?)\sstyle=\"([^\"]*)\"([^>]*)>",
    re.DOTALL,
)


def _split_style(style_val: str) -> tuple[list[str], bool]:
    parts = [p.strip() for p in style_val.split(";") if p.strip()]
    kept = [p for p in parts if not re.fullmatch(r"display\s*:\s*none", p, re.IGNORECASE)]
    return kept, len(kept) < len(parts)


def _inject_hidden(attrs: str) -> str:
    if re.search(r'\bclass="', attrs):
        return re.sub(r'\bclass="', 'class="qa-is-hidden ', attrs, count=1)
    return f'{attrs} class="qa-is-hidden"'


def fix_html_segment(html: str) -> str:
    def fix_tag(match: re.Match[str]) -> str:
        name, before, style_val, after = match.group(1), match.group(2), match.group(3), match.group(4)
        kept, had_none = _split_style(style_val)
        attrs = f"{before}{after}".strip()
        attrs = re.sub(r'\s*style="[^"]*"', "", attrs)
        if kept:
            sep = " " if attrs else ""
            attrs = f'{attrs}{sep}style="{"; ".join(kept)}"'
        if had_none:
            attrs = _inject_hidden(attrs)
        inner = f" {attrs}" if attrs else ""
        return f"<{name}{inner}>"

    return TAG_WITH_STYLE.sub(fix_tag, html)


def process_file(path: Path) -> int:
    original = path.read_text(encoding="utf-8")
    parts = SCRIPT_SPLIT.split(original)
    changed = False
    for i, part in enumerate(parts):
        if i % 2 == 1:
            continue
        fixed = fix_html_segment(part)
        if fixed != part:
            changed = True
            parts[i] = fixed
    if not changed:
        return 0
    path.write_text("".join(parts), encoding="utf-8")
    before = len(re.findall(r'style="', original))
    after = len(re.findall(r'style="', "".join(parts)))
    return before - after


def main() -> None:
    total = 0
    files = 0
    for path in sorted(TPL.rglob("*.html")):
        n = process_file(path)
        if n:
            print(f"{path.relative_to(ROOT)}: -{n} style attrs")
            total += n
            files += 1
    print(f"done: {files} files, ~{total} fewer style= attributes")


if __name__ == "__main__":
    main()
