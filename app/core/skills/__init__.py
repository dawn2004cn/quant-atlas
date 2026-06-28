from __future__ import annotations

"""
Skill infrastructure for Quant Atlas - supports external skills/plugins like Hermes/OpenClaw.
"""

import importlib
import json
import logging
import os
import shutil
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SkillManifest:
    """Skill manifest from skill.json"""
    name: str
    display_name: str
    version: str
    description: str
    author: str = ""
    license: str = "MIT"
    type: str = "external"  # builtin, external
    entry_point: str = ""
    api_entry_point: str = ""
    dependencies: list[str] = field(default_factory=list)
    provides: list[str] = field(default_factory=list)
    config_schema: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, path: Path) -> SkillManifest:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        return cls(**data)

    def to_json(self) -> dict[str, Any]:
        return {
            'name': self.name,
            'display_name': self.display_name,
            'version': self.version,
            'description': self.description,
            'author': self.author,
            'license': self.license,
            'type': self.type,
            'entry_point': self.entry_point,
            'api_entry_point': self.api_entry_point,
            'dependencies': self.dependencies,
            'provides': self.provides,
            'config_schema': self.config_schema,
        }


@dataclass
class LoadedSkill:
    """A skill that has been loaded and registered"""
    manifest: SkillManifest
    path: Path
    web_pages: Callable | None = None
    api_routes: Callable | None = None
    config: dict[str, Any] = field(default_factory=dict)
    is_active: bool = False


