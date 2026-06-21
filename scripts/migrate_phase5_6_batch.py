"""Phase 5/6 batch: portfolio, user, admin, zen, components, collaboration."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "app/presentation/web/templates"
CSS_PAGES = ROOT / "static/css/pages"
CSS_COMPONENTS = ROOT / "static/css/components"

PORTFOLIO_TEMPLATES: list[tuple[str, str]] = [
    ("portfolio.html", "Portfolio list"),
    ("portfolio_detail.html", "Portfolio detail"),
    ("shadow_account.html", "Shadow account"),
    ("run_history.html", "Run history"),
    ("selection_result.html", "Selection result"),
    ("investment_managers.html", "Investment managers"),
    ("investment_manager_detail.html", "Investment manager detail"),
    ("expert_teams.html", "Expert teams"),
]

USER_TEMPLATES: list[tuple[str, str]] = [
    ("moments.html", "Moments"),
    ("user_spectrum_hub.html", "User spectrum hub"),
]

ADMIN_TEMPLATES: list[tuple[str, str]] = [
    ("users_manage.html", "Users manage"),
    ("stocks_manage.html", "Stocks manage"),
]

ZEN_TEMPLATES: list[tuple[str, str]] = [
    ("zen_terminal.html", "Zen terminal"),
    ("portfolio_resonance.html", "Portfolio resonance"),
]

COMPONENT_FILES: list[tuple[str, str]] = [
    ("components/strategy/evidence_card.html", "evidence-card.css", "Evidence card"),
    ("components/skeleton.html", "skeleton.css", "Skeleton loaders"),
    ("components/risk/trading_dna_spiral.html", "trading-dna-spiral.css", "Trading DNA spiral"),
    ("components/wisdom/wisdom_mesh_browser.html", "wisdom-mesh-browser.css", "Wisdom mesh browser"),
]


def extract_first_style(text: str) -> str:
    match = re.search(r"<style>\s*(.*?)\s*</style>", text, re.S)
    return match.group(1).strip() if match else ""


def tokenize_css(css: str) -> str:
    return css.replace(
        "radial-gradient(circle at top right, rgba(16,63,145,0.12), transparent 35%), #fff;",
        "radial-gradient(circle at top right, color-mix(in srgb, var(--brand) 12%, transparent), transparent 35%), var(--surface-strong);",
    )


def build_multi_page_css(out_path: Path, header: str, templates: list[tuple[str, str]]) -> None:
    parts = [header]
    for fname, title in templates:
        css = tokenize_css(extract_first_style((TPL / fname).read_text(encoding="utf-8")))
        if not css:
            raise SystemExit(f"{fname}: no <style>")
        parts.append(f"/* ─── {title} ({fname}) ──────────────────────────────────────────── */\n{css}\n\n")
    out_path.write_text("".join(parts), encoding="utf-8")
    print(f"wrote {out_path.name} ({len(templates)} sections)")


def link_tag(pages_path: str) -> str:
    return (
        '<link rel="stylesheet" '
        f'href="{{{{ url_for(\'static\', filename=\'{pages_path}\') }}}}">'
    )


def replace_one_style(text: str, link: str) -> str:
    new_text, count = re.subn(r"<style>\s*.*?\s*</style>", link, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"style replace failed (count={count})")
    return new_text


def migrate_extra_css(templates: list[str], css_file: str) -> None:
    link = link_tag(f"css/pages/{css_file}")
    for fname in templates:
        path = TPL / fname
        path.write_text(replace_one_style(path.read_text(encoding="utf-8"), link), encoding="utf-8")
        print(f"OK {fname} → {css_file}")


def migrate_zen_page(fname: str) -> None:
    path = TPL / fname
    text = path.read_text(encoding="utf-8")
    link = link_tag("css/pages/zen-pages.css")
    if "{% block head_extra %}" in text:
        text = re.sub(
            r"\{% block head_extra %\}\s*<style>.*?</style>\s*\{% endblock %\}",
            f"{{% block extra_css %}}\n{link}\n{{% endblock %}}",
            text,
            count=1,
            flags=re.S,
        )
    else:
        text = replace_one_style(text, link)
    path.write_text(text, encoding="utf-8")
    print(f"OK zen {fname}")


def append_strategy_css(fname: str, title: str) -> None:
    path = CSS_PAGES / "strategy.css"
    css = tokenize_css(extract_first_style((TPL / fname).read_text(encoding="utf-8")))
    if not css:
        raise SystemExit(f"{fname}: no style")
    block = f"\n/* ─── {title} ({fname}) ──────────────────────────────────────────── */\n{css}\n"
    path.write_text(path.read_text(encoding="utf-8") + block, encoding="utf-8")
    print(f"strategy.css + {fname}")


def build_components() -> None:
    CSS_COMPONENTS.mkdir(parents=True, exist_ok=True)
    for rel_path, out_name, title in COMPONENT_FILES:
        src = TPL / rel_path
        css = extract_first_style(src.read_text(encoding="utf-8"))
        if not css:
            raise SystemExit(f"{rel_path}: no style")
        header = f"/**\n * components/{out_name} — {title}\n */\n\n"
        (CSS_COMPONENTS / out_name).write_text(header + css + "\n", encoding="utf-8")
        text = re.sub(r"<style>\s*.*?\s*</style>\s*", "", src.read_text(encoding="utf-8"), count=1, flags=re.S)
        src.write_text(text, encoding="utf-8")
        print(f"OK component {rel_path} → {out_name}")


def wire_component_links() -> None:
    zen_base = TPL / "layouts/zen_base.html"
    zb = zen_base.read_text(encoding="utf-8")
    sk_link = link_tag("css/components/skeleton.css")
    if "skeleton.css" not in zb:
        zb = zb.replace(
            "  <link rel=\"stylesheet\" href=\"{{ url_for('static', filename='css/zen-finance.css') }}\">\n{% endblock %}",
            "  <link rel=\"stylesheet\" href=\"{{ url_for('static', filename='css/zen-finance.css') }}\">\n  "
            + sk_link
            + "\n{% endblock %}",
            1,
        )
        zen_base.write_text(zb, encoding="utf-8")
        print("zen_base.html + skeleton.css")

    base = TPL / "base.html"
    bb = base.read_text(encoding="utf-8")
    widget_links = "\n".join(
        [
            "    "
            + link_tag(f"css/components/{name}")
            for _, name, _ in COMPONENT_FILES
            if name != "skeleton.css"
        ]
    )
    if "evidence-card.css" not in bb:
        bb = bb.replace(
            "{% block extra_css %}{% endblock %}",
            widget_links + "\n    {% block extra_css %}{% endblock %}",
            1,
        )
        base.write_text(bb, encoding="utf-8")
        print("base.html + component CSS links")


def main() -> None:
    build_multi_page_css(
        CSS_PAGES / "portfolio.css",
        "/**\n * pages/portfolio.css — 组合 / 交易 / 投顾\n"
        " * Depends on: design-tokens.css, common.css\n */\n\n",
        PORTFOLIO_TEMPLATES,
    )
    build_multi_page_css(
        CSS_PAGES / "user.css",
        "/**\n * pages/user.css — 朋友圈 / 用户光谱\n"
        " * Depends on: design-tokens.css, common.css\n */\n\n",
        USER_TEMPLATES,
    )
    build_multi_page_css(
        CSS_PAGES / "admin.css",
        "/**\n * pages/admin.css — 管理后台\n"
        " * Depends on: design-tokens.css, common.css\n */\n\n",
        ADMIN_TEMPLATES,
    )
    build_multi_page_css(
        CSS_PAGES / "zen-pages.css",
        "/**\n * pages/zen-pages.css — 禅意终端 / 3D 共鸣场（base 壳内页）\n"
        " * Complements: zen-finance.css\n */\n\n",
        ZEN_TEMPLATES,
    )

    append_strategy_css("collaboration_workspace.html", "Collaboration workspace")
    build_components()

    migrate_extra_css([t[0] for t in PORTFOLIO_TEMPLATES], "portfolio.css")
    migrate_extra_css([t[0] for t in USER_TEMPLATES], "user.css")
    migrate_extra_css([t[0] for t in ADMIN_TEMPLATES], "admin.css")
    for fname, _ in ZEN_TEMPLATES:
        migrate_zen_page(fname)
    migrate_extra_css(["collaboration_workspace.html"], "strategy.css")

    wire_component_links()
    print("Phase 5/6 batch complete")


if __name__ == "__main__":
    main()
