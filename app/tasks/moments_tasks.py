from __future__ import annotations

"""朋友圈：收盘自动发帖（基金经+ 6 Agent）"""


from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from app.core.logger import get_logger

from ..application.services.research.moments_service import MomentsService
from ..application.services.trading.investment_manager_service import InvestmentManagerService
from ..celery_app import celery as _celery
from ..config import INSTANCE_DIR, get_settings
from ..core.shanghai_time import today_sh_str
from ..infrastructure.repositories.deps import (
    create_investment_manager_repository,
    create_moments_repository,
    create_signal_flag_pool_repository,
    create_stock_cache,
)

logger = get_logger(__name__)

AGENT_ROLES = [
    "Macro",
    "Fundamental",
    "Technical",
    "Sentiment",
    "Backtest Optimizer",
    "Risk Manager",
]


def _svc() -> tuple[InvestmentManagerService, MomentsService]:
    s = get_settings()
    im_repo = create_investment_manager_repository(s)
    moments_repo = create_moments_repository(s)
    ims = InvestmentManagerService(
        im_repo,
        stock_cache=create_stock_cache(),
        signal_flag_pool=create_signal_flag_pool_repository(s),
    )
    ms = MomentsService(moments_repo)
    return ims, ms


def _nav_series(repo: Any, manager_id: str, *, limit: int = 420) -> list[dict[str, Any]]:
    """兼容 MySQL/SQLite：直接从仓库取净值序列，避免访问 service 私有属性"""
    return repo.get_nav_series(manager_id, limit=limit)


def _equity_series(nav: list[dict[str, Any]]) -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []
    for r in nav or []:
        d = str(r.get("nav_date") or "")[:10]
        v = float(r.get("equity") or 0)
        if d and v > 0:
            out.append((d, v))
    return out


def _return_pct(nav: list[dict[str, Any]], lookback: int) -> float:
    if not nav or len(nav) < lookback + 1:
        return 0.0
    a = float(nav[-1].get("equity") or 0)
    b = float(nav[-(lookback + 1)].get("equity") or 0)
    return 0.0 if b <= 0 else round((a / b - 1.0) * 100.0, 2)


def _plot_equity(nav: list[dict[str, Any]], *, out_path: Path) -> None:
    ser = _equity_series(nav)
    if len(ser) < 2:
        raise ValueError("nav_too_short")
    [x for x, _ in ser]
    ys = [y for _, y in ser]
    plt.figure(figsize=(10, 3.2), dpi=160)
    plt.plot(range(len(ys)), ys, linewidth=2.2)
    plt.title("Equity Curve (last 120)", fontsize=11)
    plt.grid(alpha=0.25)
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(out_path), bbox_inches="tight")
    plt.close()


def _attach_local_png(ms: MomentsService, *, file_path: Path) -> dict[str, Any]:
    # 相对 instance/uploads，供 /uploads/<path> 路由发送文
    rel = file_path.relative_to(INSTANCE_DIR / "uploads").as_posix()
    return {
        "media_type": "image",
        "file_name": file_path.name,
        "file_path": rel,
        "file_url": f"/uploads/{rel}",
        "mime_type": "image/png",
        "size_bytes": int(file_path.stat().st_size) if file_path.exists() else 0,
        "meta": {},
    }


def _top_weight_lines(holds: list[dict[str, Any]], *, top_n: int = 5) -> list[str]:
    rows = holds or []
    rows = sorted(rows, key=lambda x: float(x.get("weight") or 0), reverse=True)[: max(1, int(top_n))]
    out: list[str] = []
    for h in rows:
        sym = str(h.get("symbol") or "")
        w = float(h.get("weight") or 0) * 100.0
        mv = float(h.get("market_value") or 0)
        out.append(f"- {sym}：{w:.2f}%（市值¥{mv:,.0f}）")
    return out


def _weight_delta_lines(today: list[dict[str, Any]], prev: list[dict[str, Any]], *, top_n: int = 5) -> list[str]:
    tmap = {str(x.get("symbol") or ""): float(x.get("weight") or 0) for x in (today or [])}
    pmap = {str(x.get("symbol") or ""): float(x.get("weight") or 0) for x in (prev or [])}
    syms = set(tmap.keys()) | set(pmap.keys())
    deltas: list[tuple[str, float]] = []
    for s in syms:
        if not s:
            continue
        deltas.append((s, (tmap.get(s, 0.0) - pmap.get(s, 0.0))))
    deltas.sort(key=lambda x: abs(x[1]), reverse=True)
    out: list[str] = []
    for sym, dw in deltas[: max(1, int(top_n))]:
        out.append(f"- {sym}：{dw*100:+.2f}%")
    return out


