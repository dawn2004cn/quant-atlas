from __future__ import annotations
"""Architectural Compliance Agent: Guards system layer boundaries."""

import ast
import logging
from pathlib import Path
from typing import List


from app.core.logger import get_logger

logger = get_logger(__name__)

class ArchAuditAgent:
    """Agent that audits code for architectural violations."""

    # Define strict boundaries
    RULES = {
        "presentation_layer": {
            "forbidden": ["app.infrastructure"],
            "allowed": ["app.application.services", "app.domain"]
        }
    }

    def audit(self, path: Path) -> List[str]:
        """Audit a file for layer violations."""
        violations = []
        if not path.exists() or path.suffix != ".py":
            return violations

        tree = ast.parse(path.read_text(encoding="utf-8"))
        
        # Determine current layer from path
        layer = self._get_layer(path)
        if layer not in self.RULES:
            return violations

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if any(f.startswith(f) for f in self.RULES[layer]["forbidden"] for f in [module]):
                    violations.append(f"Layer violation: {layer} imports {module}")
        
        return violations

    def _get_layer(self, path: Path) -> str:
        if "presentation" in path.parts:
            return "presentation_layer"
        return "other"
