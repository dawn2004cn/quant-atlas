"""Replace inline <style> with research.css link in Phase 3 templates."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "app/presentation/web/templates"

LINK = (
    '<link rel="stylesheet" '
    'href="{{ url_for(\'static\', filename=\'css/pages/research.css\') }}">'
)

FILES = [
    "war_room.html",
    "ai_analysis.html",
    "ai_chat.html",
    "agent_center.html",
    "research_pipeline.html",
]


def migrate(fname: str) -> None:
    path = TPL / fname
    text = path.read_text(encoding="utf-8")
    new_text, count = re.subn(
        r"<style>.*?</style>",
        LINK,
        text,
        count=1,
        flags=re.S,
    )
    if count != 1:
        raise SystemExit(f"{fname}: expected 1 style block, replaced {count}")
    if fname == "agent_center.html" and "agent-center-page" not in new_text:
        new_text = new_text.replace(
            "{% block content %}\n<div class=\"agent-hero\">",
            "{% block content %}\n<div class=\"agent-center-page\">\n<div class=\"agent-hero\">",
            1,
        )
        # Close wrapper before endblock
        new_text = new_text.replace(
            "\n{% endblock %}\n\n{% block extra_js %}",
            "\n</div>\n{% endblock %}\n\n{% block extra_js %}",
            1,
        )
        if "agent-center-page" not in new_text:
            # fallback: close before last endblock in content
            idx = new_text.rfind("{% endblock %}")
            new_text = new_text[:idx] + "</div>\n" + new_text[idx:]
    path.write_text(new_text, encoding="utf-8")
    print(f"OK {fname}")


def main() -> None:
    for fname in FILES:
        migrate(fname)


if __name__ == "__main__":
    main()
