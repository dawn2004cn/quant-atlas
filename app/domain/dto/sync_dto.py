from pydantic import BaseModel


class TdxSyncStatsDTO(BaseModel):
    codes_total: int
    codes_ok: int
    codes_skipped: int = 0
    codes_failed: int = 0
    mysql_rows: int
    csv_written: int
    date_min: str
    date_max: str
    timescale_rows: int = 0
    timescale_factor_rows: int = 0
    timescale_qfq_rows: int = 0
    timescale_hfq_rows: int = 0
