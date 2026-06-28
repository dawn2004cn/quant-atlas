"""Tier 2: Quant Boutique — Auto-Factor Mining, Vectorized Backtest, Alt-Data Connectors, Collaborative Lab."""

from __future__ import annotations

import json
import math
import random
import statistics
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from collections.abc import Callable

from app.core.logger import get_logger

logger = get_logger(__name__)


# ── Vectorized Backtest ─────────────────────────────────────────────

@dataclass
class VectorizedBacktestResult:
    """Result from a vectorized backtest run."""
    run_id: str
    strategy_id: str
    total_return: float = 0.0
    annualized_return: float = 0.0
    annualized_vol: float = 0.0
    sharpe: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    num_trades: int = 0
    parameter_grid_size: int = 0
    elapsed_ms: float = 0.0
    backend: str = "python"
    parameters: dict[str, Any] = field(default_factory=dict)


class VectorizedBacktestService:
    """Millisecond-grade vectorized backtest with grid search."""

    def run(self, strategy_id: str, returns: list[float], signals: list[float],
            params: dict | None = None, *, backend: str = "auto") -> VectorizedBacktestResult:
        """Run a vectorized backtest on return and signal arrays."""
        if backend in ("auto", "polars", "numpy"):
            try:
                return self._run_vectorized(strategy_id, returns, signals, params, prefer_polars=backend != "numpy")
            except ImportError:
                if backend == "polars":
                    raise
        return self._run_python(strategy_id, returns, signals, params)

    def _run_python(self, strategy_id: str, returns: list[float], signals: list[float],
                    params: dict | None = None) -> VectorizedBacktestResult:
        import time
        start = time.perf_counter()

        n = min(len(returns), len(signals))
        if n < 10:
            return VectorizedBacktestResult(run_id=f"vb.{uuid.uuid4().hex[:8]}", strategy_id=strategy_id)

        positions = [sig if sig > 0 else 0 for sig in signals[:n]]
        strategy_returns = [positions[i] * returns[i] for i in range(n)]

        total_ret = sum(strategy_returns)
        ann_ret = total_ret / n * 252 if n > 0 else 0
        ann_vol = statistics.stdev(strategy_returns) * math.sqrt(252) if n > 1 else 0
        sharpe = ann_ret / ann_vol if ann_vol > 0 else 0

        cum = 0
        peak = 0
        mdd = 0
        wins = 0
        for r in strategy_returns:
            cum += r
            if cum > peak:
                peak = cum
            dd = (peak - cum) / peak if peak > 0 else 0
            mdd = max(mdd, dd)
            if r > 0:
                wins += 1

        elapsed = (time.perf_counter() - start) * 1000

        return VectorizedBacktestResult(
            run_id=f"vb.{uuid.uuid4().hex[:8]}",
            strategy_id=strategy_id,
            total_return=round(total_ret, 4),
            annualized_return=round(ann_ret, 4),
            annualized_vol=round(ann_vol, 4),
            sharpe=round(sharpe, 4),
            max_drawdown=round(mdd, 4),
            win_rate=round(wins / n, 4) if n > 0 else 0,
            num_trades=n,
            elapsed_ms=round(elapsed, 2),
            backend="python",
            parameters=params or {},
        )

    def _run_vectorized(self, strategy_id: str, returns: list[float], signals: list[float],
                        params: dict | None, *, prefer_polars: bool = True) -> VectorizedBacktestResult:
        import time

        import numpy as np

        start = time.perf_counter()
        n = min(len(returns), len(signals))
        if n < 10:
            return VectorizedBacktestResult(run_id=f"vb.{uuid.uuid4().hex[:8]}", strategy_id=strategy_id)

        backend = "numpy"
        r = np.asarray(returns[:n], dtype=float)
        s = np.asarray(signals[:n], dtype=float)

        if prefer_polars:
            try:
                import polars as pl

                df = pl.DataFrame({"ret": r, "sig": s})
                pos = df.select(pl.when(pl.col("sig") > 0).then(pl.col("sig")).otherwise(0.0).alias("pos"))["pos"]
                strat = (pos.to_numpy() * r)
                backend = "polars"
            except ImportError:
                pos = np.where(s > 0, s, 0.0)
                strat = pos * r
        else:
            pos = np.where(s > 0, s, 0.0)
            strat = pos * r

        total_ret = float(np.sum(strat))
        ann_ret = total_ret / n * 252
        ann_vol = float(np.std(strat, ddof=1) * math.sqrt(252)) if n > 1 else 0.0
        sharpe = ann_ret / ann_vol if ann_vol > 0 else 0.0

        cum = np.cumsum(strat)
        peak = np.maximum.accumulate(cum)
        with np.errstate(divide="ignore", invalid="ignore"):
            dd = np.where(peak > 0, (peak - cum) / peak, 0.0)
        dd = np.nan_to_num(dd, nan=0.0, posinf=0.0, neginf=0.0)
        mdd = float(np.max(dd)) if len(dd) else 0.0
        wins = int(np.sum(strat > 0))
        elapsed = (time.perf_counter() - start) * 1000

        return VectorizedBacktestResult(
            run_id=f"vb.{uuid.uuid4().hex[:8]}",
            strategy_id=strategy_id,
            total_return=round(total_ret, 4),
            annualized_return=round(ann_ret, 4),
            annualized_vol=round(ann_vol, 4),
            sharpe=round(sharpe, 4),
            max_drawdown=round(mdd, 4),
            win_rate=round(wins / n, 4),
            num_trades=n,
            elapsed_ms=round(elapsed, 2),
            backend=backend,
            parameters=params or {},
        )

    def grid_search(self, strategy_id: str, returns: list[float],
                    param_grid: dict[str, list[float]],
                    signal_fn: Callable[[list[float], dict], list[float]]) -> list[VectorizedBacktestResult]:
        """Run grid search over parameter combinations."""
        import itertools
        import time
        start = time.perf_counter()

        keys = list(param_grid.keys())
        values = list(param_grid.values())
        results = []

        for combo in itertools.product(*values):
            params = dict(zip(keys, combo))
            signals = signal_fn(returns, params)
            result = self.run(strategy_id, returns, signals, params)
            results.append(result)

        results.sort(key=lambda r: -r.sharpe)
        logger.info("Grid search: %d combos in %.1fms", len(results), (time.perf_counter() - start) * 1000)
        return results[:20]  # top 20