def _trade_brief_lines(trades: list[dict[str, Any]], *, max_lines: int = 4) -> list[str]:
    rows = trades or []
    rows = rows[: max(1, int(max_lines))]
    out: list[str] = []
    for t in rows:
        action = str(t.get("action") or "").upper()
        sym = str(t.get("symbol") or "")
        px = float(t.get("price") or 0)
        shares = int(t.get("shares") or 0)
        reason = str(t.get("reason") or "")
        out.append(f"- {action} {sym} @¥{px:.2f} ×{shares}（{reason.rstrip()}）")
    return out


def _pick_rebalance_symbol(
    *,
    trades_today: list[dict[str, Any]],
    holdings_today: list[dict[str, Any]],
    holdings_prev: list[dict[str, Any]],
) -> tuple[str, str]:
    """挑选“今日调仓那支股票”的摘要标的

    规则
    - 若有今日/昨日快照：取 |权重变化| 最大的 symbol（更贴近“调仓影响”）
    - 否则：取当日净成交额（BUY-SELL）绝对值最大且0 symbol
    返回 (symbol, reason_code)
    """
    tmap = {str(x.get("symbol") or ""): float(x.get("weight") or 0) for x in (holdings_today or [])}
    pmap = {str(x.get("symbol") or ""): float(x.get("weight") or 0) for x in (holdings_prev or [])}
    if tmap and pmap:
        best_sym = ""
        best_abs = -1.0
        for sym in set(tmap.keys()) | set(pmap.keys()):
            if not sym:
                continue
            dw = tmap.get(sym, 0.0) - pmap.get(sym, 0.0)
            if abs(dw) > best_abs:
                best_abs = abs(dw)
                best_sym = sym
        if best_sym:
            return best_sym, "weight_delta_max"

    # fallback: net traded notional
    notional: dict[str, float] = {}
    for t in trades_today or []:
        sym = str(t.get("symbol") or "")
        if not sym:
            continue
        action = str(t.get("action") or "").upper()
        px = float(t.get("price") or 0)
        sh = float(t.get("shares") or 0)
        amt = px * sh
        if action == "BUY":
            notional[sym] = notional.get(sym, 0.0) + amt
        elif action == "SELL":
            notional[sym] = notional.get(sym, 0.0) - amt
    best_sym = ""
    best_abs = -1.0
    for sym, v in notional.items():
        if abs(v) > best_abs and abs(v) > 0:
            best_abs = abs(v)
            best_sym = sym
    return (best_sym, "net_notional_max") if best_sym else ("", "none")


