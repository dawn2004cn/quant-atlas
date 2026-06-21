/**
 * VirtualSignalTable — react-window virtualized list for SignalFlag items.
 *
 * Replaces manual pagination with on-demand row rendering.
 * Only visible rows + overscan are mounted in the DOM.
 */

import { List } from "react-window";
import type { CSSProperties } from "react";
import type { SignalFlagItem } from "../../types/signalflag";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function fmt(v: number | undefined | null, decimals = 2): string {
  if (v == null || Number.isNaN(Number(v))) return "--";
  return Number(v).toFixed(decimals);
}

function fmtAmount(v: number | undefined | null): string {
  var val = Number(v || 0);
  if (val >= 1e8) return (val / 1e8).toFixed(2) + " 亿";
  if (val >= 1e4) return (val / 1e4).toFixed(2) + " 万";
  return val.toFixed(0);
}

function joinHz(h: { buy?: string[]; sell?: string[] } | undefined | null): string {
  if (!h) return "—";
  var b = h.buy?.length ? h.buy.join("，") : "—";
  var s = h.sell?.length ? h.sell.join("，") : "—";
  return "买 " + b + " | 卖 " + s;
}

function scoreClass(v: number): string {
  if (v >= 68) return "badge-success";
  if (v <= 42) return "badge-error";
  return "badge-ghost";
}

/* ------------------------------------------------------------------ */
/*  Row props type                                                     */
/* ------------------------------------------------------------------ */

type SignalRowProps = {
  items: SignalFlagItem[];
  onNavigate: (code: string) => void;
};

var ROW_HEIGHT = 48;

/* ------------------------------------------------------------------ */
/*  Row component                                                      */
/* ------------------------------------------------------------------ */

function SignalRow(props: {
  index: number;
  style: CSSProperties;
} & SignalRowProps) {
  var _it = props.items[props.index];
  var it = _it;

  return (
    <div
      style={props.style}
      className="flex items-center border-b border-slate-200/60 text-xs hover:bg-slate-100/50 dark:border-slate-700/40 dark:hover:bg-slate-800/30 cursor-pointer"
      onClick={function() { props.onNavigate(it.code); }}
      role="row"
    >
      <div className="w-[90px] shrink-0 px-2 font-mono font-medium truncate">{it.code}</div>
      <div className="w-[80px] shrink-0 px-2 truncate">{it.name}</div>
      <div className="w-[80px] shrink-0 px-2 text-right tabular-nums">{fmt(it.price)}</div>
      <div className={"w-[80px] shrink-0 px-2 text-right tabular-nums " + ((it.change_pct ?? 0) >= 0 ? "text-green-600" : "text-red-500")}>
        {(it.change_pct ?? 0) >= 0 ? "+" : ""}{fmt(it.change_pct)}%
      </div>
      <div className="w-[90px] shrink-0 px-2 text-right tabular-nums">{fmtAmount(it.amount)}</div>
      <div className="w-[65px] shrink-0 px-2 text-right tabular-nums">{fmt(it.turnover)}%</div>
      <div className="w-[90px] shrink-0 px-2 truncate">{it.industry}</div>
      <div className="flex-1 min-w-0 px-2 truncate text-slate-600">
        {(it.signal_strategies ?? []).map(function(s) { return s.name; }).join("，") || "—"}
      </div>
      <div className="w-[120px] shrink-0 px-2 truncate text-slate-600">
        {(it.signal_strategies_sell ?? []).map(function(s) { return s.name; }).join("，") || "—"}
      </div>
      <div className="w-[150px] shrink-0 px-2 truncate text-slate-500" title={joinHz(it.long_horizon)}>
        {joinHz(it.long_horizon).slice(0, 28)}
      </div>
      <div className="w-[65px] shrink-0 px-2 text-center">
        <span className={"badge " + scoreClass(it.safety_score) + " badge-xs"}>{fmt(it.safety_score, 1)}</span>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Header                                                             */
/* ------------------------------------------------------------------ */

function TableHeader() {
  return (
    <div className="flex items-center border-b border-slate-300 bg-slate-50/80 text-xs font-semibold text-slate-600 dark:border-slate-600 dark:bg-slate-800/60 dark:text-slate-300 shrink-0">
      <div className="w-[90px] shrink-0 px-2 py-2">代码</div>
      <div className="w-[80px] shrink-0 px-2 py-2">名称</div>
      <div className="w-[80px] shrink-0 px-2 py-2 text-right">现价</div>
      <div className="w-[80px] shrink-0 px-2 py-2 text-right">涨跌%</div>
      <div className="w-[90px] shrink-0 px-2 py-2 text-right">成交额</div>
      <div className="w-[65px] shrink-0 px-2 py-2 text-right">换手%</div>
      <div className="w-[90px] shrink-0 px-2 py-2">行业</div>
      <div className="flex-1 min-w-0 px-2 py-2">买点</div>
      <div className="w-[120px] shrink-0 px-2 py-2">卖点</div>
      <div className="w-[150px] shrink-0 px-2 py-2">多周期</div>
      <div className="w-[65px] shrink-0 px-2 py-2 text-center">安全分</div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  VirtualSignalTable                                                 */
/* ------------------------------------------------------------------ */

type Props = {
  items: SignalFlagItem[];
  total: number;
  onNavigate: (code: string) => void;
  height?: number;
};

export function VirtualSignalTable({
  items,
  total,
  onNavigate,
  height = 600,
}: Props) {
  if (!items.length) {
    return (
      <div className="text-sm text-slate-400 py-8 text-center">
        暂无数据
      </div>
    );
  }

  return (
    <div
      className="border rounded-lg overflow-hidden"
      style={{ height: height + 36 }}
    >
      <TableHeader />
      <List<SignalRowProps>
        rowCount={items.length}
        rowHeight={ROW_HEIGHT}
        rowComponent={SignalRow}
        rowProps={{ items, onNavigate }}
        overscanCount={10}
        style={{ overflowX: "hidden" } as CSSProperties}
      />
      <div className="border-t border-slate-200/60 px-2 py-1 text-xs text-slate-400 dark:border-slate-700/40 text-right">
        {"共 " + total + " 条 · 虚拟滚动 (仅渲染可见行)"}
      </div>
    </div>
  );
};