# ── Alt-Data Connectors ─────────────────────────────────────────────

@dataclass
class AltDataSource:
    """An alternative data source configuration."""
    source_id: str
    name: str
    source_type: str  # social_media / satellite / supply_chain / news
    api_endpoint: str = ""
    api_key_required: bool = False
    refresh_interval_minutes: int = 60
    enabled: bool = True


@dataclass
class AltDataPoint:
    """A single alternative data point."""
    source_id: str
    symbol: str
    timestamp: str
    value: float
    metadata: dict[str, Any] = field(default_factory=dict)




    def parallel_grid_search(self, strategy_id, returns, param_grid, signal_fn, max_workers=4):
        """Run grid search with parallel workers and return heatmap-ready data."""
        import itertools
        import time
        import concurrent.futures
        start = time.perf_counter()

        keys = list(param_grid.keys())
        values = list(param_grid.values())
        combos = list(itertools.product(*values))
        total = len(combos)

        def _eval(combo):
            params = dict(zip(keys, combo))
            signals = signal_fn(returns, params)
            return self.run(strategy_id, returns, signals, params)

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            for r in pool.map(_eval, combos):
                results.append(r)

        results.sort(key=lambda r: -r.sharpe)
        elapsed = (time.perf_counter() - start) * 1000

        heatmap = {}
        for r in results[:50]:
            key = tuple(str(r.parameters.get(k, "")) for k in keys[:2])
            if key not in heatmap or r.sharpe > heatmap[key]["sharpe"]:
                heatmap[key] = {"sharpe": r.sharpe, "return": r.total_return, "mdd": r.max_drawdown}

        logger.info("Parallel grid search: %d combos in %.1fms (%.1f/s)", total, elapsed, total / (elapsed / 1000) if elapsed > 0 else 0)
        return {
            "top_results": [r.__dict__ for r in results[:10]],
            "total_combos": total,
            "elapsed_ms": round(elapsed, 2),
            "combos_per_sec": round(total / (elapsed / 1000), 1) if elapsed > 0 else 0,
            "heatmap": [{"x": k[0], "y": k[1] if len(k) > 1 else "", "sharpe": v["sharpe"], "return": v["return"], "mdd": v["mdd"]} for k, v in heatmap.items()],
            "best_params": results[0].parameters if results else {},
            "best_sharpe": results[0].sharpe if results else 0,
        }

    def sensitivity_heatmap(self, strategy_id, returns, param_a, range_a, param_b, range_b, signal_fn):
        """2D parameter sensitivity analysis returning heatmap grid."""
        param_grid = {param_a: range_a, param_b: range_b}
        result = self.parallel_grid_search(strategy_id, returns, param_grid, signal_fn, max_workers=1)
        grid = {}
        for item in result["heatmap"]:
            key = item["x"] + "|" + item["y"]
            grid[key] = {"sharpe": item["sharpe"], "return": item["return"]}
        return {
            "param_a": {"name": param_a, "values": range_a},
            "param_b": {"name": param_b, "values": range_b},
            "grid": grid,
            "best_sharpe": result["best_sharpe"],
            "best_params": result["best_params"],
        }
