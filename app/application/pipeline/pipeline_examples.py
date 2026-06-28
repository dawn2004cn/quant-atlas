"""Example pipeline for market data processing."""

from app.application.pipeline import (
    PipelineBuilder,
    DataQualityGate,
    PipelineResult,
)
from app.core.logger import get_logger

logger = get_logger(__name__)


class MarketDataPipeline:
    """Market data processing pipeline."""

    def __init__(self):
        self._pipeline = None

    def build_pipeline(self):
        """Build the market data pipeline."""

        def read_market_data():
            """Mock market data reader."""
            return [
                {"code": "600519", "price": 1800.0, "volume": 1000000, "change_pct": 0.5},
                {"code": "000001", "price": 12.5, "volume": 50000000, "change_pct": -0.3},
                {"code": "600036", "price": 35.0, "volume": 20000000, "change_pct": 1.2},
                {"code": "INVALID", "price": -10.0, "volume": 0, "change_pct": 0},
            ]

        def write_to_cache(records):
            """Mock write to cache."""
            logger.info(f"Writing {len(records)} records to cache")
            return True

        validators = [
            lambda r: DataQualityGate.check_required_fields(r, ["code", "price", "volume"]),
            lambda r: DataQualityGate.check_value_range(r, "price", 0.01, 100000),
            lambda r: DataQualityGate.check_value_range(r, "volume", 0, 10000000000),
        ]

        transformers = [
            lambda r: {**r, "price": round(r.get("price", 0), 2)},
            lambda r: {**r, "change_pct": round(r.get("change_pct", 0), 2)},
            lambda r: {**r, "processed_at": "now"},
        ]

        self._pipeline = (
            PipelineBuilder("market_data")
            .with_reader("mock_source", read_market_data)
            .with_validator(validators)
            .with_transformer(transformers)
            .with_writer("cache", write_to_cache)
            .build()
        )

    def execute(self) -> PipelineResult:
        """Execute the pipeline."""
        if not self._pipeline:
            self.build_pipeline()
        return self._pipeline.execute()


class StockDataPipeline:
    """Stock data processing pipeline."""

    def __init__(self):
        self._pipeline = None

    def build_for_analysis(self):
        """Build pipeline for stock analysis."""

        def read_stocks():
            return [
                {"code": "600519", "name": "贵州茅台", "industry": "白酒"},
                {"code": "000001", "name": "平安银行", "industry": "银行"},
            ]

        def validate_stock(record):
            return DataQualityGate.check_required_fields(
                record, ["code", "name"]
            ) and DataQualityGate.check_enum(
                record, "industry", ["白酒", "银行", "房地产", "科技"]
            )

        def transform_stock(record):
            return {
                **record,
                "code_normalized": record["code"],
                "analysis_ready": True,
            }

        self._pipeline = (
            PipelineBuilder("stock_analysis")
            .with_reader("stock_db", read_stocks)
            .with_validator([validate_stock])
            .with_transformer([transform_stock])
            .build()
        )


def run_market_data_pipeline():
    """Run market data pipeline example."""
    logger.info("Starting market data pipeline")

    pipeline = MarketDataPipeline()
    result = pipeline.execute()

    logger.info(f"Pipeline completed: {result.success}")
    logger.info(f"Processed: {result.processed_count} records")
    logger.info(f"Errors: {len(result.errors)}")
    logger.info(f"Warnings: {len(result.warnings)}")

    return result


__all__ = ["MarketDataPipeline", "StockDataPipeline", "run_market_data_pipeline"]
