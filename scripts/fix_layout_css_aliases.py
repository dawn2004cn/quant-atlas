"""Fix corrupted dual-selector aliases in quant-atlas-layout.css."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYOUT = ROOT / "static/css/quant-atlas-layout.css"

FIXES: list[tuple[str, str]] = [
    (".qa-metric, .metrics, .metrics", ".qa-metrics, .metrics"),
    (".qa-metric, .metric span", ".qa-metric span, .metric span"),
    (".qa-metric, .metric strong", ".qa-metric strong, .metric strong"),
    (".qa-head, .head h3", ".qa-head h3, .head h3"),
    (".qa-brand, .brand h1", ".qa-brand h1, .brand h1"),
    (".qa-brand, .brand p", ".qa-brand p, .brand p"),
    (".qa-asset, .asset b,", ".qa-asset b, .asset b,"),
    (".qa-asset, .asset small", ".qa-asset small, .asset small"),
    (".qa-module, .module-top, .module-top", ".qa-module-top, .module-top"),
    (".qa-module, .module-id, .module-id", ".qa-module-id, .module-id"),
    (".qa-module, .module h3", ".qa-module h3, .module h3"),
    (".qa-module, .module p", ".qa-module p, .module p"),
    (".qa-module, .module:hover", ".qa-module:hover, .module:hover"),
    (".qa-module, .module:focus-within", ".qa-module:focus-within, .module:focus-within"),
    (".qa-drawer, .drawer.open", ".qa-drawer.open, .drawer.open"),
    (".qa-drawer, .drawer-close, .close", ".qa-drawer-close, .drawer #close, #close"),
    (".qa-spec, .spec div", ".qa-spec div, .spec div"),
    (".qa-spec, .spec span", ".qa-spec span, .spec span"),
    (".qa-toast-inline, .toast.show", ".qa-toast-inline.show, .toast.show"),
    (".qa-side, .side.open", ".qa-side.open, .side.open"),
    (".qa-side, .side-toggle", ".qa-side-toggle, .side-toggle"),
    (".qa-section-head, .section-head h2", ".qa-section-head h2, .section-head h2"),
    (".qa-hero, section.hero h2", ".qa-hero h2, section.hero h2"),
    (".qa-search, .search input,", ".qa-search input, .search input,"),
    (
        ".qa-search, .search input::placeholder",
        ".qa-search input::placeholder, .search input::placeholder",
    ),
    (
        ".qa-nav-btn, .nav-btn span:first-child",
        ".qa-nav-btn span:first-child, .nav-btn span:first-child",
    ),
    (
        ".qa-nav-btn, .nav-btn span:last-child",
        ".qa-nav-btn span:last-child, .nav-btn span:last-child",
    ),
    (
        ".qa-nav-btn, .nav-btn.active span:last-child",
        ".qa-nav-btn.active span:last-child, .nav-btn.active span:last-child",
    ),
    (
        ".qa-mobile-tabs, .mobile-tabs button",
        ".qa-mobile-tabs button, .mobile-tabs button",
    ),
    (
        ".qa-mobile-tabs, .mobile-tabs button.active",
        ".qa-mobile-tabs button.active, .mobile-tabs button.active",
    ),
    (".qa-rail, .rail .qa-brand, .brand,", ".qa-rail .qa-brand, .rail .brand,"),
    (
        ".qa-rail, .rail .qa-nav-title, .nav-title,",
        ".qa-rail .qa-nav-title, .rail .nav-title,",
    ),
    (".qa-rail, .rail > .qa-card", ".qa-rail > .qa-card, .rail > .card"),
    (
        ".qa-hero, section.hero-main, .hero-main,\n.qa-mark, .market, .market",
        ".qa-hero-main, .hero-main,\n.qa-market, .market",
    ),
    (
        '[data-theme="light"] .qa-search, .search input,',
        '[data-theme="light"] .qa-search input, [data-theme="light"] .search input,',
    ),
    (
        '[data-theme="light"] .qa-select, .select',
        '[data-theme="light"] .qa-select, [data-theme="light"] .select',
    ),
    (
        '[data-theme="light"] .qa-btn-primary, .primary',
        '[data-theme="light"] .qa-btn-primary, [data-theme="light"] .primary',
    ),
    (
        '[data-theme="light"] .qa-btn-secondary, .secondary,',
        '[data-theme="light"] .qa-btn-secondary, [data-theme="light"] .secondary,',
    ),
    (
        '[data-theme="light"] .qa-btn-ghost, .ghost',
        '[data-theme="light"] .qa-btn-ghost, [data-theme="light"] .ghost',
    ),
    (
        '[data-theme="light"] .qa-nav-btn, .nav-btn.active span:last-child',
        (
            '[data-theme="light"] .qa-nav-btn.active span:last-child, '
            '[data-theme="light"] .nav-btn.active span:last-child'
        ),
    ),
    (
        '[data-theme="light"] .qa-mobile-tabs, .mobile-tabs button.active',
        (
            '[data-theme="light"] .qa-mobile-tabs button.active, '
            '[data-theme="light"] .mobile-tabs button.active'
        ),
    ),
    (
        '[data-theme="light"] .qa-toast-inline, .toast',
        '[data-theme="light"] .qa-toast-inline, [data-theme="light"] .toast',
    ),
    (
        '[data-theme="light"] .qa-mark, .mark',
        '[data-theme="light"] .qa-mark, [data-theme="light"] .mark',
    ),
    (
        '[data-theme="light"] .qa-asset, .asset',
        '[data-theme="light"] .qa-asset, [data-theme="light"] .asset',
    ),
    (
        '[data-theme="light"] .qa-rail, .rail',
        '[data-theme="light"] .qa-rail, [data-theme="light"] .rail',
    ),
    (
        "body.qa-compact .qa-module, .module p",
        "body.qa-compact .qa-module p, body.qa-compact .module p",
    ),
    (
        "body.qa-compact .qa-module, .module",
        "body.qa-compact .qa-module, body.qa-compact .module",
    ),
]

DUPLICATE_DRAWER = """
/* Module detail drawer (tmp/design parity) */
.qa-drawer.open, .drawer.open,
.drawer.open {
    transform: translateX(0);
}