def _manager_post(
    ms: MomentsService,
    *,
    manager: dict[str, Any],
    nav: list[dict[str, Any]],
    trades_today: list[dict[str, Any]],
    holdings_today: list[dict[str, Any]],
    holdings_prev: list[dict[str, Any]],
    prev_date: str | None,
    market_date: str,
) -> dict[str, Any]:
    mid = str(manager.get("manager_id") or "")
    name = str(manager.get("name") or mid)
    r_day = _return_pct(nav, 1)
    r_week = _return_pct(nav, 5)
    r_month = _return_pct(nav, 21)
    r_year = _return_pct(nav, 252)

    trade_lines = _trade_brief_lines(trades_today, max_lines=6) if trades_today else []
    top_lines = _top_weight_lines(holdings_today, top_n=5) if holdings_today else []
    delta_lines = (
        _weight_delta_lines(holdings_today, holdings_prev, top_n=5)
        if holdings_today and holdings_prev
        else []
    )
    pick_sym, pick_kind = _pick_rebalance_symbol(
        trades_today=trades_today,
        holdings_today=holdings_today,
        holdings_prev=holdings_prev,
    )
    if pick_sym:
        rebalance_head = f"{pick_sym}（{'仓位变化最大' if pick_kind == 'weight_delta_max' else '净成交额最大'}）"
    else:
        rebalance_head = "（今日无成交/无快照）"

    text = (
        f"【收盘战报】{market_date}\n"
        f"经理：{name}\n"
        f"今日调仓：{rebalance_head}\n"
        f"今日收益：{r_day:+.2f}% | 本周：{r_week:+.2f}% | 本月：{r_month:+.2f}% | 今年：{r_year:+.2f}%\n"
        + ("\n\n【今日调仓明细】\n" + "\n".join(trade_lines) if trade_lines else "")
        + ("\n\n【Top持仓（今日）】\n" + "\n".join(top_lines) if top_lines else "")
        + (
            f"\n\n【仓位变化（{prev_date}）】\n" + "\n".join(delta_lines)
            if delta_lines and prev_date
            else ""
        )
        + "\n\n（收益基于净值快照（equity）计算；附件为净值曲线截图）"
    )

    img_path = (INSTANCE_DIR / "uploads" / "moments" / "pm" / f"{mid}_{market_date}.png").resolve()
    try:
        _plot_equity(nav[-120:], out_path=img_path)
        attachments = [_attach_local_png(ms, file_path=img_path)]
    except Exception:
        attachments = []

    return ms.create_post(
        actor_type="manager",
        actor_id=mid,
        author_name=name,
        content_text=text,
        attachments=attachments,
        content={
            "returns": {"day": r_day, "week": r_week, "month": r_month, "year": r_year},
            "rebalance_symbol": pick_sym,
            "rebalance_pick": pick_kind,
            "trades_today": trades_today[:20],
            "top_holdings_today": holdings_today[:10],
            "holdings_prev_date": prev_date or "",
        },
        market_date=market_date,
    )


def _agent_post(ms: MomentsService, *, role: str, market_date: str) -> dict[str, Any]:
    # MVP：先给出可运行的模板内容；后续可接入 LangGraph 研究输出/图片
    text = (
        f"【{role}】收盘点评（{market_date}）\n"
        f"- 今日关注：风险控制与仓位纪律优先\n"
        f"- 建议：低情绪只卖不买门禁仍生效，避免追涨\n"
        f"- 说明：这是 MVP 模板，下一步接入研究 Agent 输出\n"
    )
    return ms.create_post(
        actor_type="agent",
        actor_id=role,
        author_name=f"Agent·{role}",
        content_text=text,
        attachments=[],
        content={"role": role, "kind": "close_note"},
        market_date=market_date,
    )


if _celery is not None:

    @_celery.task(name="app.tasks.moments_tasks.moments_after_close")
    def moments_after_close(market_date: str | None = None) -> dict[str, Any]:
        """收盘后自动发帖（默认北京时间当日）"""
        ims, ms = _svc()
        d = (market_date or today_sh_str())[:10]

        # 基金经理：仅 active=1 参与（入市排期之后）
        managers = ims.list_managers()
        managers = [m for m in managers if int(m.get("active") or 0) == 1]

        posted = 0
        failed = 0
        for m in managers:
            try:
                mid = str(m["manager_id"])
                nav = _nav_series(ims._repo, mid, limit=420)  # type: ignore[arg-type]
                trades_today = ims._repo.list_trades_by_date(mid, d, limit=120)
                holdings_today = ims._repo.get_holdings_snap(mid, d)
                prev_date = ims._repo.latest_holdings_snap_date_before(mid, d)
                holdings_prev = ims._repo.get_holdings_snap(mid, prev_date) if prev_date else []
                out = _manager_post(
                    ms,
                    manager=m,
                    nav=nav,
                    trades_today=trades_today,
                    holdings_today=holdings_today,
                    holdings_prev=holdings_prev,
                    prev_date=prev_date,
                    market_date=d,
                )
                posted += 1 if out.get("ok") else 0
            except Exception:
                failed += 1
                logger.exception("moments manager post failed: %s", m.get("manager_id"))

        # 6 agents
        for role in AGENT_ROLES:
            try:
                out = _agent_post(ms, role=role, market_date=d)
                posted += 1 if out.get("ok") else 0
            except Exception:
                failed += 1
                logger.exception("moments agent post failed: %s", role)

        return {"ok": True, "market_date": d, "posted": posted, "failed": failed, "managers": len(managers)}

else:
    moments_after_close = None  # type: ignore[misc, assignment]

