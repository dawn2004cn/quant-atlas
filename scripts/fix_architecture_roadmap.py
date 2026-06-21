"""Remove orphan CSS from architecture_roadmap.html."""
from pathlib import Path

p = Path("app/presentation/web/templates/architecture_roadmap.html")
text = p.read_text(encoding="utf-8")
marker = '<div class="roadmap-hero">'
idx = text.find(marker)
if idx == -1:
    raise SystemExit("marker not found")
head_end = text.find("{% block content %}")
if head_end == -1:
    raise SystemExit("content block not found")
head = text[:head_end]
tail = text[idx:]
fixed = head + "{% block content %}\n" + tail
p.write_text(fixed, encoding="utf-8")
print(f"Fixed. Lines: {len(fixed.splitlines())}")
