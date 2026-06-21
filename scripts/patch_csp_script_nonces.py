"""Batch-add CSP nonce to inline <script> tags (not external src=)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app" / "presentation" / "web" / "templates"
TAG_RE = re.compile(r"<(script)([^>]*)>", re.IGNORECASE)


def patch_text(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        tag, attrs = match.group(1), match.group(2)
        if re.search(r"\bsrc\s*=", attrs, re.IGNORECASE):
            return match.group(0)
        if "nonce" in attrs.lower():
            return match.group(0)
        if attrs.strip():
            return f"<{tag}{attrs} nonce=\"{{{{ csp_nonce() }}}}\">"
        return f'<{tag} nonce="{{{{ csp_nonce() }}}}\">'

    return TAG_RE.sub(repl, text)


def main() -> None:
    changed = 0
    for path in sorted(ROOT.rglob("*.html")):
        original = path.read_text(encoding="utf-8")
        updated = patch_text(original)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed += 1
            print("patched", path.relative_to(ROOT.parents[2]))
    print("done, files changed:", changed)


if __name__ == "__main__":
    main()
