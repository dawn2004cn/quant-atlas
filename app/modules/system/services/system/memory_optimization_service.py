from __future__ import annotations

"""Memory optimization service for high-frequency data."""


from app.core.registry import register_service
from app.domain.dto.system_dto import MemoryStatsDTO, OptimizationResultDTO, TableInfoDTO
from app.modules.system.services.helpers.memory_access import get_shared_memory_manager


@register_service(name="memory_optimization_service")
class MemoryOptimizationService:
    """Service for memory optimization using Arrow."""

    def __init__(
        self,
        manager: object | None = None,
    ):
        self._manager = manager or get_shared_memory_manager()
        self._default_pool = self._manager.get_pool("default")

    def create_optimized_table(
        self,
        table_name: str,
        data: list[dict],
        pool_name: str | None = None,
    ) -> OptimizationResultDTO:
        """Create an optimized Arrow table."""
        if pool_name:
            pool = self._manager.get_pool(pool_name)
        else:
            pool = self._default_pool

        success = pool.create_table(table_name, data)

        if success:
            table = pool.get_table(table_name)
            try:
                import pyarrow as pa
                if isinstance(table, pa.Table):
                    num_rows = table.num_rows
                    num_cols = table.num_columns
                    memory_usage = table.nbytes
                else:
                    num_rows = len(data)
                    num_cols = len(data[0]) if data else 0
                    memory_usage = 0
            except ImportError:
                num_rows = len(data)
                num_cols = len(data[0]) if data else 0
                memory_usage = 0

            return OptimizationResultDTO(
                success=True,
                table_name=table_name,
                pool=pool_name or "default",
                num_rows=num_rows,
                num_columns=num_cols,
                memory_usage_bytes=memory_usage,
            )
        else:
            return OptimizationResultDTO(
                success=False,
                error="Failed to create table",
                table_name=table_name,
                pool=pool_name or "default",
                num_rows=0,
                num_columns=0,
                memory_usage_bytes=0,
            )

    def get_table(self, table_name: str, pool_name: str | None = None) -> list[dict] | None:
        """Get table as list of dicts."""
        if pool_name:
            pool = self._manager.get_pool(pool_name)
        else:
            pool = self._default_pool

        df = pool.get_as_pandas(table_name)
        if df is not None:
            return df.to_dict(orient="records")

        table = pool.get_table(table_name)
        if isinstance(table, list):
            return table

        return None

    def get_memory_stats(self, pool_name: str | None = None) -> MemoryStatsDTO:
        """Get memory statistics."""
        if pool_name:
            pool = self._manager.get_pool(pool_name)
        else:
            pool = self._default_pool

        tables = pool.list_tables()

        total_rows = 0
        total_memory = 0
        table_info = []

        for name in tables:
            table = pool.get_table(name)
            try:
                import pyarrow as pa
                if isinstance(table, pa.Table):
                    rows = table.num_rows
                    memory = table.nbytes
                else:
                    rows = len(table) if isinstance(table, list) else 0
                    memory = 0
            except ImportError:
                rows = len(table) if isinstance(table, list) else 0
                memory = 0

            total_rows += rows
            total_memory += memory
            table_info.append(TableInfoDTO(
                name=name,
                rows=rows,
                memory_bytes=memory,
            ))

        return MemoryStatsDTO(
            pool=pool_name or "default",
            num_tables=len(tables),
            total_rows=total_rows,
            total_memory_bytes=total_memory,
            tables=table_info,
        )

    def clear_pool(self, pool_name: str | None = None) -> None:
        """Clear memory pool."""
        if pool_name:
            pool = self._manager.get_pool(pool_name)
            pool.clear()
        else:
            self._default_pool.clear()

    def list_tables(self, pool_name: str | None = None) -> list[str]:
        """List table names in a memory pool."""
        if pool_name:
            pool = self._manager.get_pool(pool_name)
        else:
            pool = self._default_pool
        return pool.list_tables()

    def serialize_table(self, table_name: str, pool_name: str | None = None) -> bytes | None:
        """Serialize table to bytes for IPC."""
        if pool_name:
            pool = self._manager.get_pool(pool_name)
        else:
            pool = self._default_pool

        return pool.to_bytes(table_name)

    def deserialize_table(self, table_name: str, data: bytes, pool_name: str | None = None) -> bool:
        """Deserialize table from bytes."""
        if pool_name:
            pool = self._manager.get_pool(pool_name)
        else:
            pool = self._default_pool

        return pool.from_bytes(table_name, data)