class SkillRegistry:
    """Central registry for all skills (builtin + external)"""

    _instance: SkillRegistry | None = None
    _skills: dict[str, LoadedSkill] = {}
    _skills_dir: Path

    def __new__(cls, skills_dir: Path | None = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._skills_dir = skills_dir or Path('skills')
            cls._instance._skills = {}
            cls._instance._load_order: list[str] = []
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset singleton (for testing)"""
        cls._instance = None

    @property
    def skills_dir(self) -> Path:
        return self._skills_dir

    @property
    def skills(self) -> dict[str, LoadedSkill]:
        return self._skills

    @property
    def load_order(self) -> list[str]:
        return self._load_order

    def discover_skills(self) -> list[SkillManifest]:
        """Discover all skills in skills/ directory"""
        manifests = []
        if not self._skills_dir.exists():
            logger.warning(f'Skills directory does not exist: {self._skills_dir}')
            return manifests

        for skill_dir in self._skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            manifest_path = skill_dir / 'skill.json'
            if manifest_path.exists():
                try:
                    manifest = SkillManifest.from_json(manifest_path)
                    manifests.append(manifest)
                    logger.info(f'Discovered skill: {manifest.name} v{manifest.version}')
                except Exception as e:
                    logger.error(f'Failed to load manifest for {skill_dir.name}: {e}')
            else:
                logger.warning(f'No skill.json in {skill_dir}')
        return manifests

    def load_skill(self, manifest: SkillManifest) -> LoadedSkill:
        """Load and register a skill from its manifest"""
        skill_dir = self._skills_dir / manifest.name
        if not skill_dir.exists():
            raise FileNotFoundError(f'Skill directory not found: {skill_dir}')

        # Add skill directory to sys.path for imports
        if str(skill_dir) not in sys.path:
            sys.path.insert(0, str(skill_dir))

        loaded = LoadedSkill(manifest=manifest, path=skill_dir)

        # Load web pages entry point
        if manifest.entry_point:
            try:
                module_path, func_name = manifest.entry_point.rsplit(':', 1)
                module = importlib.import_module(module_path)
                loaded.web_pages = getattr(module, func_name)
                logger.info(f'Loaded web pages for {manifest.name}')
            except Exception as e:
                logger.warning(f'Failed to load web pages for {manifest.name}: {e}')

        # Load API routes entry point
        if manifest.api_entry_point:
            try:
                module_path, func_name = manifest.api_entry_point.rsplit(':', 1)
                module = importlib.import_module(module_path)
                loaded.api_routes = getattr(module, func_name)
                logger.info(f'Loaded API routes for {manifest.name}')
            except Exception as e:
                logger.warning(f'Failed to load API routes for {manifest.name}: {e}')

        # Load default config from schema
        loaded.config = {
            k: v.get('default', '') for k, v in manifest.config_schema.get('properties', {}).items()
        }

        self._skills[manifest.name] = loaded
        self._load_order.append(manifest.name)
        return loaded

    def load_all_skills(self) -> list[LoadedSkill]:
        """Discover and load all skills in order (builtin first)"""
        manifests = self.discover_skills()
        # Sort: builtin first, then by name
        manifests.sort(key=lambda m: (m.type != 'builtin', m.name))

        loaded = []
        for manifest in manifests:
            try:
                skill = self.load_skill(manifest)
                loaded.append(skill)
            except Exception as e:
                logger.error(f'Failed to load skill {manifest.name}: {e}')
        return loaded

    def get_skill(self, name: str) -> LoadedSkill | None:
        return self._skills.get(name)

    def activate_skill(self, name: str, config: dict[str, Any] | None = None) -> bool:
        """Activate a loaded skill with optional config override"""
        skill = self._skills.get(name)
        if not skill:
            logger.error(f'Skill not found: {name}')
            return False
        if config:
            skill.config.update(config)
        skill.is_active = True
        logger.info(f'Activated skill: {name}')
        return True

    def deactivate_skill(self, name: str) -> bool:
        """Deactivate a skill"""
        skill = self._skills.get(name)
        if not skill:
            return False
        skill.is_active = False
        logger.info(f'Deactivated skill: {name}')
        return True

    def register_blueprints(self, flask_app) -> int:
        """Register all active skills' blueprints with Flask app"""
        count = 0
        for skill in self._skills.values():
            if not skill.is_active:
                continue
            if skill.web_pages:
                try:
                    # Create blueprint from skill
                    from flask import Blueprint
                    bp = Blueprint(f'skill_{skill.manifest.name}', __name__,
                                   template_folder=str(skill.path / 'templates'),
                                   static_folder=str(skill.path / 'static'))
                    skill.web_pages(bp)
                    flask_app.register_blueprint(bp)
                    count += 1
                except Exception as e:
                    logger.error(f'Failed to register web pages for {skill.manifest.name}: {e}')
            if skill.api_routes:
                try:
                    from flask import Blueprint
                    bp = Blueprint(f'skill_{skill.manifest.name}_api', __name__,
                                   url_prefix=f'/api/v1/skills/{skill.manifest.name}')
                    skill.api_routes(bp)
                    flask_app.register_blueprint(bp)
                    count += 1
                except Exception as e:
                    logger.error(f'Failed to register API routes for {skill.manifest.name}: {e}')
        return count


class SkillInstaller:
    """Handle skill installation from various sources"""

    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def install_from_local(self, source_path: Path, skill_name: str | None = None) -> SkillManifest:
        """Install skill from local directory"""
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f'Source not found: {source}')

        manifest_path = source / 'skill.json'
        if not manifest_path.exists():
            raise ValueError(f'No skill.json in {source}')

        manifest = SkillManifest.from_json(manifest_path)
        target_name = skill_name or manifest.name
        target_dir = self.skills_dir / target_name

        if target_dir.exists():
            raise FileExistsError(f'Skill already installed: {target_name}')

        shutil.copytree(source, target_dir)
        logger.info(f'Installed skill {target_name} from {source}')
        return manifest

    def install_from_git(self, repo_url: str, branch: str = 'main', skill_name: str | None = None) -> SkillManifest:
        """Install skill from git repository"""
        import subprocess
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / 'skill_repo'
            subprocess.run(['git', 'clone', '--depth', '1', '--branch', branch, repo_url, str(tmp_path)],  # git clone with user-supplied URL; list form safe against shell injection
                           check=True, capture_output=True)
            return self.install_from_local(tmp_path, skill_name)

    def install_from_zip(self, zip_path: Path, skill_name: str | None = None) -> SkillManifest:
        """Install skill from zip archive"""
        import zipfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(tmp_path)
            # Find skill.json
            for item in tmp_path.rglob('skill.json'):
                return self.install_from_local(item.parent, skill_name)
            raise ValueError('No skill.json found in archive')

    def uninstall(self, skill_name: str) -> bool:
        """Uninstall a skill"""
        skill_dir = self.skills_dir / skill_name
        if not skill_dir.exists():
            return False
        shutil.rmtree(skill_dir)
        logger.info(f'Uninstalled skill: {skill_name}')
        return True

    def list_installed(self) -> list[SkillManifest]:
        """List all installed skills"""
        registry = SkillRegistry(self.skills_dir)
        return registry.discover_skills()


def get_skill_registry(skills_dir: Path | None = None) -> SkillRegistry:
    """Get the global skill registry instance"""
    return SkillRegistry(skills_dir)


def init_skills(flask_app, skills_dir: Path | None = None) -> SkillRegistry:
    """Initialize skills system and register with Flask app"""
    registry = get_skill_registry(skills_dir)
    loaded = registry.load_all_skills()

    # Auto-activate builtin skills
    for skill in loaded:
        if skill.manifest.type == 'builtin':
            registry.activate_skill(skill.manifest.name)

    # Register blueprints
    count = registry.register_blueprints(flask_app)
    logger.info(f'Registered {count} skill blueprints')

    return registry
