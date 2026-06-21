from __future__ import annotations


from app.domain.dto.service_result import GenericResponseDTO

"""Hot sector MySQL storage and querying (Eastmoney + Tonghuashun gain ranking snapshots)."""


from dataclasses import dataclass

from datetime import datetime, timezone

from typing import Any, Literal



from app.application.errors import ValidationError

from app.modules.market_data.services.hot_sector_service import get_hot_sector_service

from app.config import AppSettings, get_settings

from app.core.logger import get_logger

from app.core.runtime_config import get_runtime_int

from app.domain.ports.hot_sector_storage_port import HotSectorStoragePort



logger = get_logger(__name__)



SourceMode = Literal["auto", "live", "mysql"]




def _now_snapshot_at() -> str:

    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")




def _today_trade_date() -> str:

    return datetime.now(timezone.utc).strftime("%Y-%m-%d")




@dataclass(frozen=True)

class HotSectorIngestResult:

    ok: bool

    snapshot_at: str

    trade_date: str

    sector_count: int

    member_rows: int

    ingest_kind: str



    def to_dict(self) -> GenericResponseDTO:

        return {

            "ok": self.ok,

            "snapshot_at": self.snapshot_at,

            "trade_date": self.trade_date,

            "sector_count": self.sector_count,

            "member_rows": self.member_rows,

            "ingest_kind": self.ingest_kind,

        }




