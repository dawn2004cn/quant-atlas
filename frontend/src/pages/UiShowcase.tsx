import { useState } from "react";

export default function UiShowcase() {
  const [inputVal, setInputVal] = useState("");
  const [selectedOption, setSelectedOption] = useState("option1");
  const [checked, setChecked] = useState(false);
  const [count, setCount] = useState(0);

  const rows = Array.from({ length: 5 }, (_, i) => ({
    id: i + 1,
    name: `因子 ${String.fromCharCode(65 + i)}`,
    sharpe: (0.5 + Math.random() * 2).toFixed(2),
    ic: (Math.random() * 0.2).toFixed(3),
    turnover: `${(Math.random() * 30 + 10).toFixed(0)}%`,
  }));

  return (
    <div className="space-y-8">
      <div>
        <h1 className="page-title">UI 组件展示</h1>
        <p className="text-[var(--quant-muted)] text-sm mt-1">
          设计系统参考 — 所有可用组件与样式
        </p>
      </div>

      {/* Buttons */}
      <section>
        <h2 className="text-sm font-bold mb-3">按钮</h2>
        <div className="quant-card">
          <div className="flex flex-wrap items-center gap-3">
            <button type="button" className="btn-brand">主要按钮</button>
            <button type="button" className="btn-ghost">幽灵按钮</button>
            <button type="button" className="btn-ghost btn-sm">小幽灵</button>
            <button type="button" className="btn-brand" disabled>禁用状态</button>
          </div>
        </div>
      </section>

      {/* Buttons soft */}
      <section>
        <h2 className="text-sm font-bold mb-3">次要按钮</h2>
        <div className="quant-card flex flex-wrap gap-3">
          <button type="button" className="badge-soft">默认软标签</button>
          <button type="button" className="badge-soft bg-[var(--quant-accent)]/10 text-[var(--quant-accent)]">强调</button>
          <button type="button" className="badge-soft bg-[var(--quant-warn)]/10 text-[var(--quant-warn)]">警告</button>
          <button type="button" className="badge-soft bg-[var(--quant-danger)]/10 text-[var(--quant-danger)]">危险</button>
        </div>
      </section>

      {/* Cards */}
      <section>
        <h2 className="text-sm font-bold mb-3">卡片</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="quant-card">
            <div className="text-sm font-bold mb-2">默认卡片</div>
            <div className="text-xs text-[var(--quant-muted)]">标准白色卡片，带圆角和内边距。</div>
          </div>
          <div className="quant-card bg-[var(--quant-accent)]/5 border-[var(--quant-accent)]/20">
            <div className="text-sm font-bold mb-2">高亮卡片</div>
            <div className="text-xs text-[var(--quant-muted)]">带强调色背景的卡片，适合重点内容。</div>
          </div>
          <div className="quant-card bg-gradient-to-br from-[var(--quant-accent)]/10 to-transparent">
            <div className="text-sm font-bold mb-2">渐变卡片</div>
            <div className="text-xs text-[var(--quant-muted)]">带渐变背景的卡片。</div>
          </div>
        </div>
      </section>

      {/* Loading skeletons */}
      <section>
        <h2 className="text-sm font-bold mb-3">加载骨架</h2>
        <div className="quant-card space-y-3">
          <div className="flex items-center gap-3">
            <div className="skeleton h-10 w-10 rounded-full" />
            <div className="space-y-2 flex-1">
              <div className="skeleton h-4 w-3/4" />
              <div className="skeleton h-3 w-1/2" />
            </div>
          </div>
          <div className="skeleton h-6 w-full" />
          <div className="skeleton h-6 w-2/3" />
          <div className="flex gap-2">
            <div className="skeleton h-8 w-20" />
            <div className="skeleton h-8 w-20" />
          </div>
        </div>
      </section>

      {/* Gradient backgrounds */}
      <section>
        <h2 className="text-sm font-bold mb-3">渐变背景</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="quant-card bg-gradient-to-br from-[var(--quant-accent)]/15 to-[var(--quant-accent)]/5 min-h-[80px] flex items-center justify-center text-sm text-[var(--quant-muted)]">
            accent → accent/5
          </div>
          <div className="quant-card bg-gradient-to-br from-[var(--quant-accent)]/10 via-transparent to-[var(--quant-warn)]/10 min-h-[80px] flex items-center justify-center text-sm text-[var(--quant-muted)]">
            accent → warn
          </div>
          <div className="quant-card bg-gradient-to-t from-[var(--quant-surface-strong)]/50 to-transparent min-h-[80px] flex items-center justify-center text-sm text-[var(--quant-muted)]">
            surface → transparent
          </div>
        </div>
      </section>

      {/* Table */}
      <section>
        <h2 className="text-sm font-bold mb-3">表格</h2>
        <div className="quant-card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--quant-surface-border)] text-[var(--quant-muted)] text-xs uppercase">
                <th className="text-left py-2 px-3">#</th>
                <th className="text-left py-2 px-3">名称</th>
                <th className="text-right py-2 px-3">Sharpe</th>
                <th className="text-right py-2 px-3">IC</th>
                <th className="text-right py-2 px-3">换手率</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-b border-[var(--quant-surface-border)]/50 hover:bg-[var(--quant-surface)]/50 transition-colors">
                  <td className="py-2 px-3 mono text-xs">{r.id}</td>
                  <td className="py-2 px-3">{r.name}</td>
                  <td className="py-2 px-3 text-right mono">{r.sharpe}</td>
                  <td className="py-2 px-3 text-right mono">{r.ic}</td>
                  <td className="py-2 px-3 text-right mono">{r.turnover}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Form elements */}
      <section>
        <h2 className="text-sm font-bold mb-3">表单元素</h2>
        <div className="quant-card space-y-4">
          <div>
            <label className="block text-xs text-[var(--quant-muted)] mb-1">文本输入</label>
            <input
              type="text"
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              placeholder="输入文本..."
              className="w-full p-2.5 rounded-xl bg-[var(--quant-surface)] border border-[var(--quant-surface-border)] text-[var(--quant-fg)] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--quant-accent)]"
            />
          </div>
          <div>
            <label className="block text-xs text-[var(--quant-muted)] mb-1">下拉选择</label>
            <select
              value={selectedOption}
              onChange={(e) => setSelectedOption(e.target.value)}
              className="w-full p-2.5 rounded-xl bg-[var(--quant-surface)] border border-[var(--quant-surface-border)] text-[var(--quant-fg)] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--quant-accent)]"
            >
              <option value="option1">选项 1</option>
              <option value="option2">选项 2</option>
              <option value="option3">选项 3</option>
            </select>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="demo-checkbox"
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
              className="accent-[var(--quant-accent)]"
            />
            <label htmlFor="demo-checkbox" className="text-sm cursor-pointer">多选框示例</label>
          </div>
          <div className="flex items-center gap-3">
            <button type="button" className="btn-brand" onClick={() => setCount((c) => c + 1)}>+1</button>
            <button type="button" className="btn-ghost" onClick={() => setCount(0)}>重置</button>
            <span className="mono text-sm">{count}</span>
          </div>
        </div>
      </section>

      {/* Mono / text */}
      <section>
        <h2 className="text-sm font-bold mb-3">文本样式</h2>
        <div className="quant-card space-y-2">
          <div className="text-sm">默认正文文本</div>
          <div className="text-xs text-[var(--quant-muted)]">`text-[var(--quant-muted)]` — 辅助文本</div>
          <div className="mono text-sm">.mono — 等宽字体 123.456 ABC</div>
          <div className="text-[var(--quant-accent)] text-sm">强调色文本</div>
          <div className="text-[var(--quant-danger)] text-sm">危险/错误文本</div>
          <div className="text-[var(--quant-warn)] text-sm">警告文本</div>
        </div>
      </section>
    </div>
  );
}