class AltDataConnectorService:
    """Alternative data connectors — social media, satellite, supply chain."""

    def __init__(self):
        root = Path(__file__).resolve().parents[4]
        self._store = root / "instance" / "alt_data"
        self._store.mkdir(parents=True, exist_ok=True)
        self._sources: dict[str, AltDataSource] = {}
        self._register_default_sources()

    def _register_default_sources(self):
        defaults = [
            AltDataSource(source_id="weibo_sentiment", name="微博情绪指数", source_type="social_media"),
            AltDataSource(source_id="xueqiu_discussion", name="雪球讨论热度", source_type="social_media"),
            AltDataSource(source_id="supply_chain_index", name="供应链景气指数", source_type="supply_chain"),
            AltDataSource(source_id="satellite_parking", name="卫星停车场饱和度", source_type="satellite"),
            AltDataSource(source_id="news_headline", name="新闻标题情感分析", source_type="news"),
        ]
        for s in defaults:
            self._sources[s.source_id] = s

    def list_sources(self) -> list[AltDataSource]:
        return list(self._sources.values())

    def fetch(self, source_id: str, symbol: str) -> AltDataPoint | None:
        """Fetch a data point from an alternative data source."""
        source = self._sources.get(source_id)
        if not source:
            return None

        # Simulate data fetch (real impl would call external API)
        if source.source_type == "social_media":
            value = random.uniform(-1, 1)  # sentiment score
        elif source.source_type == "supply_chain":
            value = random.uniform(40, 60)  # PMI-like index
        elif source.source_type == "satellite":
            value = random.uniform(0, 100)  # occupancy %
        else:
            value = random.uniform(-0.5, 0.5)

        return AltDataPoint(
            source_id=source_id,
            symbol=symbol,
            timestamp=datetime.now(timezone.utc).isoformat(),
            value=round(value, 4),
            metadata={"source_name": source.name, "source_type": source.source_type},
        )

    def fetch_all(self, symbol: str) -> dict[str, AltDataPoint]:
        """Fetch data from all enabled sources for a symbol."""
        results = {}
        for sid, source in self._sources.items():
            if source.enabled:
                point = self.fetch(sid, symbol)
                if point:
                    results[sid] = point
        return results


# ── Collaborative Lab ───────────────────────────────────────────────

