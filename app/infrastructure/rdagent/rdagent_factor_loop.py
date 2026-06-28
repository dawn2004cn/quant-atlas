from __future__ import annotations
"""
RD-Agent(Q) 因子挖掘循环封装：对齐本地 Qlib 数据路径（cn_data / csi300 等），限制 loop 次数以控制成本。

依赖：``pip install rdagent``（及 RD-Agent 文档中的 LLM / 运行环境配置）。
"""


import asyncio
import contextlib
import re
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ...config import BASE_DIR
from ...core.logger import get_logger


logger = get_logger(__name__)

ProgressCallback = Callable[[int, str], None]


def _factor_template_source() -> Path:
    import rdagent

    for pkg_path in rdagent.__path__:
        candidate = Path(pkg_path) / "scenarios" / "qlib" / "experiment" / "factor_template"
        if candidate.exists():
            return candidate.resolve()

    msg = "rdagent scenarios/qlib/experiment/factor_template not found — namespace package path empty or rdagent not installed"
    raise FileNotFoundError(msg)


def _patch_yaml_text(text: str, *, provider_uri: str, market: str, benchmark: str) -> str:
    uri = str(Path(provider_uri).expanduser().resolve()).replace("\\", "/")
    out = re.sub(
        r"provider_uri:\s*[\"']?[^\"'\n]+[\"']?",
        f'provider_uri: "{uri}"',
        text,
    )
    out = re.sub(r"market:\s*&market\s+\S+", f"market: &market {market}", out)
    out = re.sub(r"benchmark:\s*&benchmark\s+\S+", f"benchmark: &benchmark {benchmark}", out)
    return out


def prepare_patched_factor_template(
    *,
    provider_uri: str,
    market: str,
    benchmark: str,
    dest_root: Path | None = None,
) -> Path:
    """拷贝 RD-Agent 内置 ``factor_template`` 并覆写 ``provider_uri`` / ``market`` / ``benchmark``。"""
    src = _factor_template_source()
    if not src.is_dir():
        raise FileNotFoundError(f"rdagent factor_template missing: {src}")
    root = Path(dest_root or (BASE_DIR / "instance" / "rdagent_factor_template"))
    dest = root / "factor_template"
    if dest.exists():
        shutil.rmtree(dest, onexc=lambda fn, path, exc: logger.warning("rmtree %s: %s", path, exc))
    shutil.copytree(src, dest)
    for yml in dest.glob("*.yaml"):
        raw = yml.read_text(encoding="utf-8")
        yml.write_text(_patch_yaml_text(raw, provider_uri=provider_uri, market=market, benchmark=benchmark), encoding="utf-8")
    logger.info("patched factor template at %s (market=%s)", dest, market)
    return dest


@contextlib.contextmanager
def _patched_qlib_factor_experiment(template_folder: Path):
    import rdagent.scenarios.qlib.experiment.factor_experiment as fe_mod
    from rdagent.scenarios.qlib.experiment.workspace import QlibFBWorkspace

    original_init = fe_mod.QlibFactorExperiment.__init__

    def _wrapped_init(self, *args: Any, **kwargs: Any) -> None:
        original_init(self, *args, **kwargs)
        self.experiment_workspace = QlibFBWorkspace(template_folder_path=template_folder)

    fe_mod.QlibFactorExperiment.__init__ = _wrapped_init  # type: ignore[method-assign]
    try:
        yield
    finally:
        fe_mod.QlibFactorExperiment.__init__ = original_init  # type: ignore[method-assign]


def _patch_data_folder_intro() -> None:
    """Patch ``generate_data_folder_from_qlib`` to skip Docker + create empty data folders."""
    import os
    from rdagent.scenarios.qlib.experiment.utils import FACTOR_COSTEER_SETTINGS
    for attr in ("data_folder", "data_folder_debug"):
        folder = getattr(FACTOR_COSTEER_SETTINGS, attr, None)
        if folder:
            os.makedirs(folder, exist_ok=True)
    import rdagent.scenarios.qlib.experiment.utils as _utils
    _utils.generate_data_folder_from_qlib = lambda: None


