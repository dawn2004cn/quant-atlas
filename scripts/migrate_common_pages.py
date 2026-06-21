"""Migrate high-traffic pages: strategy, marketplace, stock detail, system hub."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "app/presentation/web/templates"
CSS_PAGES = ROOT / "static/css/pages"
CSS_COMPONENTS = ROOT / "static/css/components"

SYSTEM_MARKER = "/* ─── Shared system utilities"

STRATEGY_TEMPLATES: list[tuple[str, str]] = [
    ("backtest.html", "Backtest"),
    ("stock_selector.html", "Stock selector"),
    ("optimize.html", "Optimize"),
    ("attribution_dashboard.html", "Attribution dashboard"),
    ("signal_observations.html", "Signal observations"),
    ("signal_flag.html", "Signal flag"),
    ("long_term_select.html", "Long-term select"),
    ("strategy_compare.html", "Strategy compare"),
    ("strategy_snapshots.html", "Strategy snapshots"),
    ("professional_workbench.html", "Professional workbench"),
]

FACTOR_TEMPLATES: list[tuple[str, str]] = [
    ("factor_evolution.html", "Factor evolution"),
    ("factor_repository.html", "Factor repository"),
    ("factor_detail.html", "Factor detail"),
]

SYSTEM_TEMPLATES: list[tuple[str, str]] = [
    ("capabilities.html", "Capabilities"),
    ("integration_hub.html", "Integration hub"),
    ("message_center.html", "Message center"),
    ("profile.html", "Profile"),
    ("observability.html", "Observability"),
    ("task_center.html", "Task center"),
    ("task_detail.html", "Task detail"),
    ("alert_center.html", "Alert center"),
    ("retail_assistant.html", "Retail assistant"),
]

RESEARCH_LINK = (
    '<link rel="stylesheet" '
    'href="{{ url_for(\'static\', filename=\'css/pages/research.css\') }}">'
)


def extract_first_style(text: str) -> str:
    match = re.search(r"<style>\s*(.*?)\s*</style>", text, re.S)
    return match.group(1).strip() if match else ""


def tokenize_css(css: str) -> str:
    return (
        css.replace(
            "radial-gradient(circle at top right, rgba(16,63,145,0.15), transparent 35%), #fff;",
            "radial-gradient(circle at top right, color-mix(in srgb, var(--brand) 15%, transparent), transparent 35%), var(--surface-strong);",
        )
        .replace(
            "radial-gradient(circle at top right, rgba(16,63,145,0.12), transparent 35%), #fff;",
            "radial-gradient(circle at top right, color-mix(in srgb, var(--brand) 12%, transparent), transparent 35%), var(--surface-strong);",
        )
        .replace(
            "radial-gradient(circle at top right, rgba(16,63,145,0.12), transparent 35%),\n            #fff;",
            "radial-gradient(circle at top right, color-mix(in srgb, var(--brand) 12%, transparent), transparent 35%),\n            var(--surface-strong);",
        )
    )


def build_multi_page_css(
    out_path: Path,
    header: str,
    templates: list[tuple[str, str]],
) -> None:
    parts = [header]
    for fname, title in templates:
        css = tokenize_css(extract_first_style((TPL / fname).read_text(encoding="utf-8")))
        if not css:
            raise SystemExit(f"{fname}: no <style> to extract")
        parts.append(f"/* ─── {title} ({fname}) ──────────────────────────────────────────── */\n{css}\n\n")
    out_path.write_text("".join(parts), encoding="utf-8")
    print(f"wrote {out_path.name} ({len(templates)} sections)")


def append_system_css(templates: list[tuple[str, str]]) -> None:
    path = CSS_PAGES / "system.css"
    content = path.read_text(encoding="utf-8")
    idx = content.find(SYSTEM_MARKER)
    if idx == -1:
        raise SystemExit("system.css: marker not found")
    blocks: list[str] = []
    for fname, title in templates:
        css = tokenize_css(extract_first_style((TPL / fname).read_text(encoding="utf-8")))
        if not css:
            raise SystemExit(f"{fname}: no <style>")
        blocks.append(f"/* ─── {title} ({fname}) ──────────────────────────────────────────── */\n{css}\n\n")
    path.write_text(content[:idx] + "".join(blocks) + content[idx:], encoding="utf-8")
    print(f"system.css +{len(templates)} sections")


def link_tag(css_name: str) -> str:
    return (
        '<link rel="stylesheet" '
        f'href="{{{{ url_for(\'static\', filename=\'css/pages/{css_name}\') }}}}">'
    )


def replace_one_style(text: str, link: str) -> str:
    new_text, count = re.subn(r"<style>\s*.*?\s*</style>", link, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"expected 1 style replacement, got {count}")
    return new_text


def migrate_list(templates: list[str], css_file: str) -> None:
    link = link_tag(css_file)
    for fname in templates:
        path = TPL / fname
        path.write_text(replace_one_style(path.read_text(encoding="utf-8"), link), encoding="utf-8")
        print(f"OK {fname} → {css_file}")


def migrate_standalone(fname: str, css_file: str) -> None:
    path = TPL / fname
    path.write_text(replace_one_style(path.read_text(encoding="utf-8"), link_tag(css_file)), encoding="utf-8")
    print(f"OK standalone {fname} → {css_file}")


def build_stock_detail_css() -> None:
    sd_css = tokenize_css(extract_first_style((TPL / "stock_detail.html").read_text(encoding="utf-8")))
    ws_css = extract_first_style((TPL / "components/stock/workspace_shell.html").read_text(encoding="utf-8"))
    header = (
        "/**\n * pages/stock-detail.css — 个股详情工作台\n"
        " * Depends on: design-tokens.css, common.css\n */\n\n"
    )
    body = f"/* ─── stock_detail.html ──────────────────────────────────────────── */\n{sd_css}\n\n"
    if ws_css:
        body += f"/* ─── workspace_shell.html ───────────────────────────────────────── */\n{ws_css}\n"
    (CSS_PAGES / "stock-detail.css").write_text(header + body, encoding="utf-8")
    print("stock-detail.css written")


def migrate_stock_detail() -> None:
    path = TPL / "stock_detail.html"
    text = path.read_text(encoding="utf-8")
    text = replace_one_style(text, link_tag("stock-detail.css"))
    text = re.sub(
        r"<style>\[x-cloak\]\s*\{\s*display:\s*none\s*!important;\s*\}</style>\s*",
        "",
        text,
        count=1,
    )
    path.write_text(text, encoding="utf-8")
    print("OK stock_detail.html → stock-detail.css")


def migrate_workspace_shell() -> None:
    path = TPL / "components/stock/workspace_shell.html"
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"<style>\s*.*?\s*</style>\s*", "", text, count=1, flags=re.S)
    path.write_text(text, encoding="utf-8")
    print("OK workspace_shell.html (styles → stock-detail.css)")


def add_x_cloak_to_common() -> None:
    common = ROOT / "static/css/common.css"
    text = common.read_text(encoding="utf-8")
    if "[x-cloak]" in text:
        print("common.css: x-cloak already present")
        return
    needle = ".qa-is-hidden { display: none; }"
    if needle not in text:
        raise SystemExit("common.css: qa-is-hidden anchor not found")
    text = text.replace(
        needle,
        f"{needle}\n[x-cloak] {{ display: none !important; }}",
        1,
    )
    common.write_text(text, encoding="utf-8")
    print("common.css: added [x-cloak]")


def main() -> None:
    build_multi_page_css(
        CSS_PAGES / "strategy.css",
        "/**\n * pages/strategy.css — 回测 / 选股 / 策略工具\n"
        " * Depends on: design-tokens.css, common.css\n */\n\n",
        STRATEGY_TEMPLATES,
    )
    build_multi_page_css(
        CSS_PAGES / "marketplace.css",
        "/**\n * pages/marketplace.css — Alpha 市集\n"
        " * Depends on: design-tokens.css, common.css\n */\n\n",
        [("marketplace.html", "Alpha marketplace")],
    )
    build_multi_page_css(
        CSS_PAGES / "alpha-factory.css",
        "/**\n * pages/alpha-factory.css — Alpha 工厂\n"
        " * Depends on: design-tokens.css, common.css\n */\n\n",
        [("alpha_factory.html", "Alpha factory")],
    )
    build_multi_page_css(
        CSS_PAGES / "factor.css",
        "/**\n * pages/factor.css — 因子库 / 进化\n"
        " * Depends on: design-tokens.css, common.css\n */\n\n",
        FACTOR_TEMPLATES,
    )
    build_multi_page_css(
        CSS_PAGES / "data-lake.css",
        "/**\n * pages/data-lake.css — 数据湖健康看板\n"
        " * Depends on: design-tokens.css, common.css\n */\n\n",
        [("data_lake_health.html", "Data lake health")],
    )
    build_multi_page_css(
        CSS_PAGES / "strategy-wizard.css",
        "/**\n * pages/strategy-wizard.css — 策略向导（独立页）\n"
        " * Depends on: design-tokens.css, common.css\n */\n\n",
        [("strategy_wizard.html", "Strategy wizard")],
    )

    append_system_css(SYSTEM_TEMPLATES)
    build_stock_detail_css()

    migrate_list([t[0] for t in STRATEGY_TEMPLATES], "strategy.css")
    migrate_list(["marketplace.html"], "marketplace.css")
    migrate_list(["alpha_factory.html"], "alpha-factory.css")
    migrate_list([t[0] for t in FACTOR_TEMPLATES], "factor.css")
    migrate_standalone("data_lake_health.html", "data-lake.css")
    migrate_standalone("strategy_wizard.html", "strategy-wizard.css")
    migrate_list([t[0] for t in SYSTEM_TEMPLATES], "system.css")

    add_x_cloak_to_common()
    migrate_stock_detail()
    migrate_workspace_shell()
    print("High-traffic migration complete")


if __name__ == "__main__":
    main()
