from __future__ import annotations

"""Skills marketplace routes for browsing, installing, and managing skills."""

import logging
from pathlib import Path

from flask import (
    Blueprint,
    jsonify,
    render_template,
    request,
    url_for,
)
from flask_login import login_required

from app.core.skills import SkillInstaller, SkillManifest, SkillRegistry

logger = logging.getLogger(__name__)

# Skill categories and icons for built-in skills registry
DEFAULT_SKILL_ICONS = {
    "quant-atlas": "🚀",
    "quant-research": "🔬",
    "market-monitor": "📊",
    "ai-analyst": "🤖",
    "risk-guard": "🛡️",
    "portfolio-optimizer": "🎯",
    "data-feed": "📡",
    "strategy-builder": "🧩",
    "alpha-factory": "⚙️",
    "backtest-engine": "🔧",
}

DEFAULT_SKILL_CATEGORIES = {
    "quant-atlas": "trading",
    "quant-research": "analysis",
    "ai-analyst": "ai",
    "risk-guard": "risk",
    "portfolio-optimizer": "portfolio",
    "data-feed": "utility",
    "strategy-builder": "trading",
    "alpha-factory": "trading",
    "backtest-engine": "analysis",
}

DEFAULT_SKILL_RATINGS = {
    "quant-atlas": 4.8,
    "quant-research": 4.5,
    "ai-analyst": 4.6,
    "risk-guard": 4.3,
    "portfolio-optimizer": 4.4,
    "data-feed": 4.2,
    "strategy-builder": 4.7,
    "alpha-factory": 4.1,
    "backtest-engine": 4.5,
}


def _get_builtin_catalog_skills() -> list[dict]:
    """Build the list of available skills in the marketplace catalog."""
    from app.config import BASE_DIR
    skills_dir = BASE_DIR / "skills"

    registry = SkillRegistry(skills_dir)
    installed_manifests = registry.discover_skills()
    installed_names = {m.name for m in installed_manifests}

    base_url = url_for("static", filename="")

    # Catalog of available skills (installed + available in marketplace)
    catalog = []

    # Add builtin quant-atlas from filesystem
    for manifest in installed_manifests:
        catalog.append(_manifest_to_catalog(manifest, installed_names, True))

    # Add some default available skills (for demo purposes)
    default_skills = [
        ("quant-research", "Quant Research", "1.0.0", "AI-powered research automation for quantitative analysis, backtesting, and report generation.", "Quant Atlas Team", "analysis", 4.5),
        ("ai-analyst", "AI Analyst", "2.1.0", "Advanced AI-powered market analysis with sentiment analysis, pattern recognition, and predictive models.", "AI Lab", "ai", 4.6),
        ("risk-guard", "Risk Guard", "1.2.0", "Comprehensive risk management system with VaR, stress testing, and position sizing recommendations.", "Risk Team", "risk", 4.3),
        ("portfolio-optimizer", "Portfolio Optimizer", "1.0.0", "Modern portfolio theory optimizer with mean-variance, Black-Litterman, and risk-parity models.", "Quant Core", "portfolio", 4.4),
        ("data-feed", "Data Feed", "1.5.0", "Real-time and historical data feed connectors for global markets, crypto, and alternative data.", "Data Team", "utility", 4.2),
        ("strategy-builder", "Strategy Builder", "2.0.0", "Visual strategy builder with drag-and-drop, custom indicators, and paper trading.", "Strategy Team", "trading", 4.7),
        ("alpha-factory", "Alpha Factory", "1.3.0", "Factor mining and alpha generation engine with genetic programming and machine learning.", "Alpha Team", "trading", 4.1),
        ("backtest-engine", "Backtest Engine", "2.2.0", "High-performance backtest engine with event-driven simulation and detailed performance analytics.", "Quant Core", "analysis", 4.5),
    ]

    installed_catalog_names = {m["name"] for m in catalog}
    for name, display_name, version, desc, author, category, rating in default_skills:
        if name not in installed_catalog_names:
            catalog.append({
                "name": name,
                "display_name": display_name,
                "version": version,
                "description": desc,
                "author": author,
                "icon": DEFAULT_SKILL_ICONS.get(name, "🧩"),
                "category": category,
                "rating": rating,
                "tags": [category, "python", "flask"],
                "downloads": 0,
                "installed": name in installed_names,
                "type": "external",
                "is_active": False,
                "is_builtin": False,
            })

    return catalog


def _manifest_to_catalog(manifest: SkillManifest, installed_names: set[str], is_installed: bool = True) -> dict:
    """Convert a SkillManifest to a catalog dict."""
    registry = SkillRegistry(Path("skills"))
    loaded = registry.get_skill(manifest.name)
    is_active = loaded.is_active if loaded else False

    return {
        "name": manifest.name,
        "display_name": manifest.display_name,
        "version": manifest.version,
        "description": manifest.description,
        "author": manifest.author,
        "icon": DEFAULT_SKILL_ICONS.get(manifest.name, "🧩"),
        "category": DEFAULT_SKILL_CATEGORIES.get(manifest.name, "utility"),
        "rating": DEFAULT_SKILL_RATINGS.get(manifest.name, 4.0),
        "tags": [manifest.type, "python"],
        "downloads": 0,
        "installed": is_installed,
        "type": manifest.type,
        "is_active": is_active,
        "is_builtin": manifest.type == "builtin",
        "config": {},
        "path": str(registry.skills_dir / manifest.name) if is_installed else "",
    }


