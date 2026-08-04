import { useState, useRef, useCallback } from "react";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { apiFetchV1 } from "../lib/api";
import {
  ResponsiveContainer,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Area,
  AreaChart,
} from "recharts";

type SimResult = {
  symbol?: string;
  series?: Array<{ date: string; value: number }>;
  stats?: { mean?: number; std?: number };
  meta?: { demo?: boolean; disclaimer?: string };
};

const QLIB_OPERATORS = [
  { op: "Mean($, 20)", label: "Mean(x, n) - 均值" },
  { op: "Std($, 20)", label: "Std(x, n) - 标准差" },
  { op: "ROC($, 10)", label: "ROC(x, n) - 变动率" },
  { op: "Ref($, 1)", label: "Ref(x, n) - 历史引用" },
  { op: "Rank($)", label: "Rank(x) - 横截面排名" },
  { op: "Corr($, $close, 10)", label: "Corr(x, y, n) - 相关性" },
  { op: "EMA($, 12)", label: "EMA(x, n) - 指数均线" },
];

const HINTS = [
  "尝试 Slope($close, 5) 捕捉趋势斜率",
  "($close - Low($low, 5)) / (High($high, 5) - Low($low, 5)) 计算 KDJ 风格的超买超卖",
  "配合 Rank 算子消除量纲影响",
];

export default function QuantLab() {
  const [formula, setFormula] = useState("Mean($close, 5) / $close");
  const [symbol, setSymbol] = useState("600519");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<SimResult | null>(null);
  const [error, setError] = useState("");
  const editorRef = useRef<HTMLTextAreaElement>(null);

  const insertOp = useCallback((op: string) => {
    const ta = editorRef.current;
    if (!ta) return;
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    const val = ta.value;
    const newVal = val.substring(0, start) + op + val.substring(end);
    setFormula(newVal);
    setTimeout(() => {
      ta.focus();
      ta.setSelectionRange(start + op.length, start + op.length);
    }, 0);
  }, []);

  async function runSimulation() {
    if (!formula.trim()) return;
    setRunning(true);
    setError("");
    setResult(null);
    try {
      const data = await apiFetchV1<SimResult>(
        `/alpha-factory/simulate?formula=${encodeURIComponent(formula)}&symbol=${encodeURIComponent(symbol)}`
      );
      if (!data.series || !data.stats) throw new Error("模拟结果格式异常");
      setResult(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "模拟失败");
    } finally {
      setRunning(false);
    }
  }

  function sendToEvolution() {
    // placeholder - would POST to evolution API
  }

  return (
    <div className="space-y-6">
      <PageQuickNav items={QUICK_NAV_PRESETS.quantLab} />
      <div>
        <div className="text-xs text-[var(--quant-accent)] font-medium mb-1">Alpha Sandbox</div>
        <h1 className="page-title">量化实验室</h1>
        <p className="text-[var(--quant-muted)] text-sm mt-1">
          手动编写 Qlib 表达式并实时模拟因子走势
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Editor */}
        <div className="lg:col-span-3 space-y-4">
          <div className="quant-card">
            <div className="flex items-center justify-between mb-3">
              <div className="text-sm font-bold">公式试验场</div>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  placeholder="股票代码"
                  className="input input-bordered input-sm w-28 bg-[var(--quant-surface)] border-[var(--quant-surface-border)]"
                />
                <button
                  type="button"
                  className="btn-brand !text-xs"
                  onClick={runSimulation}
                  disabled={running}
                >
                  {running ? "计算中..." : "立即模拟"}
                </button>
              </div>
            </div>
            <textarea
              ref={editorRef}
              value={formula}
              onChange={(e) => setFormula(e.target.value)}
              spellCheck={false}
              rows={4}
              className="w-full font-mono text-sm p-3 rounded-xl bg-[var(--quant-surface)] border border-[var(--quant-surface-border)] text-[var(--quant-fg)] focus:outline-none focus:ring-2 focus:ring-[var(--quant-accent)] resize-none"
            />
          </div>

          {/* Stats */}
          {result?.stats && (
            <div className="flex items-center gap-3">
              <span className="badge-soft">均值: {Number(result.stats.mean).toFixed(4)}</span>
              <span className="badge-soft">标准差: {Number(result.stats.std).toFixed(4)}</span>
              {result.meta?.demo && (
                <span className="badge-soft !bg-[var(--quant-warn)]/10 !text-[var(--quant-warn)]">
                  {result.meta.disclaimer || "演示模式"}
                </span>
              )}
              <button
                type="button"
                className="btn btn-ghost btn-xs ml-auto"
                onClick={sendToEvolution}
              >
                投递至演化工厂
              </button>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="quant-card border-[var(--quant-danger)]/30 bg-[var(--quant-danger)]/5 text-sm text-[var(--quant-danger)]">
              {error}
            </div>
          )}

          {/* Chart */}
          <div className="quant-card min-h-[280px]">
            {running ? (
              <div className="flex items-center justify-center h-64 text-[var(--quant-muted)] text-sm">
                计算模拟序列中...
              </div>
            ) : result?.series ? (
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={result.series}>
                  <defs>
                    <linearGradient id="factorGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--quant-accent)" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="var(--quant-accent)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--quant-line-soft)" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 11, fill: "var(--quant-muted)" }}
                    tickFormatter={(v: string) => v.slice(5)}
                  />
                  <YAxis tick={{ fontSize: 11, fill: "var(--quant-muted)" }} scale="auto" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "var(--quant-surface-strong)",
                      border: "1px solid var(--quant-surface-border)",
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="value"
                    stroke="var(--quant-accent)"
                    strokeWidth={2}
                    fill="url(#factorGrad)"
                    dot={false}
                    name="因子值"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-64 text-[var(--quant-muted)] text-sm">
                输入公式并点击模拟，在此查看因子序列可视化
              </div>
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          <div className="quant-card">
            <div className="text-sm font-bold mb-3">算子库</div>
            <div className="space-y-1 max-h-64 overflow-y-auto">
              {QLIB_OPERATORS.map((o) => (
                <button
                  key={o.op}
                  type="button"
                  className="block w-full text-left px-3 py-1.5 text-xs rounded-lg hover:bg-[var(--quant-surface)] transition-colors text-[var(--quant-fg)]"
                  onClick={() => insertOp(o.op)}
                >
                  {o.label}
                </button>
              ))}
            </div>
            <div className="text-xs text-[var(--quant-muted)] mt-3">
              使用 <code>$close</code>, <code>$volume</code> 等获取基础行情字段
            </div>
          </div>

          <div className="quant-card">
            <div className="text-sm font-bold mb-3">实验技巧</div>
            <ul className="space-y-2 text-xs text-[var(--quant-muted)]">
              {HINTS.map((h, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-[var(--quant-accent)] mt-0.5">•</span>
                  <span>{h}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
