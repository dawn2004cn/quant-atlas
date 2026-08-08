from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Application service for QuantML factor management."""


import logging
import os
import re
from pathlib import Path
from typing import Any

from app.domain.ports import QuantMLFactorRepository
from app.domain.quantml_entities import QuantMLFactor
from app.config import BASE_DIR
from app.core.logger import get_logger

logger = get_logger(__name__)


class QuantMLFactorService:
    def __init__(self, repository: QuantMLFactorRepository):
        self._repository = repository
        self._quantml_root = Path(BASE_DIR) / "QuantML" / "factor_zoo"

    def sync_all_factors(self) -> GenericResponseDTO[str, int]:
        """Parse all .md files in factor_zoo and sync to MySQL."""
        if not self._quantml_root.is_dir():
            logger.error(f"QuantML factor_zoo not found at {self._quantml_root}")
            return {"synced": 0, "error": 1}

        self._repository.clear_all()
        total_synced = 0
        
        md_files = {
            "amplitude": "runs_amplitude.md",
            "std": "runs_std.md",
            "higher_moment": "runs_higher_moment.md",
            "turnover": "runs_turnover.md",
            "liquidity": "runs_liquidity.md",
            "corr": "runs_corr.md",
            "idx": "runs_idx.md",
            "mom": "runs_mom.md",
            "all": "runs.md"
        }

        for category, filename in md_files.items():
            path = self._quantml_root / filename
            if not path.is_file():
                continue
            
            count = self._sync_file(path, category)
            total_synced += count
            logger.info(f"Synced {count} factors from {filename} (category: {category})")

        return {"synced": total_synced, "files_processed": len(md_files)}

    def _sync_file(self, path: Path, category: str) -> int:
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read {path}: {e}")
            return 0

        lines = content.splitlines()
        synced_in_file = 0
        
        # Simple Markdown table parser
        for line in lines:
            if not line.strip().startswith("|") or "factor_name" in line or "---" in line:
                continue
            
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 10:
                continue
            
            # parts[0] is empty because line starts with |
            try:
                factor = QuantMLFactor(
                    factor_name=parts[1],
                    category=category,
                    ic_mean=self._safe_float(parts[2]),
                    icir=self._safe_float(parts[3]),
                    long_average=self._safe_float(parts[4]),
                    long_short=self._safe_float(parts[5]),
                    t_stat=self._safe_float(parts[8]),
                    metadata={
                        "signic0": parts[6],
                        "signic004": parts[7],
                        "groups": parts[9:-1]
                    }
                )
                self._repository.save_factor(factor)
                synced_in_file += 1
            except (ValueError, IndexError):
                continue
                
        return synced_in_file

    def _safe_float(self, val: str) -> float | None:
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    def list_factors(self, category: str | None = None, limit: int = 100) -> list[QuantMLFactor]:
        return self._repository.list_factors(category, limit)
