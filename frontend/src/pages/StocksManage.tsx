import { useState, useEffect } from "react";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { apiFetchV1 } from "../lib/api";

type Stock = {
  code: string;
  name: string;
  market: string;
  status: string;
};

export default function StocksManagePage() {
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [market, setMarket] = useState("CN");

  const load = async () => {
    try {
      setLoading(true);
      const res = await apiFetchV1<{ items?: Stock[] } | Stock[]>("/admin/stocks");
      setStocks(Array.isArray(res) ? res : res?.items ?? []);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const add = async () => {
    if (!code || !name) return;
    try {
      await apiFetchV1("/admin/stocks", {
        method: "POST",
        body: JSON.stringify({ code, name, market }),
      });
      setCode(""); setName(""); setMarket("CN");
      await load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const toggleStatus = async (s: Stock) => {
    const next = s.status === "active" ? "inactive" : "active";
    try {
      await apiFetchV1(`/admin/stocks/${s.code}`, {
        method: "PATCH",
        body: JSON.stringify({ status: next }),
      });
      await load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.stocksManage} />
      <div>
        <h1 className="page-title">股票管理</h1>
        <p className="text-sm text-slate-500 mt-1">管理员 - 股票池维护</p>
      </div>

      {error && <div className="alert alert-error text-sm">{error}<button type="button" className="btn btn-sm ml-2" onClick={() => setError(null)}>关闭</button></div>}

      <section className="quant-card">
        <h2 className="text-lg font-bold mb-4">添加股票</h2>
        <div className="flex flex-wrap gap-3 items-end">
          <div className="form-control flex-1 min-w-[120px]">
            <label className="label"><span className="label-text">代码</span></label>
            <input className="input input-bordered input-sm" value={code} onChange={(e) => setCode(e.target.value)} placeholder="000001" />
          </div>
          <div className="form-control flex-1 min-w-[120px]">
            <label className="label"><span className="label-text">名称</span></label>
            <input className="input input-bordered input-sm" value={name} onChange={(e) => setName(e.target.value)} placeholder="平安银行" />
          </div>
          <div className="form-control w-24">
            <label className="label"><span className="label-text">市场</span></label>
            <select className="select select-bordered select-sm" value={market} onChange={(e) => setMarket(e.target.value)}>
              <option>CN</option><option>HK</option><option>US</option>
            </select>
          </div>
          <button type="button" className="btn-brand text-sm py-2" onClick={add}>添加</button>
        </div>
      </section>

      <section className="quant-card">
        <h2 className="text-lg font-bold mb-4">股票列表</h2>
        {loading ? (
          <div className="skeleton skeleton-row"></div>
        ) : (
          <div className="overflow-x-auto">
            <table className="table w-full text-sm">
              <thead>
                <tr><th>代码</th><th>名称</th><th>市场</th><th>状态</th><th></th></tr>
              </thead>
              <tbody>
                {stocks.map((s, i) => (
                  <tr key={s.code ?? i}>
                    <td><code>{s.code}</code></td>
                    <td className="font-semibold">{s.name}</td>
                    <td><span className="badge badge-ghost">{s.market}</span></td>
                    <td><span className={`badge ${s.status === "active" ? "badge-success" : "badge-ghost"}`}>{s.status === "active" ? "启用" : "停用"}</span></td>
                    <td><button type="button" className="btn btn-ghost btn-xs" onClick={() => toggleStatus(s)}>{s.status === "active" ? "停用" : "启用"}</button></td>
                  </tr>
                ))}
                {stocks.length === 0 && <tr><td colSpan={5} className="text-center py-8 text-slate-500">暂无股票</td></tr>}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}