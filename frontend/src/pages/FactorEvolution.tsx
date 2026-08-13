import { useState, useEffect, useRef, useCallback } from "react";
import { Link } from "react-router-dom";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { DemoBanner } from "../components/DemoBanner";
import { fetchFactorLineage, evolveFactor, submitFactorToVault } from "../lib/api";
import { DEMO_FACTOR_EVOLUTION } from "../lib/demoCatalog";

type Node = {
  id: string;
  factor_id?: string;
  name?: string;
  type?: string;
  ic?: number;
  ic_proxy?: boolean;
  full_name?: string;
  experiment_id?: string;
  status?: string;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
};

type LinkEdge = { source: string; target: string };

const NODE_COLORS: Record<string, string> = {
  primitive: "#5aa7ff",
  derived: "#a855f7",
  composite: "#f59e0b",
};

const TYPE_LABELS: Record<string, string> = {
  primitive: "原始种子",
  derived: "衍生进化",
  composite: "复合因子",
};

export default function FactorEvolution() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [nodes, setNodes] = useState<Node[]>([]);
  const [links, setLinks] = useState<LinkEdge[]>([]);
  const [selected, setSelected] = useState<Node | null>(null);
  const [loading, setLoading] = useState(true);
  const [isDemo, setIsDemo] = useState(false);
  const [symbol, setSymbol] = useState("000001");
  const nodesRef = useRef<Node[]>([]);
  const animRef = useRef<number>(0);
  const dragRef = useRef<{ nodeId: string | null; offsetX: number; offsetY: number }>({ nodeId: null, offsetX: 0, offsetY: 0 });
  const panRef = useRef({ x: 0, y: 0, dragging: false, startX: 0, startY: 0 });
  const zoomRef = useRef(1);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchFactorLineage({ limit: 150 });
      const raw = data.nodes ?? [];
      const useDemo = !raw.length;
      const sourceNodes = useDemo ? DEMO_FACTOR_EVOLUTION.nodes : raw;
      const sourceLinks = useDemo ? DEMO_FACTOR_EVOLUTION.links : (data.links ?? []);
      const ns = sourceNodes.map((n, i) => ({
        ...n,
        x: 400 + Math.cos(i * 2.39996) * (100 + i * 3),
        y: 300 + Math.sin(i * 2.39996) * (80 + i * 2.5),
      }));
      setNodes(ns);
      setLinks(sourceLinks);
      setIsDemo(useDemo);
      nodesRef.current = ns;
    } catch {
      const ns = DEMO_FACTOR_EVOLUTION.nodes.map((n, i) => ({
        ...n,
        x: 400 + Math.cos(i * 2.39996) * (100 + i * 3),
        y: 300 + Math.sin(i * 2.39996) * (80 + i * 2.5),
      }));
      setNodes(ns);
      setLinks(DEMO_FACTOR_EVOLUTION.links);
      setIsDemo(true);
      nodesRef.current = ns;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  // Force simulation
  useEffect(() => {
    if (nodes.length === 0) return;
    const ns = nodesRef.current;
    const ls = links;

    function tick() {
      for (let i = 0; i < ns.length; i++) {
        const a = ns[i];
        if (dragRef.current.nodeId === a.id) continue;
        let fx = 0, fy = 0;
        // Repulsion
        for (let j = 0; j < ns.length; j++) {
          if (i === j) continue;
          const b = ns[j];
          const dx = (a.x ?? 0) - (b.x ?? 0);
          const dy = (a.y ?? 0) - (b.y ?? 0);
          const d = Math.sqrt(dx * dx + dy * dy) || 1;
          const f = 800 / (d * d);
          fx += (dx / d) * f;
          fy += (dy / d) * f;
        }
        // Attraction (links)
        for (const l of ls) {
          let other: Node | undefined;
          if (l.source === a.id) other = ns.find((n) => n.id === l.target);
          else if (l.target === a.id) other = ns.find((n) => n.id === l.source);
          if (other) {
            const dx = ((other.x ?? 0)) - (a.x ?? 0);
            const dy = ((other.y ?? 0)) - (a.y ?? 0);
            fx += dx * 0.005;
            fy += dy * 0.005;
          }
        }
        // Center gravity
        fx += (400 - (a.x ?? 0)) * 0.001;
        fy += (300 - (a.y ?? 0)) * 0.001;
        a.vx = ((a.vx ?? 0) + fx) * 0.85;
        a.vy = ((a.vy ?? 0) + fy) * 0.85;
        a.x = (a.x ?? 0) + (a.vx ?? 0);
        a.y = (a.y ?? 0) + (a.vy ?? 0);
      }
      animRef.current = requestAnimationFrame(tick);
    }
    animRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animRef.current);
  }, [nodes, links]);

  // Canvas rendering
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || nodes.length === 0) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const cvs = canvas;
    const context = ctx;
    const currentLinks = links;
    let raf: number;
    function draw() {
      const w = cvs.width;
      const h = cvs.height;
      const zoom = zoomRef.current;
      const pan = panRef.current;
      context.clearRect(0, 0, w, h);
      context.save();
      context.translate(pan.x, pan.y);
      context.scale(zoom, zoom);

      // Links
      context.strokeStyle = "rgba(255,255,255,0.12)";
      context.lineWidth = 1;
      for (const l of currentLinks) {
        const src = nodesRef.current.find((n) => n.id === l.source);
        const tgt = nodesRef.current.find((n) => n.id === l.target);
        if (src && tgt) {
          context.beginPath();
          context.moveTo(src.x ?? 0, src.y ?? 0);
          context.lineTo(tgt.x ?? 0, tgt.y ?? 0);
          context.stroke();
        }
      }

      // Nodes
      for (const n of nodesRef.current) {
        const color = NODE_COLORS[n.type ?? "primitive"] ?? "#999";
        const radius = n.id === selected?.id ? 10 : 7;
        context.beginPath();
        context.arc(n.x ?? 0, n.y ?? 0, radius, 0, Math.PI * 2);
        context.fillStyle = color;
        context.fill();
        if (n.id === selected?.id) {
          context.strokeStyle = "#fff";
          context.lineWidth = 2;
          context.stroke();
        }
      }

      context.restore();
      raf = requestAnimationFrame(draw);
    }
    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, [nodes, links, selected]);

  // Mouse interactions
  function getCanvasPos(e: React.MouseEvent<HTMLCanvasElement>) {
    const rect = canvasRef.current!.getBoundingClientRect();
    return {
      x: (e.clientX - rect.left - panRef.current.x) / zoomRef.current,
      y: (e.clientY - rect.top - panRef.current.y) / zoomRef.current,
    };
  }

  function findNodeAt(x: number, y: number): Node | null {
    for (const n of nodesRef.current) {
      const dx = (n.x ?? 0) - x;
      const dy = (n.y ?? 0) - y;
      if (dx * dx + dy * dy < 100) return n;
    }
    return null;
  }

  function onMouseDown(e: React.MouseEvent<HTMLCanvasElement>) {
    const pos = getCanvasPos(e);
    const node = findNodeAt(pos.x, pos.y);
    if (node) {
      dragRef.current = { nodeId: node.id, offsetX: pos.x - (node.x ?? 0), offsetY: pos.y - (node.y ?? 0) };
      setSelected(node);
    } else {
      panRef.current = { ...panRef.current, dragging: true, startX: e.clientX - panRef.current.x, startY: e.clientY - panRef.current.y };
    }
  }

  function onMouseMove(e: React.MouseEvent<HTMLCanvasElement>) {
    if (dragRef.current.nodeId) {
      const pos = getCanvasPos(e);
      const node = nodesRef.current.find((n) => n.id === dragRef.current.nodeId);
      if (node) {
        node.x = pos.x - dragRef.current.offsetX;
        node.y = pos.y - dragRef.current.offsetY;
      }
    } else if (panRef.current.dragging) {
      panRef.current.x = e.clientX - panRef.current.startX;
      panRef.current.y = e.clientY - panRef.current.startY;
    }
  }

  function onMouseUp() {
    dragRef.current = { nodeId: null, offsetX: 0, offsetY: 0 };
    panRef.current.dragging = false;
  }

  function onWheel(e: React.WheelEvent<HTMLCanvasElement>) {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    zoomRef.current = Math.max(0.2, Math.min(3, zoomRef.current * delta));
  }

  async function handleEvolve() {
    if (!selected?.factor_id) return;
    if (!confirm(`确定要对因子 ${selected.factor_id} 进行定向演化吗？`)) return;
    await evolveFactor(selected.factor_id);
  }

  async function handleSubmitVault() {
    if (!selected?.factor_id) return;
    await submitFactorToVault(selected.factor_id);
  }

  return (
    <div className="space-y-4">
      <PageQuickNav items={QUICK_NAV_PRESETS.factorEvolution} />
      <div>
        <h1 className="page-title">因子演化拓扑</h1>
        <p className="text-[var(--quant-muted)] text-sm mt-1">可视化因子的演化关系和继承链</p>
        <DemoBanner show={isDemo} />
      </div>

      <div className="flex gap-4">
        {/* Canvas */}
        <div className="flex-1 quant-card p-0 overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center h-96 text-[var(--quant-muted)]">加载中...</div>
          ) : (
            <canvas
              ref={canvasRef}
              width={800}
              height={500}
              className="w-full cursor-grab active:cursor-grabbing"
              onMouseDown={onMouseDown}
              onMouseMove={onMouseMove}
              onMouseUp={onMouseUp}
              onMouseLeave={onMouseUp}
              onWheel={onWheel}
            />
          )}
        </div>

        {/* Sidebar */}
        <div className="w-72 space-y-4">
          {/* Stats */}
          <div className="quant-card">
            <div className="text-sm font-bold mb-2">拓扑概览</div>
            <div className="grid grid-cols-2 gap-2 text-center text-sm">
              <div>
                <div className="mono font-bold">{nodes.length}</div>
                <div className="text-xs text-[var(--quant-muted)]">节点</div>
              </div>
              <div>
                <div className="mono font-bold">{links.length}</div>
                <div className="text-xs text-[var(--quant-muted)]">连接</div>
              </div>
            </div>
            <div className="flex gap-2 mt-3 text-[10px]">
              {Object.entries(NODE_COLORS).map(([type, color]) => (
                <span key={type} className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full" style={{ background: color }} />
                  {TYPE_LABELS[type]}
                </span>
              ))}
            </div>
          </div>

          {/* Selected Node */}
          {selected ? (
            <div className="quant-card space-y-3">
              <div className="text-sm font-bold">节点详情</div>
              <div className="space-y-2 text-sm">
                <div>
                  <span className="text-[var(--quant-muted)]">类型：</span>
                  <span className="badge-soft ml-1">{TYPE_LABELS[selected.type ?? "primitive"]}</span>
                </div>
                {selected.factor_id && (
                  <div>
                    <span className="text-[var(--quant-muted)]">因子：</span>
                    <Link to={`/factor/${selected.factor_id}`} className="text-[var(--quant-accent)] hover:underline">
                      {selected.factor_id}
                    </Link>
                  </div>
                )}
                {selected.experiment_id && (
                  <div>
                    <span className="text-[var(--quant-muted)]">实验：</span>
                    <span className="mono text-xs">{selected.experiment_id}</span>
                  </div>
                )}
                {selected.ic != null && (
                  <div>
                    <span className="text-[var(--quant-muted)]">IC：</span>
                    <span className="mono">{selected.ic.toFixed(4)}</span>
                    {selected.ic_proxy && <span className="text-[var(--quant-warn)] text-xs ml-1">(proxy)</span>}
                  </div>
                )}
                {selected.full_name && (
                  <div>
                    <span className="text-[var(--quant-muted)]">公式：</span>
                    <div className="mono text-xs break-all mt-1">{selected.full_name}</div>
                  </div>
                )}
              </div>
              <div className="flex gap-2">
                <button type="button" className="btn-brand !text-xs !px-3 !py-1.5" onClick={handleEvolve}>
                  定向演化
                </button>
                <button type="button" className="btn btn-ghost btn-xs" onClick={handleSubmitVault}>
                  提交入库
                </button>
              </div>
            </div>
          ) : (
            <div className="quant-card text-center text-sm text-[var(--quant-muted)] py-8">
              点击节点查看详情
            </div>
          )}

          {/* Backtest Input */}
          <div className="quant-card">
            <div className="text-sm font-bold mb-2">回测标的</div>
            <div className="flex gap-2">
              <input
                type="text"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                placeholder="6位代码"
                className="input input-bordered input-sm flex-1 bg-[var(--quant-surface)] border-[var(--quant-surface-border)]"
              />
              <Link
                to={`/backtest?factor=${selected?.factor_id ?? ""}&symbol=${symbol}`}
                className="btn btn-primary btn-sm"
              >
                回测
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