def _patch_qlibfb_workspace_execute() -> None:
    """Replace ``QlibFBWorkspace.execute`` Docker/Conda logic with local subprocess.

    RD-Agent 的 ``QlibFBWorkspace.execute`` 依赖 ``QTDockerEnv`` 或 ``QlibCondaEnv``
    来运行 ``qrun`` 和 ``read_exp_res.py``。在 Windows 上既没有 Docker 也没有
    ``rdagent4qlib`` conda 环境，直接在当前 Python 子进程中执行。
    """
    import subprocess
    import sys

    import pandas as pd

    import rdagent.scenarios.qlib.experiment.workspace as _ws_mod

    def _local_execute(self, qlib_config_name: str = "conf.yaml", run_env: dict | None = None, *args: Any, **kwargs: Any) -> tuple:
        import os as _os
        import logging as _log
        _logger = _log.getLogger("QlibFBWorkspace.local_execute")
        env = dict(_os.environ)
        if run_env:
            env.update(run_env)
        ws_path = str(self.workspace_path)

        qrun_result = subprocess.run(  # noqa: S603  # qrun from local PATH; qlib_config_name defaults to conf.yaml
            ["qrun", qlib_config_name],
            cwd=ws_path,
            env={**env, "PYTHONPATH": "./"},
            capture_output=True, text=True, timeout=3600,
        )
        stdout = qrun_result.stdout + "\n" + qrun_result.stderr

        read_exp = subprocess.run(
            [sys.executable, "read_exp_res.py"],
            cwd=ws_path,
            env=env,
            capture_output=True, text=True, timeout=300,
        )
        stdout += "\n" + read_exp.stdout + "\n" + read_exp.stderr

        ret_path = self.workspace_path / "ret.pkl"
        if ret_path.exists():
            try:
                pd.read_pickle(ret_path)  # noqa: S301  # reads from locally-generated workspace file (controlled path)
            except Exception:
                logger.debug("Failed to read ret.pkl from path=%s", ret_path)

        qlib_res_path = self.workspace_path / "qlib_res.csv"
        if qlib_res_path.exists():
            try:
                return pd.read_csv(qlib_res_path, index_col=0).iloc[:, 0], stdout
            except Exception:
                logger.debug("Failed to read qlib_res.csv from path=%s", qlib_res_path)
        return None, stdout

    _ws_mod.QlibFBWorkspace.execute = _local_execute


def _summarize_loop(loop: Any) -> dict[str, Any]:
    """从 ``FactorRDLoop.trace`` 抽取假设、因子公式、实现片段与 qlib 数值结果。"""
    rounds: list[dict[str, Any]] = []
    trace = getattr(loop, "trace", None)
    hist = getattr(trace, "hist", None) if trace is not None else None
    if not hist:
        return {"rounds": [], "note": "empty trace"}

    for exp, fb in hist:
        row: dict[str, Any] = {
            "feedback_decision": getattr(fb, "decision", None),
            "observations": (getattr(fb, "observations", None) or "")[:2000],
            "hypothesis_evaluation": (getattr(fb, "hypothesis_evaluation", None) or "")[:2000],
        }
        sub_tasks = getattr(exp, "sub_tasks", None) or []
        tasks_out: list[dict[str, Any]] = []
        for t in sub_tasks:
            if hasattr(t, "get_task_information_and_implementation_result"):
                tasks_out.append(t.get_task_information_and_implementation_result())
            elif hasattr(t, "factor_formulation"):
                tasks_out.append(
                    {
                        "factor_name": getattr(t, "factor_name", ""),
                        "factor_formulation": getattr(t, "factor_formulation", ""),
                        "factor_description": getattr(t, "factor_description", ""),
                    }
                )
        row["tasks"] = tasks_out
        sw = getattr(exp, "sub_workspace_list", None) or []
        codes: list[dict[str, str]] = []
        for ws in sw[:3]:
            fd = getattr(ws, "file_dict", None) or {}
            for name, content in list(fd.items())[:5]:
                if isinstance(content, str) and name.endswith(".py"):
                    codes.append({"file": name, "snippet": content[:4000]})
        row["code_snippets"] = codes
        res = getattr(exp, "result", None)
        if res is not None and hasattr(res, "to_dict"):
            row["qlib_metrics_series"] = {str(k): float(v) for k, v in res.items() if _is_number(v)}
        elif res is not None:
            row["qlib_result_repr"] = str(res)[:2000]
        rounds.append(row)

    return {"rounds": rounds, "round_count": len(rounds)}


def _is_number(v: Any) -> bool:
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False


