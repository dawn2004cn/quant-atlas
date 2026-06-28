from __future__ import annotations

"""Pipeline DSL compiler for automated quant research."""

from typing import Any

import yaml

from app.application.factor.miner import FactorMiner
from app.application.factor.registry import factor_registry
from app.core.logger import get_logger

logger = get_logger(__name__)

class PipelineCompiler:
    """Compiles DSL YAML into executable factor mining tasks."""

    def __init__(self, registry=factor_registry):
        self._registry = registry
        self._miner = FactorMiner(registry=registry)

    def compile_and_run(self, config_path: str, data: Any, target: Any) -> dict[str, Any]:
        """Load YAML, compile tasks, and execute mining."""
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        pipeline_name = config.get("name", "unnamed_pipeline")
        steps = config.get("steps", [])

        logger.info(f"Executing pipeline: {pipeline_name}")

        # Prepare factor list from steps
        factors = [
            {"name": step["factor"], "params": step.get("params", {})}
            for step in steps
        ]

        # Run mining
        results = self._miner.mine(data, target, factors)

        return {
            "pipeline": pipeline_name,
            "results": results
        }
