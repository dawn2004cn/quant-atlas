"""Offline RL research sidecar (TradeMaster-inspired, not live).

Tabular Q-learning on Feature Pipeline day-bar features. Actions are cash/long only.
``RL_LIVE_ENABLED`` defaults off; live execution is explicitly forbidden.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime_bool
from app.domain.alpha.feature_pipeline import FeatureSpec, build_feature_frame

logger = get_logger(__name__)

ACTIONS = ("flat", "long")
N_ACTIONS = 2
N_BINS = 3
N_STATES = N_BINS * N_BINS  # ret_1 × ma_bias_5


class RlLiveForbiddenError(RuntimeError):
    """Raised when RL research path is asked to touch live execution."""


def rl_live_enabled() -> bool:
    return get_runtime_bool("RL_LIVE_ENABLED", False)


def assert_rl_research_only() -> None:
    """Hard gate: RL must not place broker orders."""
    if rl_live_enabled():
        raise RlLiveForbiddenError(
            "rl_live_not_wired — RL_LIVE_ENABLED=1 is ignored; research sidecar never submits orders"
        )
    # even when disabled, any live hook should still refuse
    raise RlLiveForbiddenError("rl_live_forbidden")


def _models_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "instance" / "rl_research"


def _bin3(value: float, *, hi: float = 0.01) -> int:
    if value < -hi:
        return 0
    if value > hi:
        return 2
    return 1


def state_index(ret_1: float, ma_bias_5: float) -> int:
    return _bin3(float(ret_1)) * N_BINS + _bin3(float(ma_bias_5))


def states_from_frame(frame: pd.DataFrame) -> np.ndarray:
    ret = frame["ret_1"].astype(float).to_numpy() if "ret_1" in frame.columns else np.zeros(len(frame))
    bias = (
        frame["ma_bias_5"].astype(float).to_numpy()
        if "ma_bias_5" in frame.columns
        else np.zeros(len(frame))
    )
    return np.array([state_index(r, b) for r, b in zip(ret, bias, strict=False)], dtype=np.int32)


@dataclass
class RlTrainResult:
    ok: bool
    n_rows: int
    n_states: int = N_STATES
    episodes: int = 0
    train_return: float = 0.0
    valid_return: float = 0.0
    valid_max_drawdown: float = 0.0
    valid_sharpe: float = 0.0
    policy_path: str | None = None
    notes: list[str] = field(default_factory=list)
    live_enabled: bool = False
    synthetic_bars: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "n_rows": self.n_rows,
            "n_states": self.n_states,
            "episodes": self.episodes,
            "train_return": self.train_return,
            "valid_return": self.valid_return,
            "valid_max_drawdown": self.valid_max_drawdown,
            "valid_sharpe": self.valid_sharpe,
            "policy_path": self.policy_path,
            "notes": list(self.notes),
            "live_enabled": False,
            "synthetic_bars": self.synthetic_bars,
        }


def _equity_metrics(returns: Sequence[float]) -> tuple[float, float, float]:
    arr = np.asarray(list(returns), dtype=float)
    if arr.size == 0:
        return 0.0, 0.0, 0.0
    equity = np.cumprod(1.0 + arr)
    peak = np.maximum.accumulate(equity)
    dd = float(np.max((peak - equity) / np.where(peak == 0, 1.0, peak))) if equity.size else 0.0
    total = float(equity[-1] - 1.0)
    mu = float(np.mean(arr))
    sigma = float(np.std(arr))
    sharpe = float(mu / sigma * np.sqrt(252)) if sigma > 1e-12 else 0.0
    return total, dd, sharpe


def _rollout(q: np.ndarray, states: np.ndarray, next_ret: np.ndarray) -> np.ndarray:
    rets = []
    for t in range(len(states) - 1):
        a = int(np.argmax(q[int(states[t])]))
        rets.append(float(next_ret[t + 1]) if a == 1 else 0.0)
    return np.asarray(rets, dtype=float)


def train_q_policy(
    bars: list[dict[str, Any]] | pd.DataFrame,
    *,
    spec: FeatureSpec | None = None,
    episodes: int = 8,
    lr: float = 0.15,
    gamma: float = 0.9,
    epsilon: float = 0.15,
    seed: int = 42,
) -> tuple[np.ndarray, pd.DataFrame, dict[str, Any]]:
    spec = spec or FeatureSpec()
    df = bars if isinstance(bars, pd.DataFrame) else pd.DataFrame(bars)
    frame = build_feature_frame(df, spec)
    if frame.empty or "ret_1" not in frame.columns or len(frame) < 40:
        raise ValueError("rl_insufficient_rows")
    states = states_from_frame(frame)
    next_ret = frame["ret_1"].astype(float).to_numpy()
    # reward at t uses next day's return (already causal: features at t, ret_1[t+1] ≈ next close move)
    rng = np.random.default_rng(seed)
    q = np.zeros((N_STATES, N_ACTIONS), dtype=float)
    n = len(states)
    split = max(20, min(n - 10, int(n * 0.8)))
    train_idx = list(range(split - 1))
    for _ in range(max(1, episodes)):
        for t in train_idx:
            s = int(states[t])
            a = int(rng.integers(0, N_ACTIONS)) if rng.random() < epsilon else int(np.argmax(q[s]))
            r = float(next_ret[t + 1]) if a == 1 else 0.0
            s2 = int(states[t + 1])
            q[s, a] += lr * (r + gamma * float(np.max(q[s2])) - q[s, a])
    train_rets = _rollout(q, states[:split], next_ret[:split])
    valid_rets = _rollout(q, states[split - 1 :], next_ret[split - 1 :])
    tr_tot, _, _ = _equity_metrics(train_rets)
    va_tot, va_dd, va_sh = _equity_metrics(valid_rets)
    metrics = {
        "train_return": tr_tot,
        "valid_return": va_tot,
        "valid_max_drawdown": va_dd,
        "valid_sharpe": va_sh,
        "split": split,
        "n_rows": int(n),
        "episodes": int(episodes),
    }
    return q, frame, metrics


def save_policy(
    q: np.ndarray,
    *,
    metrics: dict[str, Any],
    spec_name: str = "cn_day_v0",
    symbol: str = "",
    synthetic_bars: bool = False,
    extra: dict[str, Any] | None = None,
) -> Path:
    out = _models_dir()
    out.mkdir(parents=True, exist_ok=True)
    payload = {
        "spec_name": spec_name,
        "symbol": symbol,
        "ts": datetime.now(timezone.utc).isoformat(),
        "q_table": q.tolist(),
        "actions": list(ACTIONS),
        "n_states": N_STATES,
        "metrics": metrics,
        "synthetic_bars": synthetic_bars,
        "live_enabled": False,
        "engine": "tabular_q_v0",
        **(extra or {}),
    }
    path = out / f"{spec_name}_latest.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_latest_policy(*, spec_name: str = "cn_day_v0") -> dict[str, Any] | None:
    path = _models_dir() / f"{spec_name}_latest.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("rl policy corrupt %s", path, exc_info=True)
        return None
    data["policy_path"] = str(path)
    return data


def infer_action(
    *,
    ret_1: float,
    ma_bias_5: float,
    spec_name: str = "cn_day_v0",
    q: np.ndarray | None = None,
) -> dict[str, Any]:
    table = q
    policy = None
    if table is None:
        policy = load_latest_policy(spec_name=spec_name)
        if not policy:
            return {"ok": False, "error": "rl_policy_not_found", "live_enabled": False}
        table = np.asarray(policy["q_table"], dtype=float)
    s = state_index(ret_1, ma_bias_5)
    a = int(np.argmax(table[s]))
    return {
        "ok": True,
        "state": s,
        "action": ACTIONS[a],
        "action_index": a,
        "q_values": [float(x) for x in table[s]],
        "live_enabled": False,
        "policy_ts": (policy or {}).get("ts"),
    }


def run_rl_research(
    bars: list[dict[str, Any]] | pd.DataFrame,
    *,
    spec_name: str = "cn_day_v0",
    symbol: str = "",
    episodes: int = 8,
    synthetic_bars: bool = False,
) -> RlTrainResult:
    q, _frame, metrics = train_q_policy(
        bars,
        spec=FeatureSpec(name=spec_name),
        episodes=episodes,
    )
    path = save_policy(
        q,
        metrics=metrics,
        spec_name=spec_name,
        symbol=symbol,
        synthetic_bars=synthetic_bars,
    )
    notes = ["research_only", "never_submits_orders"]
    if synthetic_bars:
        notes.append("synthetic_bars")
    return RlTrainResult(
        ok=True,
        n_rows=int(metrics.get("n_rows") or 0),
        episodes=int(metrics.get("episodes") or episodes),
        train_return=float(metrics.get("train_return") or 0.0),
        valid_return=float(metrics.get("valid_return") or 0.0),
        valid_max_drawdown=float(metrics.get("valid_max_drawdown") or 0.0),
        valid_sharpe=float(metrics.get("valid_sharpe") or 0.0),
        policy_path=str(path),
        notes=notes,
        live_enabled=False,
        synthetic_bars=synthetic_bars,
    )


__all__ = [
    "RlLiveForbiddenError",
    "RlTrainResult",
    "assert_rl_research_only",
    "infer_action",
    "load_latest_policy",
    "rl_live_enabled",
    "run_rl_research",
    "state_index",
    "train_q_policy",
]