@dataclass
class LabNotebook:
    """A collaborative research notebook."""
    notebook_id: str
    team_id: int
    title: str
    content: str  # markdown / code
    tags: list[str] = field(default_factory=list)
    created_by: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class SharedFactor:
    """A factor shared within a team."""
    factor_id: str
    team_id: int
    expression: str
    ic_history: list[float] = field(default_factory=list)
    shared_by: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AutoFactorMiningService:
    """Genetic programming based auto-factor mining."""

    def __init__(self):
        self._operators = ["add", "sub", "mul", "div", "gt", "lt", "abs", "neg", "sqrt", "square", "log", "rank", "delay", "ts_sum", "ts_mean", "ts_std", "corr", "cov"]
        self._factor_store_path = Path(__file__).resolve().parents[4] / "instance" / "auto_factors.jsonl"
        self._factor_store_path.parent.mkdir(parents=True, exist_ok=True)

    def _random_tree(self, max_depth=3, n_features=5):
        """Generate a random expression tree."""
        import random
        if max_depth <= 1:
            return ("feature", random.randint(0, n_features - 1))
        op = random.choice(self._operators)
        if op in ("abs", "neg", "sqrt", "square", "log", "rank"):
            return (op, self._random_tree(max_depth - 1, n_features))
        return (op, self._random_tree(max_depth - 1, n_features), self._random_tree(max_depth - 1, n_features))

    def _evaluate_tree(self, tree, data):
        """Evaluate an expression tree on data matrix."""
        import math
        import random
        if tree[0] == "feature":
            col = tree[1]
            if col < len(data):
                return [x[col] if isinstance(x, (list, tuple)) else 0 for x in data]
            return [random.gauss(0, 0.01) for _ in data]
        op = tree[0]
        if op in ("abs", "neg", "sqrt", "square", "log", "rank"):
            child = self._evaluate_tree(tree[1], data)
            if op == "abs": return [abs(v) for v in child]
            if op == "neg": return [-v for v in child]
            if op == "sqrt": return [math.sqrt(max(abs(v), 1e-10)) for v in child]
            if op == "square": return [v * v for v in child]
            if op == "log": return [math.log(max(abs(v), 1e-10)) for v in child]
            if op == "rank":
                sorted_vals = sorted(child)
                return [sorted_vals.index(v) / max(len(sorted_vals) - 1, 1) for v in child]
            return child
        left = self._evaluate_tree(tree[1], data)
        right = self._evaluate_tree(tree[2], data)
        if op == "add": return [l + r for l, r in zip(left, right)]
        if op == "sub": return [l - r for l, r in zip(left, right)]
        if op == "mul": return [l * r for l, r in zip(left, right)]
        if op == "div": return [l / max(abs(r), 1e-10) for l, r in zip(left, right)]
        if op == "gt": return [1.0 if l > r else 0.0 for l, r in zip(left, right)]
        if op == "lt": return [1.0 if l < r else 0.0 for l, r in zip(left, right)]
        return [l + r for l, r in zip(left, right)]

    def _compute_ic(self, factor_values, forward_returns):
        """Compute Information Coefficient (rank correlation)."""
        import random
        n = min(len(factor_values), len(forward_returns))
        if n < 5: return random.uniform(0, 0.05)
        fv = factor_values[:n]
        fr = forward_returns[:n]
        fv_rank = sorted((v, i) for i, v in enumerate(fv))
        fr_rank = sorted((v, i) for i, v in enumerate(fr))
        rank_map_f = {idx: r for r, (_, idx) in enumerate(fv_rank)}
        rank_map_r = {idx: r for r, (_, idx) in enumerate(fr_rank)}
        nf = len(fv)
        d_sq = sum((rank_map_f.get(i, 0) - rank_map_r.get(i, 0)) ** 2 for i in range(nf))
        return 1 - (6 * d_sq) / max(nf * (nf * nf - 1), 1)

    def mutate(self, tree, rate=0.3):
        """Mutate a tree by replacing random subtrees."""
        import random
        if random.random() < rate:
            return self._random_tree(max_depth=2)
        if len(tree) > 1 and isinstance(tree[1], tuple):
            return (tree[0], self.mutate(tree[1], rate))
        if len(tree) > 2 and isinstance(tree[2], tuple):
            return (tree[0], tree[1], self.mutate(tree[2], rate))
        return tree

    def crossover(self, tree_a, tree_b):
        """Crossover: swap random subtrees between two trees."""
        import random
        if random.random() < 0.5:
            return tree_a
        if len(tree_a) > 1 and isinstance(tree_a[1], tuple) and len(tree_b) > 1 and isinstance(tree_b[1], tuple):
            return (tree_a[0], tree_b[1], tree_a[2]) if len(tree_a) > 2 else (tree_a[0], tree_b[1])
        return tree_a

    def run_evolution(self, data, forward_returns, population_size=50, generations=10):
        """Run genetic programming evolution to find high-IC factors."""
        import random
        population = [self._random_tree(max_depth=3) for _ in range(population_size)]

        history = []
        for gen in range(generations):
            scores = []
            for tree in population:
                try:
                    values = self._evaluate_tree(tree, data)
                    ic = self._compute_ic(values, forward_returns)
                    scores.append((abs(ic), tree))
                except Exception:
                    scores.append((0.0, tree))
            scores.sort(key=lambda x: x[0], reverse=True)
            best_ic = scores[0][0] if scores else 0
            history.append({"generation": gen + 1, "best_ic": round(best_ic, 6), "population_size": len(population)})

            elite_count = max(2, population_size // 5)
            next_gen = [scores[i][1] for i in range(elite_count)]
            while len(next_gen) < population_size:
                if random.random() < 0.7 and len(scores) >= 2:
                    parent_a = random.choice(scores[:max(10, population_size // 2)])[1]
                    parent_b = random.choice(scores[:max(10, population_size // 2)])[1]
                    child = self.crossover(parent_a, parent_b)
                    child = self.mutate(child)
                    next_gen.append(child)
                else:
                    next_gen.append(self._random_tree(max_depth=3))
            population = next_gen

        best = max(((abs(self._compute_ic(self._evaluate_tree(t, data), forward_returns)), t) for t in population), key=lambda x: x[0])
        return {
            "best_ic": round(best[0], 6),
            "generations_run": generations,
            "history": history,
            "best_factor_expr": str(best[1]),
        }

    def save_factor(self, name, expression, ic, created_by="system"):
        """Save a mined factor to the store."""
        import json
        import uuid
        record = {
            "factor_id": f"af.{uuid.uuid4().hex[:8]}",
            "name": name,
            "expression": str(expression),
            "ic": round(ic, 6),
            "created_by": created_by,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._factor_store_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def list_factors(self, min_ic=0.0) -> list[dict]:
        """List all mined factors with IC above threshold."""
        import json
        if not self._factor_store_path.exists():
            return []
        factors = []
        with self._factor_store_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip(): continue
                f = json.loads(line)
                if f.get("ic", 0) >= min_ic:
                    factors.append(f)
        return sorted(factors, key=lambda x: x.get("ic", 0), reverse=True)


class CollaborativeLabService:
    """Shared research environment — notebooks, factors, backtest reports."""

    def __init__(self):
        root = Path(__file__).resolve().parents[4]
        self._store = root / "instance" / "collab_lab"
        self._store.mkdir(parents=True, exist_ok=True)
        self._notebooks_file = self._store / "notebooks.jsonl"
        self._factors_file = self._store / "shared_factors.jsonl"

    def create_notebook(self, team_id: int, title: str, content: str,
                        created_by: int, tags: list[str] | None = None) -> LabNotebook:
        """Create a shared research notebook."""
        nb = LabNotebook(
            notebook_id=f"nb.{uuid.uuid4().hex[:8]}",
            team_id=team_id,
            title=title,
            content=content,
            tags=tags or [],
            created_by=created_by,
        )
        with self._notebooks_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(nb.__dict__, ensure_ascii=False) + "\n")
        return nb

    def list_notebooks(self, team_id: int) -> list[LabNotebook]:
        if not self._notebooks_file.exists():
            return []
        notebooks = []
        with self._notebooks_file.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                data = json.loads(line)
                if int(data.get("team_id", -1)) == team_id:
                    notebooks.append(LabNotebook(**data))
        return notebooks

    def share_factor(self, team_id: int, expression: str, shared_by: int,
                     ic_history: list[float] | None = None) -> SharedFactor:
        """Share a factor with the team."""
        factor = SharedFactor(
            factor_id=f"sf.{uuid.uuid4().hex[:8]}",
            team_id=team_id,
            expression=expression,
            ic_history=ic_history or [],
            shared_by=shared_by,
        )
        with self._factors_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(factor.__dict__, ensure_ascii=False) + "\n")
        return factor

    def list_shared_factors(self, team_id: int) -> list[SharedFactor]:
        if not self._factors_file.exists():
            return []
        factors = []
        with self._factors_file.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                data = json.loads(line)
                if int(data.get("team_id", -1)) == team_id:
                    factors.append(SharedFactor(**data))
        return factors
