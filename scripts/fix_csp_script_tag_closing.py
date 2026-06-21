"""Repair inline <script> tags broken by patch_csp_script_nonces.py (missing '>')."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app" / "presentation" / "web" / "templates"
BROKEN = re.compile(
    r'<script([^>]*\bnonce\s*=\s*"\{\{\s*csp_nonce\(\)\s*\}\}")(?!\s*>)',
    re.IGNORECASE,
)


def fix_text(text: str) -> str:
    return BROKEN.sub(r"<script\1>", text)


def main() -> None:
    changed = 0
    for path in sorted(ROOT.rglob("*.html")):
        original = path.read_text(encoding="utf-8")
        updated = fix_text(original)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed += 1
            print("fixed", path.relative_to(ROOT.parents[2]))
    print("done, files fixed:", changed)


if __name__ == "__main__":
    main()
