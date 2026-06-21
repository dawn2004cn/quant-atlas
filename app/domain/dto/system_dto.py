from pydantic import BaseModel
from typing import List, Optional

class TableInfoDTO(BaseModel):
    name: str
    rows: int
    memory_bytes: int

class MemoryStatsDTO(BaseModel):
    pool: str
    num_tables: int
    total_rows: int
    total_memory_bytes: int
    tables: List[TableInfoDTO]

class OptimizationResultDTO(BaseModel):
    success: bool
    table_name: str
    pool: str
    num_rows: int
    num_columns: int
    memory_usage_bytes: int
    error: Optional[str] = None