@media (min-width: 1181px) {
    .qa-drawer, .drawer,
    .drawer {
        position: fixed;
        right: 0;
        top: 0;
        z-index: 90;
        width: min(420px, 100vw);
        height: 100vh;
        transform: translateX(100%);
    }
}

@media (max-width: 1180px) {
    .qa-drawer, .drawer,
    .drawer {
        position: fixed;
        left: 14px;
        right: 14px;
        bottom: calc(90px + env(safe-area-inset-bottom));
        top: auto;
        width: auto;
        height: auto;
        max-height: 70vh;
        border-radius: 24px;
        transform: translateY(120%);
    }

    .qa-drawer.open, .drawer.open,
    .drawer.open {
        transform: translateY(0);
    }
}
"""

RESPONSIVE_DRAWER = """

@media (max-width: 1180px) {
    .qa-drawer, .drawer {
        left: 14px;
        right: 14px;
        bottom: calc(90px + env(safe-area-inset-bottom));
        top: auto;
        width: auto;
        height: auto;
        max-height: 70vh;
        border-radius: 24px;
        border-left: none;
        transform: translateY(120%);
    }

    .qa-drawer.open, .drawer.open {
        transform: translateY(0);
    }
}
"""


def main() -> None:
    raw = LAYOUT.read_bytes()
    content = raw.decode("utf-8", errors="replace")
    content = content.replace("\ufffd", "—")
    for old, new in FIXES:
        count = content.count(old)
        if count:
            content = content.replace(old, new)
            print(f"fixed {count}x: {old[:60]}...")
        else:
            print(f"skip (not found): {old[:60]}...")

    if DUPLICATE_DRAWER.strip() in content:
        content = content.replace(DUPLICATE_DRAWER, "")
        print("removed duplicate drawer block")

    marker = ".qa-toast-inline.show, .toast.show {"
    if RESPONSIVE_DRAWER.strip() not in content and marker in content:
        idx = content.index(marker)
        end = content.index("}", idx) + 1
        content = content[:end] + RESPONSIVE_DRAWER + content[end:]
        print("inserted responsive drawer rules")

    LAYOUT.write_text(content, encoding="utf-8")
    print("done")


if __name__ == "__main__":
    main()
