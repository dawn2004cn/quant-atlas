"""
Quant Atlas skill package.
"""

from app.core.skills import SkillRegistry


# Register quant-atlas as a built-in skill on import
def register_skill():
    from pathlib import Path
    registry = SkillRegistry(Path('skills'))
    manifests = registry.discover_skills()
    for m in manifests:
        if m.name == 'quant-atlas':
            registry.load_skill(m)
            registry.activate_skill('quant-atlas')
            return m
    return None
