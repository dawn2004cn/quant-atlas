from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Qlib 运行时封装：安全 init、数据状态、官方回测、平台策略信号对齐。"""


import copy
import json
import threading
from pathlib import Path
from typing import Any

import pandas as pd

from app.config import BASE_DIR
from app.core.logger import get_logger

logger = get_logger(__name__)

_INIT_LOCK = threading.Lock()


def _qlib_available() -> bool:
    try:
        import qlib  # noqa: F401, PLC0415
    except ImportError:
        return False
    return True


def _load_yaml_mapping(path: Path) -> GenericResponseDTO:
    if not path.is_file():
        raise FileNotFoundError(f"config yaml not found: {path}")
    text = path.read_text(encoding="utf-8")
    try:
        from ruamel.yaml import YAML  # type: ignore[import-untyped]

        y = YAML(typ="safe", pure=True)
        data = y.load(text)
    except ImportError:
        import yaml  # type: ignore[import-untyped]

        data = yaml.safe_load(text)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError("qlib config yaml root must be a mapping")
    return data


def _records_to_qlib_pred(
    records: list[dict[str, Any]],
    *,
    default_instrument: str,
    score_key: str = "score",
) -> pd.Series:
    """构建 Qlib ``TopkDropoutStrategy`` 可用的 MultiIndex (instrument, datetime) score。"""
    rows: list[tuple[str, pd.Timestamp, float]] = []
    for r in records:
        inst = str(r.get("instrument") or r.get("symbol") or default_instrument).strip().upper()
        ds = r.get("date") or r.get("Date")
        if ds is None:
            continue
        dt = pd.Timestamp(ds)
        if score_key in r:
            sc = float(r[score_key])
        else:
            sig = int(r.get("Signal", r.get("signal", 0)))
            sc = 1.0 if sig > 0 else (-1.0 if sig < 0 else 0.0)
        rows.append((inst, dt, sc))
    if not rows:
        raise ValueError("no valid signal rows")
    idx = pd.MultiIndex.from_tuples([(a, b) for a, b, _ in rows], names=["instrument", "datetime"])
    s = pd.Series([c for _, _, c in rows], index=idx).sort_index()
    return s


class QlibService:
    """与 ``instance/qlib_bin``、``config/qlib_config.yaml`` 及可选 ``config/qlib_config.local.yaml`` / 旧版 ``instance/qlib_config.yaml`` 协同。"""

    @staticmethod
    def platform_signal_rows_from_dataframe(df: pd.DataFrame, *, instrument: str = "SH600519") -> list[dict[str, Any]]:
        """将 ``BaseTradingStrategy.generate_signals`` 产出的 DataFrame 转为 ``integrate_existing_strategy`` 的 records。"""
        if df is None or df.empty:
            return []
        col_date = "Date" if "Date" in df.columns else "date"
        col_sig = "Signal" if "Signal" in df.columns else "signal"
        if col_date not in df.columns or col_sig not in df.columns:
            raise ValueError("DataFrame 需包含 Date/date 与 Signal/signal 列")
        inst = instrument.strip().upper()
        rows: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            d = row[col_date]
            ds = d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)[:10]
            rows.append({"date": ds, "Signal": int(row[col_sig]), "instrument": inst})
        return rows

    def __init__(self, engine: IBacktestEngine, base_dir: Path | None = None) -> None:
        self.engine = engine
        self._base = Path(base_dir or BASE_DIR)
        self.qlib_bin_dir = (self._base / "instance" / "qlib_bin").resolve()
        self._last_init: dict[str, Any] = {}
        self._quant_atlas_profile: dict[str, Any] = {}

    def execute_strategy(self, strategy_config: Dict[str, Any]) -> GenericResponseDTO:
        """Execute a strategy using the injected engine."""
        return self.engine.run(strategy_config)

    def default_config_path(self) -> Path:
        """顺序：``config/qlib_config.yaml`` → ``config/qlib_config.local.yaml`` → 旧路径 ``instance/qlib_config.yaml``。"""
        primary = (self._base / "config" / "qlib_config.yaml").resolve()
        if primary.is_file():
            return primary
        local = (self._base / "config" / "qlib_config.local.yaml").resolve()
        if local.is_file():
            return local
        legacy = (self._base / "instance" / "qlib_config.yaml").resolve()
        if legacy.is_file():
            return legacy
        return primary

    def get_quant_atlas_profile(self) -> GenericResponseDTO:
        """YAML 中 ``quant_atlas`` 块（不传入 qlib.init），如 benchmark、market 说明。"""
        return dict(self._quant_atlas_profile)

    def init_qlib(
        self,
        config_path: str | Path | None = None,
        *,
        provider_uri: str | Path | None = None,
        region: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> GenericResponseDTO:
        """初始化 qlib；可传官方风格 ``config.yaml``，或由参数覆盖 ``provider_uri`` / ``region``。

        - 未传 ``config_path`` 时按 ``config/qlib_config.yaml`` → ``config/qlib_config.local.yaml`` → ``instance/qlib_config.yaml`` 查找。
        - YAML 根下的 ``quant_atlas`` 仅保留在应用层，不会传入 ``qlib.init``（避免与 pyqlib 参数冲突）。
        - 多次调用会使用 qlib 内部 ``C.set`` 重置配置（线程内串行）。
        """
        if not _qlib_available():
            return {"ok": False, "error": "import_error", "message": "未安装 pyqlib，请安装 requirements-qlib.txt"}

        import qlib
        from qlib.constant import REG_CN

        cfg_path = Path(config_path).expanduser() if config_path else self.default_config_path()
        merged: dict[str, Any] = {}
        if cfg_path.is_file():
            try:
                merged.update(_load_yaml_mapping(cfg_path))
                logger.info("qlib init: loaded yaml %s", cfg_path)
            except Exception as exc:  # noqa: BLE001
                logger.exception("qlib init: yaml load failed")
                return {"ok": False, "error": "yaml_error", "message": str(exc)}
        raw_atlas = merged.pop("quant_atlas", None)
        self._quant_atlas_profile = dict(raw_atlas) if isinstance(raw_atlas, dict) else {}
        if extra:
            merged.update(extra)
        if provider_uri is not None:
            merged["provider_uri"] = str(Path(provider_uri).expanduser().resolve())
        elif "provider_uri" not in merged:
            merged["provider_uri"] = str(self.qlib_bin_dir)
        else:
            pu = merged.get("provider_uri")
            if isinstance(pu, str) and pu.strip():
                pth = Path(pu.strip()).expanduser()
                if not pth.is_absolute():
                    pth = (self._base / pth).resolve()
                merged["provider_uri"] = str(pth)
        if region is not None:
            merged["region"] = region
        elif "region" not in merged:
            merged["region"] = REG_CN

        default_conf = str(merged.pop("default_conf", "client"))

        with _INIT_LOCK:
            try:
                qlib.init(default_conf, **merged)
            except Exception as exc:  # noqa: BLE001
                logger.exception("qlib.init failed")
                return {"ok": False, "error": "init_failed", "message": str(exc)}

        snap = {
            "ok": True,
            "provider_uri": merged.get("provider_uri"),
            "region": str(merged.get("region")),
            "config_path": str(cfg_path) if cfg_path.is_file() else "",
            "quant_atlas": dict(self._quant_atlas_profile),
        }
        self._last_init = snap
        logger.info("qlib init ok provider_uri=%s", snap.get("provider_uri"))
        return snap

    def get_data_status(self, *, market: str | None = None) -> GenericResponseDTO:
        """不强制已 init：从磁盘读取日历与标的表；若已 init 则附带 qlib 注册状态。"""
        cal = self.qlib_bin_dir / "calendars" / "day.txt"
        inst = self.qlib_bin_dir / "instruments" / "all.txt"
        last_trade = ""
        n_instruments = 0
        try:
            if cal.is_file():
                lines = [ln.strip() for ln in cal.read_text(encoding="utf-8").splitlines() if ln.strip()]
                last_trade = lines[-1] if lines else ""
        except OSError as exc:
            logger.warning("read calendar failed: %s", exc)
        try:
            if inst.is_file():
                n_instruments = sum(1 for ln in inst.read_text(encoding="utf-8").splitlines() if ln.strip())
        except OSError as exc:
            logger.warning("read instruments failed: %s", exc)

        mkt = (market or "CN").upper()
        registered = False
        if _qlib_available():
            from qlib.config import C

            registered = bool(C.registered)

        return {
            "market": mkt,
            "last_trading_day": last_trade,
            "instrument_count": n_instruments,
            "qlib_bin_dir": str(self.qlib_bin_dir),
            "calendar_exists": cal.is_file(),
            "instruments_exists": inst.is_file(),
            "qlib_registered": registered,
        }

    def run_qlib_backtest(self, strategy_config: dict[str, Any]) -> GenericResponseDTO:
        """调用 ``qlib.contrib.evaluate.backtest_daily``。

        ``strategy_config`` 字段：

        - ``start_time``, ``end_time`` (必填)
        - ``account`` (初始资金), ``benchmark``
        - ``strategy``: 传给 ``qlib.utils.init_instance_by_config`` 的类配置；若含 ``signal_records`` 则先转为 pred 再注入 ``kwargs.signal``
        - ``exchange_kwargs``, ``executor`` 可选，透传
        """
        if not _qlib_available():
            return {"ok": False, "error": "import_error", "message": "未安装 pyqlib"}

        init_res = self.init_qlib()
        if not init_res.get("ok"):
            return {"ok": False, "error": "init_failed", "message": init_res.get("message", "")}

        from qlib.contrib.evaluate import backtest_daily, risk_analysis
        from qlib.utils import init_instance_by_config

        cfg = copy.deepcopy(strategy_config)
        start = cfg.get("start_time") or cfg.get("start")
        end = cfg.get("end_time") or cfg.get("end")
        if not start or not end:
            return {"ok": False, "error": "validation", "message": "start_time/end_time 必填"}

        account = float(cfg.get("account", cfg.get("initial_capital", 1_000_000)))
        benchmark = str(cfg.get("benchmark", "SH000300"))
        exchange_kwargs = cfg.get("exchange_kwargs")
        executor = cfg.get("executor")

        strat_cfg = cfg.get("strategy")
        if strat_cfg is None:
            return {"ok": False, "error": "validation", "message": "strategy 配置缺失"}

        strat_cfg = copy.deepcopy(strat_cfg)
        if not isinstance(strat_cfg, dict):
            return {"ok": False, "error": "validation", "message": "strategy 必须为对象"}

        default_inst = str(cfg.get("default_instrument", "SH600519")).upper()
        sig_records = strat_cfg.pop("signal_records", None)
        strat_cfg.pop("default_instrument", None)
        if sig_records is not None:
            if not isinstance(sig_records, list):
                return {"ok": False, "error": "validation", "message": "signal_records 须为数组"}
            kwargs = strat_cfg.setdefault("kwargs", {})
            try:
                kwargs["signal"] = _records_to_qlib_pred(sig_records, default_instrument=default_inst)
            except Exception as exc:  # noqa: BLE001
                logger.exception("signal_records 转换失败")
                return {"ok": False, "error": "signal_error", "message": str(exc)}

        try:
            strategy = init_instance_by_config(strat_cfg)
        except Exception as exc:  # noqa: BLE001
            logger.exception("init_instance_by_config(strategy) 失败")
            return {"ok": False, "error": "strategy_build", "message": str(exc)}

        try:
            report_normal, positions_normal = backtest_daily(
                start_time=str(start),
                end_time=str(end),
                strategy=strategy,
                account=account,
                benchmark=benchmark,
                exchange_kwargs=exchange_kwargs,
                executor=executor,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("backtest_daily 失败")
            return {"ok": False, "error": "backtest_failed", "message": str(exc)}

        curve: list[dict[str, Any]] = []
        metrics: dict[str, Any] = {}
        try:
            if report_normal is not None and not report_normal.empty:
                if "account" in report_normal.columns:
                    acct = report_normal["account"]
                    idx = acct.index
                    for i, v in enumerate(acct.values):
                        ts = idx[i]
                        tss = ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts)
                        curve.append({"date": tss, "account": float(v) if pd.notna(v) else None})
                if "return" in report_normal.columns:
                    r = report_normal["return"].dropna()
                    if len(r) > 1:
                        ra = risk_analysis(r, freq="day", mode="sum")
                        metrics = {
                            "annualized_return": float(ra.loc["annualized_return", "risk"]),
                            # qlib risk_analysis: information_ratio ≈ 日频 IR（均值/波动 * sqrt(N)）
                            "sharpe_ratio": float(ra.loc["information_ratio", "risk"]),
                            "max_drawdown": float(ra.loc["max_drawdown", "risk"]),
                        }
        except Exception as exc:  # noqa: BLE001
            logger.warning("metrics 提取失败: %s", exc)

        pos_preview = None
        try:
            if positions_normal is not None and not positions_normal.empty:
                pos_preview = json.loads(positions_normal.tail(5).to_json(orient="split", date_format="iso"))
        except Exception:  # noqa: BLE001
            pos_preview = str(type(positions_normal))

        return {
            "ok": True,
            "equity_curve": curve,
            "metrics": metrics,
            "report_columns": list(report_normal.columns) if report_normal is not None else [],
            "positions_preview": pos_preview,
        }

    def integrate_existing_strategy(
        self,
        old_strategy_signal: dict[str, Any] | list[dict[str, Any]],
    ) -> GenericResponseDTO:
        """将平台策略信号（``Signal`` 列 / 显式 score）转为 Qlib MultiIndex score，并可选跑对比回测。

        输入支持：

        - ``{ "records": [...], "instrument": "SH600519", "run_backtest": true, "start_time", "end_time", "account" }``
        - 或直接传 ``records`` 数组。

        ``records`` 每项: ``date``, ``Signal`` 或 ``signal`` 或 ``score``, 可选 ``instrument``。
        """
        payload: dict[str, Any]
        if isinstance(old_strategy_signal, list):
            payload = {"records": old_strategy_signal}
        else:
            payload = old_strategy_signal

        records = payload.get("records")
        if not isinstance(records, list) or not records:
            return {"ok": False, "error": "validation", "message": "records 须为非空数组"}

        inst = str(payload.get("instrument") or payload.get("symbol") or "SH600519").strip().upper()
        try:
            pred = _records_to_qlib_pred(records, default_instrument=inst)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": "convert_failed", "message": str(exc)}

        pr = pred.reset_index()
        if pr.shape[1] >= 3:
            pr = pr.rename(columns={pr.columns[-1]: "score"})
        preview = pr.head(20).assign(date=lambda x: x["datetime"].astype(str)).drop(columns=["datetime"]).to_dict(orient="records")

        out: dict[str, Any] = {
            "ok": True,
            "qlib_signal_format": "MultiIndex Series (instrument, datetime) -> score",
            "instrument_default": inst,
            "points": int(len(pred)),
            "preview": preview,
        }

        if payload.get("run_backtest"):
            strat = {
                "class": "TopkDropoutStrategy",
                "module_path": "qlib.contrib.strategy.signal_strategy",
                "kwargs": {
                    "topk": int(payload.get("topk", 1)),
                    "n_drop": int(payload.get("n_drop", 0)),
                    "signal": pred,
                },
            }
            bt_cfg = {
                "start_time": payload.get("start_time") or payload.get("start"),
                "end_time": payload.get("end_time") or payload.get("end"),
                "account": float(payload.get("account", payload.get("initial_capital", 1_000_000))),
                "benchmark": str(payload.get("benchmark", "SH000300")),
                "strategy": strat,
            }
            if not bt_cfg["start_time"] or not bt_cfg["end_time"]:
                out["backtest_error"] = "run_backtest=true 时需要 start_time/end_time"
            else:
                out["qlib_backtest"] = self.run_qlib_backtest(bt_cfg)

        return out


def create_default_qlib_service() -> QlibService:
    from app.modules.system.services.helpers.backtest_engine_access import create_backtest_engine
    return QlibService(engine=create_backtest_engine(), base_dir=BASE_DIR)
