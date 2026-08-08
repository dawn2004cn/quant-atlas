from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Alpha Factory Orchestrator - 整合所有组件的统一服务层.

This orchestrates:
- rd-agent factor generation
- QlibTaskService experiments
- FactorVault persistence
- Post-mortem analysis
- Weekly meeting scheduling
"""


from typing import Any

from app.domain.alpha.factor_vault import (
    FactorVaultStorage,
    InMemoryFactorVaultStorage,
    get_factor_vault,
    MarketRegime,
)
from app.domain.alpha.postmortem_analysis import (
    PostMortemAnalysis,
    get_postmortem_analyzer,
    FailureType,
)
from app.domain.alpha.weekly_meeting import (
    WeeklyMeetingExecutor,
    get_weekly_meeting,
)
from app.domain.ports.qlib_task_ports import (
    QlibExperimentResult,
    QlibTaskService,
)
from app.modules.system.services.helpers.qlib_access import create_qlib_task_service
from app.core.logger import get_logger

logger = get_logger(__name__)


def _extract_ic_from_payload(payload: dict[str, Any] | None) -> float | None:
    if not payload:
        return None
    for key in ("ic", "ic_mean", "IC", "rank_ic"):
        if payload.get(key) is not None:
            try:
                return float(payload[key])
            except (TypeError, ValueError):
                continue
    metrics = payload.get("metrics")
    if isinstance(metrics, dict):
        return _extract_ic_from_payload(metrics)
    return None


def _factor_display_ic(factor: dict[str, Any]) -> tuple[float, bool]:
    """Return (ic_value, is_sharpe_proxy) for lineage visualization."""
    for source in (factor.get("metadata") or {}, factor.get("backtest_result") or {}):
        ic = _extract_ic_from_payload(source)
        if ic is not None:
            return ic, False
    try:
        return float(factor.get("sharpe_ratio") or 0), True
    except (TypeError, ValueError):
        return 0.0, True


def _find_factor_by_experiment_id(
    vault: FactorVaultStorage,
    experiment_id: str,
    *,
    scan_limit: int = 200,
) -> dict[str, Any] | None:
    for factor in vault.list_recent_factors(limit=scan_limit):
        if (factor.get("metadata") or {}).get("experiment_id") == experiment_id:
            return factor
    return None


def _dispatch_rdagent_evolution(*, factor_id: str, seed_formula: str) -> dict[str, Any]:
    """Enqueue targeted factor evolution via RD-Agent job store + Celery/thread."""
    import copy
    import threading

    from app.config import BASE_DIR
    from app.domain.services.rdagent_config import parse_rdagent_loop_params
    from app.modules.system.services.helpers.rdagent_access import create_rdagent_job_store
    from app.tasks.rdagent_tasks import celery_rdagent_enabled, run_rdagent_factor_generation

    body = {
        "loop_n": 1,
        "budget": {"max_loops": 1},
        "search_space": {
            "mode": "targeted_evolution",
            "parent_factor_id": factor_id,
            "seed_formula": seed_formula,
        },
    }
    store = create_rdagent_job_store(BASE_DIR)
    job_id = store.create(
        params_summary={
            "parent_factor_id": factor_id,
            "mode": "targeted_evolution",
        },
    )
    task_params = parse_rdagent_loop_params(body)
    task_params["_job_id"] = job_id
    payload = copy.deepcopy(task_params)

    mode = "thread"
    if celery_rdagent_enabled() and callable(getattr(run_rdagent_factor_generation, "apply_async", None)):
        run_rdagent_factor_generation.apply_async(args=[payload])
        mode = "celery"
    else:
        threading.Thread(
            target=lambda: run_rdagent_factor_generation(payload),
            daemon=True,
        ).start()

    return {"job_id": job_id, "execution_mode": mode}


class AlphaFactoryOrchestrator:
    """Alpha Factory 统一编排器."""

    def __init__(
        self,
        qlib_service: QlibTaskService | None = None,
        factor_vault: FactorVaultStorage | None = None,
    ) -> None:
        try:
            self._qlib = qlib_service or create_qlib_task_service()
        except RuntimeError:
            self._qlib = None
        self._vault = factor_vault or get_factor_vault()
        self._postmortem = get_postmortem_analyzer()
        self._weekly = get_weekly_meeting()

    def evolve_factor_targeted(self, factor_id: str) -> GenericResponseDTO:
        """基于特定因子进行定向演化."""
        parent = self._vault.get_factor(factor_id)
        if not parent:
            return {"ok": False, "error": "parent_factor_not_found"}
        
        formula = parent["formula"]

        try:
            dispatch = _dispatch_rdagent_evolution(factor_id=factor_id, seed_formula=formula)
        except Exception as exc:  # noqa: BLE001
            logger.warning("evolve_factor_targeted dispatch failed: %s", exc, exc_info=True)
            return {"ok": False, "error": "dispatch_failed", "parent_id": factor_id}

        return {
            "ok": True,
            "job_id": dispatch["job_id"],
            "parent_id": factor_id,
            "strategy": "Genetic Mutation",
            "execution_mode": dispatch["execution_mode"],
            "message": "定向演化任务已投递至 RD-Agent 队列",
        }

    def get_lineage_graph(self, limit: int = 100) -> GenericResponseDTO:
        """获取因子血缘图谱数据."""
        factors = self._vault.list_recent_factors(limit=limit)
        nodes = []
        links = []
        
        # Build map for fast lookup
        factor_ids = {f["factor_id"] for f in factors}
        
        for f in factors:
            metadata = f.get("metadata") or {}
            parents = f.get("parents") or metadata.get("parents") or []
            
            # Identify type
            ftype = "primitive"
            if parents:
                ftype = "derived" if len(parents) < 3 else "composite"
                
            ic_value, ic_proxy = _factor_display_ic(f)
            nodes.append({
                "id": f["factor_id"],
                "factor_id": f["factor_id"],
                "name": f["formula"][:20] + "...",
                "full_name": f["formula"],
                "type": ftype,
                "ic": ic_value,
                "ic_proxy": ic_proxy,
                "regime": f.get("regime"),
                "experiment_id": metadata.get("experiment_id"),
                "status": metadata.get("status"),
            })
            
            for pid in parents:
                # Only add links to factors that are in our result set (to keep graph clean)
                if pid in factor_ids:
                    links.append({"source": pid, "target": f["factor_id"]})
                    
        return {"nodes": nodes, "links": links}

    @property
    def qlib_service(self) -> QlibTaskService:
        return self._qlib

    @property
    def factor_vault(self) -> FactorVaultStorage:
        return self._vault

    @property
    def postmortem(self) -> PostMortemAnalysis:
        return self._postmortem

    @property
    def weekly_meeting(self) -> WeeklyMeetingExecutor:
        return self._weekly

    def submit_factor_experiment(
        self,
        formula: str,
        *,
        data_scope: dict[str, Any] | None = None,
        save_to_vault: bool = False,
    ) -> GenericResponseDTO:
        """提交因子实验.

        Args:
            formula: Alpha 表达式
            data_scope: 数据范围
            save_to_vault: 是否保存到因子库

        Returns:
            实验结果
        """
        exp_id = self._qlib.submit_experiment(
            formula,
            data_scope=data_scope,
        )

        result = {
            "experiment_id": exp_id,
            "formula": formula,
            "status": "submitted",
        }

        if save_to_vault:
            submit_meta: dict[str, Any] = {
                "experiment_id": exp_id,
                "status": "submitted",
            }
            if data_scope:
                submit_meta["data_scope"] = data_scope
            factor_id = self._vault.save_factor(
                formula,
                metadata=submit_meta,
            )
            result["factor_id"] = factor_id

        logger.info("Submitted experiment %s: %s", exp_id, formula[:80])
        return result

    def analyze_experiment_result(
        self,
        experiment_id: str,
        backtest_result: dict[str, Any] | None = None,
    ) -> GenericResponseDTO:
        """????????????."""
        # If we don't have a real experiment result, create a synthetic one
        if not backtest_result:
            backtest_result = {"sharpe_ratio": 0.0, "max_drawdown": 0.0, "ic": 0.0}
        """分析实验结果并更新因子库.

        Args:
            experiment_id: 实验 ID
            backtest_result: 回测结果

        Returns:
            分析结果
        """
        exp_result = self._qlib.get_experiment_result(experiment_id)
        formula = exp_result.formula

        if not exp_result.is_success:
            analysis = self._postmortem.analyze(
                formula,
                error_message=exp_result.error,
                backtest_result=backtest_result,
            )
            existing = _find_factor_by_experiment_id(self._vault, experiment_id)
            if existing:
                self._vault.patch_factor(
                    existing["factor_id"],
                    metadata={
                        "status": "failed",
                        "failure_type": analysis["failure_type"],
                    },
                )
            return {
                "status": "failed",
                "experiment_id": experiment_id,
                "failure_type": analysis["failure_type"],
                "root_cause": analysis["root_cause"],
                "patch_prompt": analysis["patch_prompt"],
            }

        sharpe = exp_result.sharpe_ratio
        mdd = exp_result.max_drawdown
        bt = backtest_result or exp_result.backtest_result or {}
        ic = _extract_ic_from_payload(bt)
        metadata: dict[str, Any] = {
            "experiment_id": experiment_id,
            "status": "completed",
        }
        if ic is not None:
            metadata["ic"] = ic
        equity_curve = bt.get("equity_curve")
        if equity_curve:
            metadata["equity_curve"] = equity_curve

        regime = self._infer_regime(sharpe, mdd)
        existing = _find_factor_by_experiment_id(self._vault, experiment_id)
        if existing:
            factor_id = existing["factor_id"]
            self._vault.patch_factor(
                factor_id,
                regime=regime.value if regime else None,
                sharpe_ratio=sharpe,
                max_drawdown=mdd,
                backtest_result=bt,
                metadata=metadata,
            )
        else:
            factor_id = self._vault.save_factor(
                formula,
                regime=regime.value if regime else None,
                sharpe_ratio=sharpe,
                max_drawdown=mdd,
                backtest_result=bt,
                metadata=metadata,
            )

        return {
            "status": "success",
            "experiment_id": experiment_id,
            "factor_id": factor_id,
            "sharpe_ratio": sharpe,
            "max_drawdown": mdd,
            "ic": ic,
            "regime": regime.value if regime else "unknown",
        }

    def _infer_regime(
        self,
        sharpe: float,
        mdd: float,
    ) -> MarketRegime | None:
        """推断市场状态."""
        if mdd > 0.15:
            return MarketRegime.VOLATILE
        if mdd < 0.05:
            return MarketRegime.LOW_VOLATILITY

        if sharpe > 1.5:
            return MarketRegime.TRENDING_UP
        if sharpe < 0:
            return MarketRegime.TRENDING_DOWN

        return MarketRegime.RANGING

    def run_weekly_meeting(self) -> GenericResponseDTO:
        """执行每周投研会议."""
        stale_factors = self._weekly.watcher.get_stale_factors()

        scan_result = self._weekly.execute_weekly_scan(
            max_experiments=100,
        )

        return {
            "stale_factors_count": stale_factors,
            "planned_experiments": scan_result["planned_experiments"],
            "meeting_prompt": scan_result["prompt"],
            "scheduled_time": self._weekly.scheduler.get_next_run_time(),
        }

    def get_dashboard(self) -> GenericResponseDTO:
        """获取 Alpha Factory 仪表板.

        数据来源:
        - total_factors: 因子库 (factor_vault.list_recent_factors)
        - avg_sharpe: 因子库中因子的Sharpe均值
        - failed_count: 失败分析记录 (postmortem.get_failure_history)
        - is_weekly_enabled: 投研周会调度器状态 (weekly_meeting.scheduler)
        - active_count: 有效因子数量（有时间序列数据的因子）

        数据产生方式:
        1. 因子数据: 通过 submit_factor_experiment 提交实验，
           实验完成后 analyze_experiment_result 将结果保存到 factor_vault
        2. 失败记录: 实验失败时 postmortem.analyze 会记录失败信息
        3. 周会状态: 投研周会定期执行扫描和因子切换
        """
        recent_factors = self._vault.list_recent_factors(limit=20)
        failed_experiments = self._postmortem.get_failure_history(limit=10)

        sharpe_values = [f.get("sharpe_ratio") for f in recent_factors if f.get("sharpe_ratio")]
        avg_sharpe = sum(sharpe_values) / len(sharpe_values) if sharpe_values else 0.0
        active_count = len([f for f in recent_factors if f.get("regime")])

        weekly_next = None
        weekly_enabled = False
        try:
            if hasattr(self._weekly, 'scheduler'):
                weekly_next = self._weekly.scheduler.get_next_run_time()
                weekly_enabled = getattr(self._weekly.scheduler, 'is_enabled', False)
        except Exception as e:
            logger.warning("alpha_factory_orchestrator.py.get_dashboard: %s", e)

        return {
            "total_factors": len(recent_factors),
            "avg_sharpe": avg_sharpe,
            "recent_sharpe": [
                {"formula": f["formula"][:60], "sharpe": f.get("sharpe_ratio")}
                for f in recent_factors[:5]
            ],
            "failed_count": len(failed_experiments),
            "weekly_meeting_next": weekly_next,
            "is_weekly_enabled": weekly_enabled,
            "active_count": active_count,
        }


_orchestrator: AlphaFactoryOrchestrator | None = None


def get_orchestrator() -> AlphaFactoryOrchestrator:
    """获取全局编排器."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AlphaFactoryOrchestrator()
    return _orchestrator


def set_orchestrator(orch: AlphaFactoryOrchestrator) -> None:
    """设置全局编排器."""
    global _orchestrator
    _orchestrator = orch