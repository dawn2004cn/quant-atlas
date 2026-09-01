"""Canonical /api/v1 path contract — verify and repair route registration at boot."""

from __future__ import annotations

import importlib
import logging
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from flask import Blueprint, Flask

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path("app/presentation/web/templates")
TEMPLATE_FETCH_RE = re.compile(r"""fetch\(\s*['"](/api/v1/[^'"]+)['"]""")
# Paths built via JS string concat — not literal fetch targets.
DYNAMIC_FETCH_PREFIX_SKIP: tuple[str, ...] = (
    "/api/v1/stocks/",
    "/api/v1/decision/snapshots/",
    "/api/v1/decision/snapshots/public/",
    "/api/v1/strategy/snapshots/",
    "/api/v1/swarm/topology/presets/",
    "/api/v1/teams/",
    "/api/v1/truth/droplet/",
    "/api/v1/agent-swarm/swarm/status/",
    "/api/v1/system/celery/task/",
)


@dataclass(frozen=True)
class RouteModuleSpec:
    """A route module that must mount canonical API paths."""

    name: str
    module: str
    register_attr: str
    paths: tuple[str, ...]


# Frontend + tests expect these exact paths on the main /api/v1 blueprint.
CRITICAL_ROUTE_MODULES: tuple[RouteModuleSpec, ...] = (
    RouteModuleSpec(
        "jarvis",
        "app.presentation.api.routes_v1_jarvis",
        "register_jarvis_routes",
        ("/api/v1/jarvis/proactive",),
    ),
    RouteModuleSpec(
        "task_ops",
        "app.presentation.api.routes_v1_task_ops",
        "register_task_ops_routes",
        (
            "/api/v1/system/task-messages",
            "/api/v1/system/active-jobs",
        ),
    ),
    RouteModuleSpec(
        "compliance",
        "app.presentation.api.routes_v1_compliance",
        "register_compliance_routes",
        ("/api/v1/compliance/manifest",),
    ),
    RouteModuleSpec(
        "data_infrastructure",
        "app.presentation.api.routes_v1_data_infrastructure",
        "register_data_infrastructure_routes",
        (
            "/api/v1/data/timeseries-health",
            "/api/v1/data/timeseries-sync-history",
        ),
    ),
    RouteModuleSpec(
        "quant_ai",
        "app.presentation.api.routes_v1_quant_ai",
        "register_quant_ai_routes",
        ("/api/v1/backtest",),
    ),
    RouteModuleSpec(
        "nl",
        "app.presentation.api.routes_v1_nl",
        "register_nl_routes",
        (
            "/api/v1/nl/query",
            "/api/v1/nl-parser/query",
        ),
    ),
    RouteModuleSpec(
        "integration_stack",
        "app.presentation.api.routes_v1_integration_stack",
        "register_integration_stack_routes",
        ("/api/v1/integration/stack-status",),
    ),
    RouteModuleSpec(
        "system_health",
        "app.presentation.api.routes_v1_system_health",
        "register_system_health_routes",
        ("/api/v1/system/health",),
    ),
    RouteModuleSpec(
        "realtime",
        "app.presentation.api.routes_v1_realtime",
        "register_realtime_routes",
        ("/api/v1/realtime/status",),
    ),
    RouteModuleSpec(
        "zen_mode",
        "app.presentation.api.routes_v1_zen_mode",
        "register_zen_mode_routes",
        (
            "/api/v1/zen-mode/zen/search",
            "/api/v1/zen-mode/zen/toggle",
            "/api/v1/zen-mode/resonance/field",
        ),
    ),
    RouteModuleSpec(
        "provenance_explorer",
        "app.presentation.api.routes_v1_provenance",
        "register_provenance_routes",
        ("/api/v1/provenance/truth-dashboard",),
    ),
    RouteModuleSpec(
        "alert_center",
        "app.presentation.api.routes_v1_alert_center",
        "register_alert_center_routes",
        ("/api/v1/system/alerts/dispatch",),
    ),
    RouteModuleSpec(
        "shadow_account",
        "app.presentation.api.routes_v1_shadow_account",
        "register_shadow_account_routes",
        (
            "/api/v1/shadow-account/status",
            "/api/v1/shadow-account/analyze",
        ),
    ),
    RouteModuleSpec(
        "alpha_marketplace",
        "app.presentation.api.routes_v1_alpha_marketplace",
        "register_alpha_marketplace_routes",
        (
            "/api/v1/alpha/marketplace/listings",
            "/api/v1/alpha/marketplace/orders",
            "/api/v1/alpha/reputation/balance",
            "/api/v1/alpha/wallet/balance",
        ),
    ),
    RouteModuleSpec(
        "market_core",
        "app.presentation.api.routes_v1_market_core",
        "register_market_core_routes",
        (
            "/api/v1/markets/CN/quotes/page",
            "/api/v1/markets/CN/quotes",
        ),
    ),
)

