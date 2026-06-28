from pydantic import BaseModel

class TableInfoDTO(BaseModel):
    name: str
    rows: int
    memory_bytes: int

class MemoryStatsDTO(BaseModel):
    pool: str
    num_tables: int
    total_rows: int
    total_memory_bytes: int
    tables: list[TableInfoDTO]

class OptimizationResultDTO(BaseModel):
    success: bool
    table_name: str
    pool: str
    num_rows: int
    num_columns: int
    memory_usage_bytes: int
    error: str | None = None