class HotSectorStorageService:

    """Write hot sector rankings and optional constituent stocks to MySQL, supporting snapshot-based querying."""



    def __init__(

        self,

        *,

        settings: AppSettings | None = None,

        repository: HotSectorStoragePort | None = None,

    ) -> None:

        self._settings = settings or get_settings()

        self._repo = repository



    def _require_mysql(self):

        if not self._settings.use_mysql or self._settings.mysql is None:

            raise ValidationError("mysql_not_enabled")

        return self._settings.mysql



    def _require_repo(self) -> HotSectorStoragePort:

        self._require_mysql()

        if self._repo is None:

            raise ValidationError("hot_sector_repository_unavailable")

        return self._repo



    def _fetch_sectors_for_ingest(self, *, limit: int, kind: str) -> list[dict[str, Any]]:

        rows, _warnings = _load_live_sectors(limit=limit, kind=kind)

        return rows



    def ingest_snapshot(

        self,

        *,

        limit: int = 80,

        kind: str = "all",

        ingest_members: bool = True,

        top_sectors_for_members: int = 25,

        members_limit: int = 80,

    ) -> HotSectorIngestResult:

        """Fetch Eastmoney/Tonghuashun rankings and write to MySQL (one batch snapshot)."""

        return self._ingest_sectors(

            sectors=self._fetch_sectors_for_ingest(limit=limit, kind=kind),

            ingest_kind=(kind or "all").strip().lower(),

            snapshot_source="multi",

            ingest_members=ingest_members,

            top_sectors_for_members=top_sectors_for_members,

            members_limit=members_limit,

        )



    def ingest_ths_snapshot(

        self,

        *,

        limit_per_kind: int = 60,

        ingest_members: bool = True,

        top_sectors_for_members: int = 30,

        members_limit: int = 80,

    ) -> HotSectorIngestResult:

        """Fetch only Tonghuashun four board types (concept/region/industry/CSRC) and ingest constituent stocks."""

        svc = get_hot_sector_service()

        sectors = svc.get_ths_all_boards(limit_per_kind=limit_per_kind)

        if not sectors:

            raise ValidationError("hot_sector_ths_fetch_empty")

        return self._ingest_sectors(

            sectors=sectors,

            ingest_kind="ths",

            snapshot_source="tonghuashun",

            ingest_members=ingest_members,

            top_sectors_for_members=top_sectors_for_members,

            members_limit=members_limit,

            members_provider="ths",

        )



    def _ingest_sectors(

        self,

        *,

        sectors: list[dict[str, Any]],

        ingest_kind: str,

        snapshot_source: str,

        ingest_members: bool,

        top_sectors_for_members: int,

        members_limit: int,

        members_provider: str | None = None,

    ) -> HotSectorIngestResult:

        repo = self._require_repo()

        if not sectors:

            raise ValidationError("hot_sector_fetch_empty")



        snapshot_at = _now_snapshot_at()

        trade_date = _today_trade_date()

        svc = get_hot_sector_service()

        prov = (members_provider or "").strip().lower() or None



        sector_params: list[tuple[Any, ...]] = []

        for idx, row in enumerate(sectors, start=1):

            sector_params.append(

                (

                    snapshot_at,

                    str(row.get("sector_code") or "").upper(),

                    str(row.get("name") or ""),

                    str(row.get("kind") or "concept"),

                    str(row.get("source") or "eastmoney"),

                    float(row.get("change_pct") or 0),

                    float(row.get("price") or 0),

                    float(row.get("amount") or 0),

                    float(row.get("volume") or 0),

                    float(row.get("turnover_rate") or 0),

                    idx,

                )

            )



        member_params: list[tuple[Any, ...]] = []

        if ingest_members and top_sectors_for_members > 0:

            for row in sectors[:top_sectors_for_members]:

                code = str(row.get("sector_code") or "").upper()

                if not code:

                    continue

                board_kind = str(row.get("kind") or "concept")

                members = svc.get_sector_members(

                    code,

                    limit=members_limit,

                    kind=board_kind,  # type: ignore[arg-type]

                    sector_name=str(row.get("name") or ""),

                    provider=prov or str(row.get("provider") or "") or None,

                )

                for m in members:

                    member_params.append(

                        (

                            snapshot_at,

                            code,

                            str(m.get("symbol") or ""),

                            str(m.get("name") or ""),

                            float(m.get("change_pct") or 0),

                            float(m.get("price") or 0),

                            float(m.get("amount") or 0),

                            float(m.get("volume") or 0),

                        )

                    )



        retention_days = max(1, get_runtime_int("HOT_SECTOR_SNAPSHOT_RETENTION_DAYS", 30))

        try:

            repo.save_ingest_batch(

                snapshot_at=snapshot_at,

                trade_date=trade_date,

                ingest_kind=ingest_kind,

                snapshot_source=snapshot_source,

                sector_params=sector_params,

                member_params=member_params,

                retention_days=retention_days,

            )

        except Exception:

            logger.exception("hot sector ingest failed")

            raise



        member_rows = len(member_params)

        logger.info(

            "hot sector ingested snapshot_at=%s sectors=%s members=%s",

            snapshot_at,

            len(sectors),

            member_rows,

        )

        return HotSectorIngestResult(

            ok=True,

            snapshot_at=snapshot_at,

            trade_date=trade_date,

            sector_count=len(sectors),

            member_rows=member_rows,

            ingest_kind=ingest_kind,

        )



    def list_snapshots(self, *, limit: int = 30) -> list[dict[str, Any]]:

        return self._require_repo().list_snapshots(limit=limit)



    def latest_snapshot_at(self) -> str | None:

        return self._require_repo().latest_snapshot_at()



    def list_sectors_from_mysql(

        self,

        *,

        snapshot_at: str | None,

        kind: str,

        limit: int,

    ) -> tuple[list[dict[str, Any]], str | None]:

        repo = self._require_repo()

        snap = snapshot_at or repo.latest_snapshot_at()

        if not snap:

            return [], None

        rows = repo.list_sectors(snapshot_at=snap, kind=kind, limit=limit)

        return rows, snap



    def list_members_from_mysql(

        self,

        sector_code: str,

        *,

        snapshot_at: str | None,

        limit: int,

    ) -> tuple[list[dict[str, Any]], str | None]:

        repo = self._require_repo()

        code = (sector_code or "").strip().upper()

        snap = snapshot_at or repo.latest_snapshot_at()

        if not code or not snap:

            return [], snap

        rows = repo.list_members(sector_code=code, snapshot_at=snap, limit=limit)

        return rows, snap



    @staticmethod

    def _attach_sector_freshness(payload: dict[str, Any]) -> dict[str, Any]:

        from app.modules.system.services.ui.data_freshness_service import enrich_market_payload



        mode = str(payload.get("source_mode") or "unknown")

        snap = str(payload.get("snapshot_at") or "")

        enriched = enrich_market_payload(

            {"snapshot_at": snap, "updated_at": snap},

            source=f"hot_sectors:{mode}",

        )

        out = dict(payload)

        out["data_timestamp"] = enriched.get("data_timestamp")

        out["is_realtime"] = enriched.get("is_realtime")

        out["freshness"] = enriched.get("freshness")

        return out



    def resolve_sectors(

        self,

        *,

        limit: int,

        kind: str,

        source: SourceMode = "auto",

        snapshot_at: str | None = None,

    ) -> GenericResponseDTO:

        """auto: use MySQL if latest snapshot exists, otherwise fetch live."""

        mode = (source or "auto").strip().lower()

        if mode not in ("auto", "live", "mysql"):

            mode = "auto"



        if mode in ("auto", "mysql") and self._settings.use_mysql and self._repo is not None:

            try:

                rows, snap = self.list_sectors_from_mysql(

                    snapshot_at=snapshot_at if mode == "mysql" else None,

                    kind=kind,

                    limit=limit,

                )

                if rows:

                    return self._attach_sector_freshness(

                        {

                            "sectors": rows,

                            "count": len(rows),

                            "snapshot_at": snap,

                            "source_mode": "mysql",

                        }

                    )

            except ValidationError:

                if mode == "mysql":

                    raise

            except Exception as exc:

                logger.warning("hot sector mysql read failed: %s", exc)

                if mode == "mysql":

                    raise ValidationError("hot_sector_mysql_read_failed") from exc



        from datetime import datetime as dt



        live, warnings = _load_live_sectors(limit=limit, kind=kind)

        return self._attach_sector_freshness(

            {

                "sectors": live,

                "count": len(live),

                "snapshot_at": dt.now().isoformat(timespec="seconds"),

                "source_mode": "live",

                "warnings": warnings,

            }

        )



    def resolve_members(

        self,

        sector_code: str,

        *,

        limit: int,

        source: SourceMode = "auto",

        snapshot_at: str | None = None,

        board_kind: str = "concept",

        sector_name: str | None = None,

        provider: str | None = None,

    ) -> tuple[list[dict[str, Any]], str]:

        mode = (source or "auto").strip().lower()

        if mode in ("auto", "mysql") and self._settings.use_mysql and self._repo is not None:

            try:

                rows, snap = self.list_members_from_mysql(

                    sector_code,

                    snapshot_at=snapshot_at if mode == "mysql" else None,

                    limit=limit,

                )

                if rows:

                    return rows, "mysql"

            except ValidationError:

                if mode == "mysql":

                    raise

            except Exception as exc:

                logger.warning("hot sector members mysql read failed: %s", exc)

                if mode == "mysql":

                    raise ValidationError("hot_sector_members_mysql_read_failed") from exc



        svc = get_hot_sector_service()

        bk = (board_kind or "concept").strip().lower()

        if bk not in ("concept", "industry", "region", "csrc"):

            bk = "concept"

        rows = svc.get_sector_members(

            sector_code,

            limit=limit,

            kind=bk,  # type: ignore[arg-type]

            sector_name=sector_name,

            provider=provider,

        )

        return rows, "live"