# Wrong paths produced by Phase-2 sub-blueprint prefixes (keep as aliases).
LEGACY_PATH_ALIASES: tuple[tuple[str, str], ...] = (
    ("/api/v1/ai-agent/jarvis/proactive", "/api/v1/jarvis/proactive"),
    ("/api/v1/ai-agent/backtest", "/api/v1/backtest"),
    ("/api/v1/system/system/task-messages", "/api/v1/system/task-messages"),
    ("/api/v1/system/system/active-jobs", "/api/v1/system/active-jobs"),
    ("/api/v1/data/data/timeseries-health", "/api/v1/data/timeseries-health"),
    ("/api/v1/data/data/timeseries-sync-history", "/api/v1/data/timeseries-sync-history"),
    ("/api/v1/system/compliance/manifest", "/api/v1/compliance/manifest"),
    ("/api/v1/phase18/zen/search", "/api/v1/zen-mode/zen/search"),
    ("/api/v1/phase18/zen/toggle", "/api/v1/zen-mode/zen/toggle"),
    ("/api/v1/phase18/resonance/field", "/api/v1/zen-mode/resonance/field"),
)


def preload_critical_route_modules() -> None:
    """Import critical route modules so @register_routes side effects always run."""
    for spec in CRITICAL_ROUTE_MODULES:
        try:
            importlib.import_module(spec.module)
        except Exception:
            logger.warning(
                "Critical route module import failed: %s",
                spec.module,
                exc_info=True,
            )


def app_has_path(url_map, path: str, *, method: str | None = None) -> bool:
    """Check Flask url_map for an exact rule path."""
    for rule in url_map.iter_rules():
        if rule.rule != path:
            continue
        if method is None:
            return True
        if method.upper() in rule.methods:
            return True
    return False


def missing_canonical_paths(url_map, specs: Iterable[RouteModuleSpec] | None = None) -> list[str]:
    """Return canonical paths that are absent from the application url_map."""
    rules = [rule.rule for rule in url_map.iter_rules()]
    missing: list[str] = []
    for spec in specs or CRITICAL_ROUTE_MODULES:
        for path in spec.paths:
            if not path_registered_in_rules(rules, path):
                missing.append(path)
    return missing


def register_route_module_fallback(
    blueprint: Blueprint,
    ctx: object,
    spec: RouteModuleSpec,
    *,
    registered_names: set[str],
) -> bool:
    """Explicitly register a route module when auto-discovery skipped or failed."""
    if spec.name in registered_names:
        return False
    try:
        mod = importlib.import_module(spec.module)
        register_fn: Callable = getattr(mod, spec.register_attr)
        register_fn(blueprint, ctx)
        registered_names.add(spec.name)
        logger.info("Critical route fallback registered: %s", spec.name)
        return True
    except Exception:
        logger.error(
            "Critical route fallback failed for %s (%s)",
            spec.name,
            spec.module,
            exc_info=True,
        )
        return False


def _spec_already_mounted(blueprint: Blueprint, spec: RouteModuleSpec) -> bool:
    """True when every canonical path for *spec* is already on *blueprint* url_map."""
    rules = {rule.rule for rule in blueprint.url_map.iter_rules()}
    return all(path in rules for path in spec.paths)


def repair_unregistered_critical_modules(
    blueprint: Blueprint,
    ctx: object,
    registered_names: set[str],
) -> None:
    """Register critical modules that auto-discovery skipped or failed to load."""
    preload_critical_route_modules()
    for spec in CRITICAL_ROUTE_MODULES:
        if spec.name in registered_names or _spec_already_mounted(blueprint, spec):
            continue
        register_route_module_fallback(blueprint, ctx, spec, registered_names=registered_names)


