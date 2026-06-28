from __future__ import annotations

"""Knowledge Distillation: Converts successful swarm remediations into persistent expert skills."""


from typing import Any

from app.core.logger import get_logger
from app.infrastructure.agent.swarm.runtime import SwarmRuntime
from app.infrastructure.agent.swarm.tools.skill_writer_tool import SkillWriterTool

logger = get_logger(__name__)

class KnowledgeDistiller:
    """Distills successful agent reasoning into reusable skills."""

    def __init__(self, swarm_runtime: SwarmRuntime):
        self.runtime = swarm_runtime
        self.skill_writer = SkillWriterTool()

    def distill(self, run_id: str, skill_name: str) -> dict[str, Any]:
        """Extract reasoning from a successful run and save as a skill."""
        run = self.runtime._store.load_run(run_id)
        if not run or not run.final_report:
            return {"status": "error", "message": "Run report not available."}

        # Create skill content
        content = f"""---
name: {skill_name}
category: distillation
description: "Automatically distilled knowledge from run {run_id}"
---

{run.final_report}
"""

        # Save using the Swarm SkillWriterTool
        result = self.skill_writer.execute(
            skill_name=skill_name,
            content=content
        )

        logger.info(f"Knowledge distilled into skill {skill_name}")
        return {"status": "success", "detail": result}
