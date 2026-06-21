"""Dynamic Pipeline Builder."""

import importlib
from typing import List
from app.infrastructure.pipeline.base import Pipeline, DataProcessor
from app.infrastructure.config_loader.loader import DynamicConfigLoader
from pathlib import Path

class PipelineFactory:
    """Creates a pipeline instance based on dynamic config."""
    
    @staticmethod
    def create_from_config(config_name: str) -> Pipeline:
        loader = DynamicConfigLoader()
        config = loader.get_config(config_name)
        processor_paths = config.get("ingestion_pipeline", [])
        
        processors: List[DataProcessor] = []
        for path in processor_paths:
            module_name, class_name = path.rsplit(".", 1)
            module = importlib.import_module(module_name)
            cls = getattr(module, class_name)
            processors.append(cls())
            
        return Pipeline(processors)
