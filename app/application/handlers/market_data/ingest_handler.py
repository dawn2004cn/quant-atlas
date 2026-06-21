from __future__ import annotations
"""Handler for market data ingestion commands."""


from typing import Any, Optional
from app.application.commands.market_data.ingest import IngestMarketDataCommand
from app.modules.system.services.helpers.config_loader_access import get_config_loader_port
from app.modules.system.services.helpers.longhu_mapping_access import get_longhu_mapping_port
from app.modules.system.services.helpers.market_data_ingestor_access import create_longhu_ingestor
from app.domain.ports.market_data_ports import IMarketDataIngestor
from app.domain.ports.repository_ports import IBasicMarketDataRepository
from app.core.logger import get_logger

logger = get_logger(__name__)


class IConfigLoader:
    """Interface for config loading."""
    
    def get_config(self, key: str) -> dict[str, Any]:
        pass


class MarketDataIngestionHandler:
    """Handles the ingestion of market data."""
    
    def __init__(
        self,
        repository: Optional[IBasicMarketDataRepository] = None,
        longhu_adapter: Optional[IMarketDataIngestor] = None,
        config_loader: Optional[IConfigLoader] = None,
    ):
        self._repo = repository
        self._adapter = longhu_adapter
        self._config_loader = config_loader
    
    @property
    def repo(self):
        if self._repo is None:
            from app.modules.system.services.helpers.service_resolver_access import resolve_optional_service
            self._repo = resolve_optional_service(IBasicMarketDataRepository)
        return self._repo
    
    @property
    def adapter(self):
        if self._adapter is None:
            from app.modules.system.services.helpers.service_resolver_access import resolve_optional_service
            self._adapter = resolve_optional_service(IMarketDataIngestor)
        if self._adapter is None:
            self._adapter = create_longhu_ingestor()
        return self._adapter
    
    @property
    def config_loader(self):
        if self._config_loader is None:
            from app.modules.system.services.helpers.service_resolver_access import resolve_optional_service
            self._config_loader = resolve_optional_service(IConfigLoader)
        if self._config_loader is None:
            self._config_loader = get_config_loader_port()
        return self._config_loader

    def handle(self, command: IngestMarketDataCommand) -> dict:
        """Process the ingestion command."""
        rules = self.config_loader.get_config("ingestion_rules")
        max_rows = rules.get("max_rows", 5000)
        
        start_s = command.start_date.strftime("%Y%m%d")
        end_s = command.end_date.strftime("%Y%m%d")
        
        df = self.adapter.fetch_data(start_s, end_s)
        if df is None or df.empty:
            return {"ok": False, "error": "fetch_failed_or_empty"}
        
        entries = get_longhu_mapping_port().map_dataframe_to_entries(df)
        
        n = self.repo.upsert_longhu_rows([e.model_dump() for e in entries])
        
        from app.domain.events.bus import bus
        from app.domain.events.market_events import MarketDataIngestedEvent
        bus.publish(MarketDataIngestedEvent(
            symbol="ALL", 
            data_type="longhu", 
            count=n
        ))
        
        return {"ok": True, "rows": n}


__all__ = ["MarketDataIngestionHandler", "IConfigLoader"]