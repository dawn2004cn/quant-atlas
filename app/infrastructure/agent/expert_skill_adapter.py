from typing import Any

from app.core.logger import get_logger
from app.domain.ports.agent_ports import ExpertSkillPort
from app.infrastructure.agent.skills.loader import SkillsLoader

logger = get_logger(__name__)

class ExpertSkillAdapter(ExpertSkillPort):
    """Adapter for specialized financial expert skills.

    This adapter provides access to the 74+ project-standard skills.
    """

    def __init__(self):
        try:
            self.loader = SkillsLoader()
            logger.info(f"ExpertSkillAdapter initialized with {len(self.loader.skills)} skills")
        except Exception as e:
            logger.error(f"Failed to initialize expert skills loader: {e}")
            self.loader = None

    def load_skill(
        self,
        skill_name: str,
    ) -> dict[str, Any]:
        """Load a specific skill's content."""
        if self.loader is None:
            return {"error": "Skills loader not initialized"}

        content = self.loader.get_content(skill_name)
        if content.startswith("Error:"):
            return {"error": content}

        return {
            "name": skill_name,
            "content": content,
            "status": "ok"
        }


    def list_skills(self) -> list[str]:
        """List all available skills."""
        if self.loader is None:
            return []
        return [s.name for s in self.loader.skills]