def attach_legacy_path_aliases(app: Flask) -> int:
    """Mirror canonical handlers at legacy wrong-prefix paths."""
    url_map = app.url_map
    attached = 0
    for alias_path, canonical_path in LEGACY_PATH_ALIASES:
        if app_has_path(url_map, alias_path):
            continue
        canonical_rule = next((r for r in url_map.iter_rules() if r.rule == canonical_path), None)
        if canonical_rule is None:
            continue
        view_func = app.view_functions.get(canonical_rule.endpoint)
        if view_func is None:
            continue
        methods = {m for m in canonical_rule.methods if m not in ("HEAD", "OPTIONS")}
        if not methods:
            methods = {"GET"}
        safe_endpoint = f"legacy_alias_{attached}_{canonical_rule.endpoint.replace('.', '_')}"
        try:
            app.add_url_rule(
                alias_path,
                endpoint=safe_endpoint,
                view_func=view_func,
                methods=sorted(methods),
            )
            attached += 1
        except Exception:
            logger.debug(
                "Legacy alias skipped %s -> %s",
                alias_path,
                canonical_path,
                exc_info=True,
            )
    if attached:
        logger.info("Attached %d legacy API path aliases", attached)
    return attached


def finalize_v1_route_contract(app: Flask, *, strict: bool | None = None) -> list[str]:
    """Audit canonical paths and attach legacy aliases. Returns still-missing paths."""
    missing = missing_canonical_paths(app.url_map)
    if missing:
        logger.error(
            "API v1 contract missing %d canonical path(s): %s",
            len(missing),
            ", ".join(missing),
        )
    else:
        logger.info("API v1 canonical route contract OK (%d modules)", len(CRITICAL_ROUTE_MODULES))
    attach_legacy_path_aliases(app)
    assert_v1_route_contract(app, strict=strict, missing_canonical=missing)
    return missing


def rule_to_path_regex(rule: str) -> re.Pattern[str]:
    """Convert a Flask rule like /api/v1/markets/<market>/headlines to regex."""
    escaped: list[str] = []
    for segment in rule.split("/"):
        if not segment:
            continue
        if segment.startswith("<"):
            escaped.append("[^/]+")
        else:
            escaped.append(re.escape(segment))
    return re.compile("^/" + "/".join(escaped) + "$")


def path_registered_in_rules(rules: Iterable[str], path: str) -> bool:
    """Return True if *path* matches any Flask rule (exact or parameterized)."""
    rule_list = list(rules)
    if path in rule_list:
        return True
    for rule in rule_list:
        if "<" in rule and rule_to_path_regex(rule).match(path):
            return True
    return False


def collect_template_fetch_paths(
    templates_dir: Path | None = None,
) -> set[str]:
    """Literal ``fetch('/api/v1/...')`` paths from Jinja templates."""
    root = templates_dir or TEMPLATE_DIR
    paths: set[str] = set()
    if not root.is_dir():
        return paths
    for html in root.rglob("*.html"):
        text = html.read_text(encoding="utf-8", errors="ignore")
        for match in TEMPLATE_FETCH_RE.finditer(text):
            raw = match.group(1).split("?")[0]
            if any(raw.startswith(prefix) for prefix in DYNAMIC_FETCH_PREFIX_SKIP):
                continue
            paths.add(raw)
    return paths


def missing_template_fetch_paths(
    url_map,
    *,
    templates_dir: Path | None = None,
) -> list[str]:
    """Template fetch paths with no matching Flask rule."""
    rules = [rule.rule for rule in url_map.iter_rules()]
    return sorted(
        path
        for path in collect_template_fetch_paths(templates_dir)
        if not path_registered_in_rules(rules, path)
    )


def assert_v1_route_contract(
    app: Flask,
    *,
    strict: bool | None = None,
    missing_canonical: list[str] | None = None,
    check_templates: bool = False,
) -> None:
    """Raise when canonical (and optionally template) paths are missing in strict mode."""
    from app.bootstrap_components.service_readiness import is_strict_bootstrap

    if strict is None:
        strict = is_strict_bootstrap()
    if not strict:
        return

    missing = (
        missing_canonical
        if missing_canonical is not None
        else missing_canonical_paths(app.url_map)
    )
    if missing:
        raise RuntimeError(
            "API v1 canonical route contract failed — missing paths: "
            + ", ".join(missing)
        )

    if check_templates:
        tpl_missing = missing_template_fetch_paths(app.url_map)
        if tpl_missing:
            raise RuntimeError(
                "API v1 template fetch contract failed — missing paths: "
                + ", ".join(tpl_missing[:20])
                + (" ..." if len(tpl_missing) > 20 else "")
            )