def _load_live_sectors(*, limit: int, kind: str) -> tuple[list[dict[str, Any]], list[str]]:

    """Fetch sector list live; returns (rows, warnings)."""

    svc = get_hot_sector_service()

    k = (kind or "all").strip().lower()

    budget = float(get_runtime_int("HOT_SECTOR_LIVE_BUDGET_SEC", 22))

    warnings: list[str] = []



    def _sort_cap(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:

        rows.sort(key=lambda x: float(x.get("change_pct") or 0), reverse=True)

        return rows[:limit]



    if k == "em":

        return _sort_cap(svc.get_hot_sectors(limit=limit, vendor="em", budget_sec=budget)), warnings

    if k == "ths":

        per = max(20, min(limit, 80))

        rows = svc.get_ths_all_boards(limit_per_kind=per)

        if not rows:

            warnings.append("ths: empty (network or anti-bot)")

        return _sort_cap(rows), warnings

    if k == "csrc":

        rows = svc.get_ths_csrc_industries(limit=limit)

        if not rows:

            warnings.append("csrc: empty (403/401 common off-hours)")

        return _sort_cap(rows), warnings

    if k == "kpl":

        rows, w = svc._run_fetch_tasks(

            [("kpl", lambda: (

                svc.get_kpl_concepts(limit=limit)

                + svc.get_kpl_regions(limit=limit)

                + svc.get_kpl_industries(limit=limit)

            ))],

            budget_sec=budget,

        )

        warnings.extend(w)

        return _sort_cap(rows), warnings

    if k == "xgt":

        return _sort_cap(svc.get_xgt_concepts(limit=limit)), warnings

    if k == "region":

        rows, w = svc._run_fetch_tasks(

            [

                ("ths_region", lambda: svc.get_ths_regions(limit=limit)),

                ("kpl_region", lambda: svc.get_kpl_regions(limit=limit)),

            ],

            budget_sec=budget,

        )

        warnings.extend(w)

        if not rows:

            warnings.append("region: no data from THS/KPL")

        return _sort_cap(rows), warnings

    if k == "concept":

        rows, w = svc._run_fetch_tasks(

            [

                ("em_concepts", lambda: svc.get_em_concepts(limit=limit)),

                ("ths_concepts", lambda: svc.get_ths_concepts(limit=limit)),

                ("kpl_concepts", lambda: svc.get_kpl_concepts(limit=limit)),

                ("xgt_concepts", lambda: svc.get_xgt_concepts(limit=limit)),

            ],

            budget_sec=budget,

        )

        warnings.extend(w)

        return _sort_cap(rows), warnings

    if k == "industry":

        rows, w = svc._run_fetch_tasks(

            [

                ("em_industries", lambda: svc.get_em_industries(limit=limit)),

                ("ths_industries", lambda: svc.get_ths_industries(limit=limit)),

                ("ths_csrc", lambda: svc.get_ths_csrc_industries(limit=limit)),

                ("kpl_industries", lambda: svc.get_kpl_industries(limit=limit)),

            ],

            budget_sec=budget,

        )

        warnings.extend(w)

        return _sort_cap(rows), warnings



    rows = svc.get_hot_sectors(limit=limit, vendor="all", budget_sec=budget)

    if not rows:

        warnings.append("all: no vendor returned data; try source=live&kind=em or ingest mysql")

    return rows, warnings