def _patch_select_for_windows() -> None:
    import select as _select_mod
    if not hasattr(_select_mod, "poll"):
        import threading

        _select_mod.POLLIN = 1
        _select_mod.POLLOUT = 4
        _select_mod.POLLERR = 8
        _select_mod.POLLHUP = 16

        class _PseudoPoller:
            def __init__(self) -> None:
                self._fds: dict[int, int] = {}
                self._lock = threading.Lock()
            def register(self, fd: int, events: int = 1) -> None:
                with self._lock:
                    self._fds[fd] = events
            def unregister(self, fd: int) -> None:
                with self._lock:
                    self._fds.pop(fd, None)
            def poll(self, timeout: float | None = None) -> list[tuple[int, int]]:
                with self._lock:
                    fds = list(self._fds.keys())
                if not fds:
                    return []
                r, _, _ = _select_mod.select(fds, [], [], timeout if timeout is not None else 0.5)
                return [(fd, 1) for fd in r]

        _select_mod.poll = lambda: _PseudoPoller()  # type: ignore[attr-defined]
        _select_mod.select = lambda *args, **kwargs: ([], [], [])  # type: ignore[attr-defined]


def run_factor_mining_loop(
    params: dict[str, Any] | None = None,
    *,
    progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    """
    运行 RD-Agent **因子专用** 循环（``FactorRDLoop``），限制 ``loop_n`` 控制成本。

    ``params`` 常用字段：

    - ``provider_uri``: Qlib 数据目录（默认 ``instance/qlib_bin`` 或项目下路径）
    - ``market``: 如 ``csi300``、``csi500``、``csi100``
    - ``benchmark``: 默认 ``SH000300``
    - ``loop_n``: 外层循环次数，建议 ``5``–``10``
    - ``evolving_n``: 写入 ``FactorBasePropSetting``（与 RD-Agent 配置一致）
    - ``template_dest``: 补丁模板输出目录（可选）
    """
    _patch_select_for_windows()
    p = dict(params or {})
    provider = str(p.get("provider_uri") or (BASE_DIR / "instance" / "qlib_bin").resolve())
    market = str(p.get("market") or "csi300").strip()
    benchmark = str(p.get("benchmark") or "SH000300").strip()
    loop_n = int(p.get("loop_n") or p.get("max_loops") or 7)
    loop_n = max(1, min(loop_n, 20))
    evolving_n = int(p.get("evolving_n") or loop_n)
    evolving_n = max(1, min(evolving_n, 30))
    template_dest = p.get("template_dest")
    dest_path = Path(template_dest) if template_dest else None

    def _prog(pc: int, msg: str) -> None:
        if progress:
            progress(pc, msg)
        logger.info("rdagent factor loop [%s%%] %s", pc, msg)

    _prog(1, "准备因子模板与 Qlib 路径")

    try:
        template_folder = prepare_patched_factor_template(
            provider_uri=provider,
            market=market,
            benchmark=benchmark,
            dest_root=dest_path,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("prepare_patched_factor_template failed")
        return {"ok": False, "error": "template_prepare_failed", "message": str(exc)}

    try:
        from rdagent.app.qlib_rd_loop.conf import FACTOR_PROP_SETTING
        from rdagent.app.qlib_rd_loop.factor import FactorRDLoop
    except ImportError as exc:
        return {"ok": False, "error": "import_error", "message": f"rdagent 未正确安装: {exc}"}

    _prog(5, f"启动 FactorRDLoop loop_n={loop_n} evolving_n={evolving_n}")

    # --- 补丁：Docker/Conda → 本地 subprocess ---
    _patch_data_folder_intro()
    _patch_qlibfb_workspace_execute()

    # --- 增强点：配置 LLM（统一入口）---
    from ...core.llm_config import setup_llm_env
    llm_info = setup_llm_env()
    logger.info("RD-Agent using model: %s at %s", llm_info["model"], llm_info["base_url"])
    # ----------------------------------------

    summary: dict[str, Any] = {}
    loop: Any = None
    with _patched_qlib_factor_experiment(template_folder):
        loop = FactorRDLoop(FACTOR_PROP_SETTING)
        try:
            asyncio.run(loop.run(loop_n=loop_n))
        except Exception as exc:  # noqa: BLE001
            logger.exception("FactorRDLoop.run failed")
            summary = _summarize_loop(loop)
            return {
                "ok": False,
                "error": "loop_failed",
                "message": str(exc),
                "provider_uri": provider,
                "market": market,
                "benchmark": benchmark,
                "loop_n": loop_n,
                "report": summary,
            }

    _prog(95, "汇总 trace")
    summary = _summarize_loop(loop)
    _prog(100, "完成")
    return {
        "ok": True,
        "provider_uri": provider,
        "market": market,
        "benchmark": benchmark,
        "loop_n": loop_n,
        "report": summary,
    }