def register_routes(bp: Blueprint) -> None:
    """Register skills marketplace routes."""

    @bp.route("/skills")
    @login_required
    def marketplace():
        """Skill marketplace page - browse available skills."""
        catalog = _get_builtin_catalog_skills()
        return render_template("skills_marketplace.html", skills=catalog)

    @bp.route("/skills/installed")
    @login_required
    def installed():
        """Installed skills management page."""
        from app.config import BASE_DIR
        skills_dir = BASE_DIR / "skills"
        registry = SkillRegistry(skills_dir)
        loaded = registry.load_all_skills()

        skill_list = []
        active_count = 0
        builtin_count = 0
        external_count = 0

        for skill in loaded:
            is_active = registry.get_skill(skill.manifest.name)
            active_state = is_active.is_active if is_active else False
            if active_state:
                active_count += 1
            if skill.manifest.type == "builtin":
                builtin_count += 1
            else:
                external_count += 1

            skill_list.append({
                "name": skill.manifest.name,
                "display_name": skill.manifest.display_name,
                "version": skill.manifest.version,
                "description": skill.manifest.description,
                "author": skill.manifest.author,
                "icon": DEFAULT_SKILL_ICONS.get(skill.manifest.name, "🧩"),
                "type": skill.manifest.type,
                "is_active": active_state,
                "is_builtin": skill.manifest.type == "builtin",
                "config": skill.config or {},
                "path": str(skill.path),
            })

        stats = {
            "total": len(skill_list),
            "active": active_count,
            "builtin": builtin_count,
            "external": external_count,
        }

        return render_template("skills_installed.html", skills=skill_list, stats=stats)

    @bp.route("/api/skills/install", methods=["POST"])
    @login_required
    def api_install():
        """API endpoint to install a skill."""
        data = request.get_json(silent=True) or {}
        skill_name = data.get("skill_name", "")
        auto_activate = data.get("auto_activate", True)

        if not skill_name:
            return jsonify({"success": False, "message": "技能名称不能为空"})

        from app.config import BASE_DIR
        skills_dir = BASE_DIR / "skills"

        try:
            installer = SkillInstaller(skills_dir)
            # For now, we simulate installation from a built-in template
            # In production, this would fetch from a registry/git repo
            # For demo: create a minimal skill dir
            from app.core.skills import SkillManifest
            target_dir = skills_dir / skill_name
            if target_dir.exists():
                return jsonify({"success": False, "message": f"技能 {skill_name} 已安装"})

            target_dir.mkdir(parents=True, exist_ok=True)

            manifest = SkillManifest(
                name=skill_name,
                display_name=skill_name.replace("-", " ").title(),
                version="1.0.0",
                description=f"{skill_name} 技能",
                author="Community",
                type="external",
            )
            import json
            with open(target_dir / "skill.json", "w", encoding="utf-8") as f:
                json.dump(manifest.to_json(), f, ensure_ascii=False, indent=2)

            (target_dir / "__init__.py").touch()

            if auto_activate:
                registry = SkillRegistry(skills_dir)
                registry.load_skill(manifest)
                registry.activate_skill(skill_name)

            return jsonify({"success": True, "message": f"技能 {skill_name} 安装成功"})
        except Exception as e:
            logger.error("Failed to install skill %s: %s", skill_name, e, exc_info=True)
            return jsonify({"success": False, "message": f"安装失败: {str(e)}"})

    @bp.route("/api/skills/uninstall", methods=["POST"])
    @login_required
    def api_uninstall():
        """API endpoint to uninstall a skill."""
        data = request.get_json(silent=True) or {}
        skill_name = data.get("skill_name", "")

        if not skill_name:
            return jsonify({"success": False, "message": "技能名称不能为空"})

        from app.config import BASE_DIR
        skills_dir = BASE_DIR / "skills"

        # Prevent uninstalling builtin skills
        registry = SkillRegistry(skills_dir)
        skill = registry.get_skill(skill_name)
        if skill and skill.manifest.type == "builtin":
            return jsonify({"success": False, "message": "内置技能无法卸载"})

        try:
            installer = SkillInstaller(skills_dir)
            installer.uninstall(skill_name)
            return jsonify({"success": True, "message": f"技能 {skill_name} 卸载成功"})
        except Exception as e:
            logger.error("Failed to uninstall skill %s: %s", skill_name, e, exc_info=True)
            return jsonify({"success": False, "message": f"卸载失败: {str(e)}"})

    @bp.route("/api/skills/toggle", methods=["POST"])
    @login_required
    def api_toggle():
        """API endpoint to activate/deactivate a skill."""
        data = request.get_json(silent=True) or {}
        skill_name = data.get("skill_name", "")
        action = data.get("action", "activate")

        if not skill_name:
            return jsonify({"success": False, "message": "技能名称不能为空"})

        from app.config import BASE_DIR
        skills_dir = BASE_DIR / "skills"
        registry = SkillRegistry(skills_dir)

        if action == "activate":
            registry.activate_skill(skill_name)
        else:
            registry.deactivate_skill(skill_name)

        return jsonify({"success": True, "message": f"技能 {skill_name} 已{'启用' if action == 'activate' else '禁用'}"})

    @bp.route("/api/skills/config", methods=["POST"])
    @login_required
    def api_config():
        """API endpoint to update skill config."""
        data = request.get_json(silent=True) or {}
        skill_name = data.get("skill_name", "")
        key = data.get("key", "")
        value = data.get("value", "")

        if not skill_name or not key:
            return jsonify({"success": False, "message": "参数不完整"})

        from app.config import BASE_DIR
        skills_dir = BASE_DIR / "skills"
        registry = SkillRegistry(skills_dir)
        skill = registry.get_skill(skill_name)
        if not skill:
            return jsonify({"success": False, "message": f"技能 {skill_name} 未找到"})

        skill.config[key] = value
        return jsonify({"success": True, "message": "配置更新成功"})
