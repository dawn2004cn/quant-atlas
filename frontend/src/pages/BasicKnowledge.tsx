import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { DemoBanner } from "../components/DemoBanner";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";
import { DEMO_BASIC_KNOWLEDGE } from "../lib/demoCatalog";

type KnowledgeHit = {
  id: string;
  source_type: string;
  title: string;
  snippet?: string;
  symbol?: string | null;
  published_at?: string | null;
  url?: string | null;
  score?: number;
  meta?: Record<string, unknown>;
};

type SearchPayload = {
  query?: string;
  symbol?: string | null;
  items?: KnowledgeHit[];
  count?: number;
  by_source?: Record<string, number>;
  note?: string;
  errors?: Record<string, string>;
};

const SOURCE_LABELS: Record<string, string> = {
  yanbao: "研报",
  news: "新闻",
  financial: "财报",
  industry_chain: "产业链",
  corpus: "基础知识",
};

const SOURCE_FILTERS = Object.keys(SOURCE_LABELS);

export function BasicKnowledgePage() {
  const [q, setQ] = useState("产业链");
  const [symbol, setSymbol] = useState("");
  const [sources, setSources] = useState<string[]>([...SOURCE_FILTERS]);
  const [submitted, setSubmitted] = useState({ q: "产业链", symbol: "", sources: SOURCE_FILTERS.join(",") });

  const swrKey = useMemo(
    () => ["knowledge-search", submitted.q, submitted.symbol, submitted.sources],
    [submitted],
  );

  const { data, error, isLoading, mutate } = useSWR(
    swrKey,
    () => {
      const params = new URLSearchParams();
      if (submitted.q) params.set("q", submitted.q);
      if (submitted.symbol) params.set("symbol", submitted.symbol);
      if (submitted.sources) params.set("sources", submitted.sources);
      params.set("limit", "40");
      return apiFetchV1<SearchPayload>(`/knowledge/search?${params}`);
    },
    { revalidateOnFocus: false, shouldRetryOnError: false },
  );

  const liveItems = data?.items ?? [];
  const isDemo = Boolean(error) || (!isLoading && !liveItems.length);
  const view = isDemo ? DEMO_BASIC_KNOWLEDGE : data!;
  const items = view.items ?? [];
  const bySource = view.by_source ?? {};

  function toggleSource(id: string) {
    setSources((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  function onSearch(e: React.FormEvent) {
    e.preventDefault();
    setSubmitted({
      q: q.trim(),
      symbol: symbol.trim().toUpperCase(),
      sources: (sources.length ? sources : SOURCE_FILTERS).join(","),
    });
  }

  if (isLoading && !items.length && !isDemo) return <PageSkeleton rows={5} />;

  return (
    <div className="mx-auto max-w-[960px] space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.knowledge} />
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-[11px] font-mono uppercase tracking-[0.18em] text-zinc-500">Basic Knowledge Base</div>
          <h1 className="mt-0.5 text-2xl font-bold tracking-tight text-zinc-100">基础知识库</h1>
          <p className="mt-1 text-sm text-zinc-500">
            聚合研报、财报摘要、新闻归档、产业链逻辑与内置语料（平台已接入源，非任意站点爬虫）。
          </p>
          <DemoBanner show={isDemo} />
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => void mutate()}
            className="rounded-lg px-3 py-1.5 text-xs text-zinc-300 ring-1 ring-zinc-700/60 hover:bg-zinc-800"
          >
            刷新
          </button>
          <Link
            to="/yanbao-hub"
            className="rounded-lg bg-emerald-500/15 px-3 py-1.5 text-xs font-semibold text-emerald-400 ring-1 ring-emerald-500/30"
          >
            研报中心
          </Link>
        </div>
      </div>

      <form onSubmit={onSearch} className="rounded-xl bg-zinc-900/50 p-4 ring-1 ring-zinc-800/50 space-y-3">
        <div className="grid gap-3 sm:grid-cols-[1fr_140px_auto]">
          <input
            className="w-full rounded-lg border border-zinc-700/60 bg-zinc-800/60 px-3 py-2 text-sm text-zinc-200"
            placeholder="关键词：产业链 / 财报 / 评级…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <input
            className="w-full rounded-lg border border-zinc-700/60 bg-zinc-800/60 px-3 py-2 font-mono text-sm text-zinc-200"
            placeholder="股票代码"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
          />
          <button
            type="submit"
            className="rounded-lg bg-emerald-500/15 px-4 py-2 text-sm font-semibold text-emerald-400 ring-1 ring-emerald-500/30"
          >
            搜索
          </button>
        </div>
        <div className="flex flex-wrap gap-2">
          {SOURCE_FILTERS.map((id) => {
            const on = sources.includes(id);
            return (
              <button
                key={id}
                type="button"
                onClick={() => toggleSource(id)}
                className={`rounded-lg px-2.5 py-1 text-xs ring-1 ${
                  on
                    ? "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30"
                    : "text-zinc-500 ring-zinc-700/50"
                }`}
              >
                {SOURCE_LABELS[id]}
              </button>
            );
          })}
        </div>
      </form>

      <div className="flex flex-wrap gap-2 font-mono text-[11px] text-zinc-500">
        {Object.entries(bySource).map(([k, n]) => (
          <span key={k} className="rounded bg-zinc-900/80 px-2 py-1 ring-1 ring-zinc-800/80">
            {SOURCE_LABELS[k] || k}:{n}
          </span>
        ))}
        {view.note ? <span className="text-zinc-600">{view.note}</span> : null}
      </div>

      <section className="rounded-xl bg-zinc-900/50 ring-1 ring-zinc-800/50 divide-y divide-zinc-800/80">
        {items.map((hit) => (
          <article key={hit.id} className="p-4">
            <div className="flex flex-wrap items-baseline gap-2">
              <span className="rounded bg-zinc-800 px-1.5 py-0.5 font-mono text-[10px] text-zinc-400">
                {SOURCE_LABELS[hit.source_type] || hit.source_type}
              </span>
              <h2 className="text-sm font-semibold text-zinc-100">{hit.title}</h2>
              {hit.symbol ? (
                <Link
                  className="font-mono text-xs text-emerald-400"
                  to={`/stock/${encodeURIComponent(hit.symbol)}?m=CN`}
                >
                  {hit.symbol}
                </Link>
              ) : null}
              {hit.score != null ? (
                <span className="ml-auto font-mono text-[10px] text-zinc-600">score {hit.score.toFixed?.(1) ?? hit.score}</span>
              ) : null}
            </div>
            {hit.snippet ? <p className="mt-2 text-sm leading-relaxed text-zinc-400">{hit.snippet}</p> : null}
            <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-zinc-600">
              {hit.published_at ? <span>{hit.published_at}</span> : null}
              {hit.url ? (
                <a className="text-emerald-500/80 hover:underline" href={hit.url} target="_blank" rel="noreferrer">
                  原文
                </a>
              ) : null}
            </div>
          </article>
        ))}
        {!items.length ? (
          <div className="p-8 text-center text-sm text-zinc-500">暂无命中，试试「产业链」或输入股票代码。</div>
        ) : null}
      </section>
    </div>
  );
}
