"use client";

import { useState, useMemo, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Network, Search, X, ArrowUpRight, AlertTriangle, Building2, Users, GitBranch, Zap, Activity, TrendingUp, Eye } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import Lottie from "lottie-react";
import radarPulse from "../../../public/lottie/radar-pulse.json";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

interface GraphNode {
  id: string;
  name: string;
  type: string;
  role: string;
  color: string;
  company?: string;
  score?: number | null;
  signals_count?: number;
  signals?: string[];
  is_holding?: boolean;
  age?: number;
  age_signal?: boolean;
  multi_mandats?: boolean;
  sector?: string;
  city?: string;
  siren?: string;
  ca?: string;
  ebitda?: string;
  priority?: string;
  node_size?: number;
  x?: number;
  y?: number;
}

interface GraphLink {
  source: string | GraphNode;
  target: string | GraphNode;
  label: string;
  value: number;
  type?: string;
  director?: string;
}

interface GraphData { nodes: GraphNode[]; links: GraphLink[]; }
interface GraphStats { nodes: number; links: number; companies: number; directors: number; cross_mandates: number; signals: number; }

type FilterType = "all" | "company" | "director" | "internal" | "subsidiary";

const FILTERS: { key: FilterType; label: string; icon: React.ReactNode; color: string }[] = [
  { key: "all", label: "Tout le réseau", icon: <Network size={13} />, color: "#ffffff" },
  { key: "company", label: "Cibles", icon: <Building2 size={13} />, color: "#10b981" },
  { key: "director", label: "Dirigeants", icon: <Users size={13} />, color: "#f59e0b" },
  { key: "internal", label: "Équipe EDR", icon: <Eye size={13} />, color: "#6366f1" },
  { key: "subsidiary", label: "Filiales", icon: <GitBranch size={13} />, color: "#8b5cf6" },
];

export default function RelationshipGraph() {
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [stats, setStats] = useState<GraphStats | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState<FilterType>("all");
  const [loading, setLoading] = useState(true);
  const fgRef = useRef<any>(null);
  const animFrameRef = useRef<number>(0);
  const [tick, setTick] = useState(0);

  // Animation tick for pulsing nodes
  useEffect(() => {
    const animate = () => {
      setTick(t => t + 1);
      animFrameRef.current = requestAnimationFrame(animate);
    };
    animFrameRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animFrameRef.current);
  }, []);

  useEffect(() => {
    fetch("/api/graph")
      .then(r => r.json())
      .then(d => {
        setGraphData(d.data);
        setStats(d.stats);
        if (d.data.nodes.length > 3) setSelectedNode(d.data.nodes.find((n: GraphNode) => n.type === "company") || d.data.nodes[0]);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const filteredData = useMemo(() => {
    let nodes = graphData.nodes;
    if (activeFilter !== "all") nodes = nodes.filter(n => n.type === activeFilter);
    if (search) nodes = nodes.filter(n =>
      n.name.toLowerCase().includes(search.toLowerCase()) ||
      (n.company || "").toLowerCase().includes(search.toLowerCase()) ||
      (n.sector || "").toLowerCase().includes(search.toLowerCase())
    );
    const ids = new Set(nodes.map(n => n.id));
    const links = graphData.links.filter(l => ids.has(l.source as string) && ids.has(l.target as string));
    return { nodes, links };
  }, [search, activeFilter, graphData]);

  const nodeCanvasObject = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const { x, y } = node;
    const r = (node.node_size || 6);
    const isSelected = selectedNode?.id === node.id;
    const isHovered = hoveredNode?.id === node.id;
    const isCompany = node.type === "company";
    const isDirector = node.type === "director";
    const isInternal = node.type === "internal";
    const t = Date.now() / 1000;

    // Outer glow for selected / hovered
    if (isSelected || isHovered || node.signals_count > 0) {
      const glowR = r * (isSelected ? 5 : isHovered ? 4 : 2.5);
      const grad = ctx.createRadialGradient(x, y, r * 0.5, x, y, glowR);
      grad.addColorStop(0, node.color + "50");
      grad.addColorStop(1, node.color + "00");
      ctx.beginPath();
      ctx.arc(x, y, glowR, 0, 2 * Math.PI);
      ctx.fillStyle = grad;
      ctx.fill();
    }

    // Pulsing ring for priority companies
    if (isCompany && node.signals_count >= 2) {
      const pulse = r + 4 + Math.sin(t * 2.5) * 2;
      ctx.beginPath();
      ctx.arc(x, y, pulse, 0, 2 * Math.PI);
      ctx.strokeStyle = node.color + "60";
      ctx.lineWidth = 1.5 / globalScale;
      ctx.stroke();
    }

    // Holding double ring
    if (node.is_holding) {
      ctx.beginPath();
      ctx.arc(x, y, r + 4 / globalScale, 0, 2 * Math.PI);
      ctx.strokeStyle = node.color + "40";
      ctx.lineWidth = 2 / globalScale;
      ctx.stroke();
    }

    // Selection ring
    if (isSelected) {
      ctx.beginPath();
      ctx.arc(x, y, r + 5 / globalScale, 0, 2 * Math.PI);
      ctx.strokeStyle = node.color;
      ctx.lineWidth = 2 / globalScale;
      ctx.stroke();
    }

    // Main node
    ctx.beginPath();
    ctx.arc(x, y, r, 0, 2 * Math.PI);
    if (isCompany || isInternal) {
      const g = ctx.createRadialGradient(x - r * 0.35, y - r * 0.35, 0, x, y, r);
      g.addColorStop(0, node.color + "FF");
      g.addColorStop(1, node.color + "CC");
      ctx.fillStyle = g;
    } else {
      ctx.fillStyle = node.color + "CC";
    }
    ctx.fill();

    // Initials for internal team nodes
    if (isInternal && globalScale > 0.8) {
      const initials = node.name.split(" ").map((w: string) => w[0]).join("").slice(0, 2);
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillStyle = "#fff";
      ctx.font = `bold ${Math.max(6, 8 / globalScale)}px Inter, sans-serif`;
      ctx.fillText(initials, x, y);
    }

    // Cross-mandate dot (orange)
    if (node.multi_mandats) {
      const dotR = Math.max(2.5, 3.5 / globalScale);
      ctx.beginPath();
      ctx.arc(x + r * 0.8, y - r * 0.8, dotR, 0, 2 * Math.PI);
      ctx.fillStyle = "#f97316";
      ctx.fill();
      ctx.strokeStyle = "#000";
      ctx.lineWidth = 0.8 / globalScale;
      ctx.stroke();
    }

    // Age warning dot (red) for directors >= 60
    if (isDirector && node.age_signal) {
      const dotR = Math.max(2.5, 3.5 / globalScale);
      ctx.beginPath();
      ctx.arc(x - r * 0.8, y - r * 0.8, dotR, 0, 2 * Math.PI);
      ctx.fillStyle = "#ef4444";
      ctx.fill();
      ctx.strokeStyle = "#000";
      ctx.lineWidth = 0.8 / globalScale;
      ctx.stroke();
    }

    // Label
    if (globalScale > 0.55) {
      const fs = Math.max(7, Math.min(13, 10 / globalScale));
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      const label = node.name.length > 14 ? node.name.slice(0, 14) + "…" : node.name;

      // Text shadow
      ctx.fillStyle = "rgba(0,0,0,0.8)";
      ctx.font = `${isCompany ? "bold " : ""}${fs}px Inter, sans-serif`;
      ctx.fillText(label, x + 0.5, y + r + 5 / globalScale + 0.5);

      ctx.fillStyle = isCompany ? "rgba(255,255,255,0.95)" : "rgba(255,255,255,0.7)";
      ctx.fillText(label, x, y + r + 5 / globalScale);
    }
  }, [selectedNode, hoveredNode, tick]);

  const linkCanvasObject = useCallback((link: any, ctx: CanvasRenderingContext2D) => {
    const start = link.source;
    const end = link.target;
    if (!start?.x || !end?.x) return;

    const isCrossMandate = link.type === "cross_mandate";
    const isDirects = link.type === "directs";
    const isSubsidiary = link.type === "subsidiary";

    ctx.beginPath();
    ctx.moveTo(start.x, start.y);
    ctx.lineTo(end.x, end.y);

    if (isCrossMandate) {
      ctx.setLineDash([5, 4]);
      ctx.strokeStyle = "rgba(249,115,22,0.65)";
      ctx.lineWidth = 2;
    } else if (isDirects) {
      ctx.setLineDash([2, 4]);
      ctx.strokeStyle = "rgba(255,255,255,0.18)";
      ctx.lineWidth = 1;
    } else if (isSubsidiary) {
      ctx.setLineDash([3, 5]);
      ctx.strokeStyle = "rgba(139,92,246,0.3)";
      ctx.lineWidth = 1;
    } else {
      ctx.setLineDash([]);
      ctx.strokeStyle = "rgba(255,255,255,0.05)";
      ctx.lineWidth = 1;
    }
    ctx.stroke();
    ctx.setLineDash([]);
  }, []);

  const typeLabel = (type: string) => {
    const labels: Record<string, string> = { internal: "Équipe EDR", company: "Cible M&A", director: "Dirigeant", subsidiary: "Filiale" };
    return labels[type] || type;
  };

  const scoreColor = (score?: number | null) => {
    if (!score) return "text-gray-500";
    if (score >= 65) return "text-emerald-400";
    if (score >= 45) return "text-amber-400";
    return "text-indigo-400";
  };

  return (
    <div className="flex flex-col h-[calc(100dvh-4rem)] pb-3 overflow-hidden gap-3">

      {/* ── Header + Stats ── */}
      <header className="shrink-0 flex flex-col lg:flex-row lg:items-center justify-between gap-3 pt-3 px-1">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
            <Network size={20} className="text-indigo-400" />
          </div>
          <div>
            <h1 className="text-2xl font-black tracking-tight text-white leading-none">Intelligence Réseau</h1>
            <p className="text-gray-600 text-[10px] font-bold uppercase tracking-widest mt-0.5">Cartographie M&A propriétaire</p>
          </div>
        </div>

        {/* Stats glassmorphism pills */}
        {stats && (
          <div className="flex items-center gap-2 flex-wrap">
            {[
              { icon: <Building2 size={12} />, value: stats.companies, label: "Cibles", color: "text-emerald-400" },
              { icon: <Users size={12} />, value: stats.directors, label: "Dirigeants", color: "text-amber-400" },
              { icon: <GitBranch size={12} />, value: stats.cross_mandates, label: "Mandats croisés", color: "text-orange-400" },
              { icon: <Zap size={12} />, value: stats.signals, label: "Signaux", color: "text-red-400" },
            ].map(s => (
              <div key={s.label} className="flex items-center gap-2 px-3 py-2 rounded-2xl bg-white/[0.04] backdrop-blur-xl border border-white/8 shadow-[inset_0_1px_0_rgba(255,255,255,0.07)]">
                <span className={s.color}>{s.icon}</span>
                <span className="text-white font-black text-sm">{s.value}</span>
                <span className="text-gray-600 text-[9px] font-black uppercase tracking-wider hidden sm:block">{s.label}</span>
              </div>
            ))}
          </div>
        )}
      </header>

      {/* ── Main: Graph + Panel ── */}
      <div className="flex-1 flex gap-3 min-h-0">

        {/* Graph canvas */}
        <div className="flex-1 rounded-3xl bg-[#030305] border border-white/[0.06] relative overflow-hidden shadow-[0_8px_80px_rgba(0,0,0,0.9)]">

          {/* Top controls row */}
          <div className="absolute top-3 left-3 right-3 z-10 flex items-center gap-2 flex-wrap">
            {/* Search */}
            <div className="relative flex-1 min-w-[140px] max-w-[220px]">
              <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-600" />
              <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Rechercher..."
                className="w-full bg-black/60 backdrop-blur-xl border border-white/10 rounded-xl py-1.5 pl-8 pr-3 text-xs text-gray-200 placeholder-gray-600 outline-none focus:border-indigo-500/40 transition-all"
              />
            </div>

            {/* Glassmorphism filter tabs */}
            <div className="flex items-center gap-1 bg-black/50 backdrop-blur-xl border border-white/8 rounded-2xl p-1">
              {FILTERS.map(f => (
                <button
                  key={f.key}
                  onClick={() => setActiveFilter(f.key)}
                  className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-[9px] font-black uppercase tracking-wider transition-all duration-200 ${
                    activeFilter === f.key
                      ? "bg-white/10 text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.12)]"
                      : "text-gray-600 hover:text-gray-400"
                  }`}
                  style={activeFilter === f.key ? { color: f.color } : {}}
                >
                  <span style={activeFilter === f.key ? { color: f.color } : { opacity: 0.4 }}>{f.icon}</span>
                  <span className="hidden md:block">{f.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Legend bottom-left */}
          <div className="absolute bottom-3 left-3 z-10 flex flex-col gap-1.5">
            {[
              { color: "#10b981", label: "Cible prioritaire (≥65)" },
              { color: "#f59e0b", label: "Qualification (≥45)" },
              { color: "#6366f1", label: "Monitoring" },
              { color: "#ef4444", label: "Dirigeant senior (60+)" },
              { color: "#f97316", label: "Mandat croisé" },
            ].map(l => (
              <div key={l.label} className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-black/70 backdrop-blur-md border border-white/8 text-[8px] text-gray-500 font-bold uppercase tracking-wider">
                <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: l.color }} />
                {l.label}
              </div>
            ))}
          </div>

          {/* Fit button */}
          <button
            onClick={() => fgRef.current?.zoomToFit(500, 40)}
            className="absolute bottom-3 right-3 z-10 w-8 h-8 rounded-xl bg-black/70 backdrop-blur-md border border-white/10 flex items-center justify-center text-gray-500 hover:text-white transition-colors"
          >
            <Activity size={14} />
          </button>

          {/* Graph or Lottie loading */}
          <div className="absolute inset-0">
            {loading ? (
              <div className="flex flex-col items-center justify-center h-full gap-6">
                <div className="w-32 h-32">
                  <Lottie animationData={radarPulse} loop />
                </div>
                <div className="space-y-1 text-center">
                  <p className="text-[11px] font-black text-indigo-400 uppercase tracking-[0.3em]">Analyse du réseau</p>
                  <p className="text-[9px] text-gray-600 font-medium">Cartographie des connexions M&A...</p>
                </div>
              </div>
            ) : (
              <ForceGraph2D
                ref={fgRef}
                graphData={filteredData}
                backgroundColor="#030305"
                nodeLabel={() => ""}
                nodeCanvasObject={nodeCanvasObject}
                linkCanvasObject={linkCanvasObject}
                onNodeClick={(node: any) => setSelectedNode(node)}
                onNodeHover={(node: any) => setHoveredNode(node)}
                nodeRelSize={1}
                linkDirectionalParticles={(link: any) => link.type === "cross_mandate" ? 3 : 0}
                linkDirectionalParticleWidth={2}
                linkDirectionalParticleColor={(link: any) => "#f97316"}
                linkDirectionalParticleSpeed={0.005}
                d3AlphaDecay={0.02}
                d3VelocityDecay={0.3}
                warmupTicks={60}
                cooldownTicks={200}
              />
            )}
          </div>
        </div>

        {/* ── Detail Panel (glassmorphism) ── */}
        <AnimatePresence mode="wait">
          {selectedNode && (
            <motion.aside
              key={selectedNode.id}
              initial={{ opacity: 0, x: 24, scale: 0.97 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 24, scale: 0.97 }}
              transition={{ type: "spring", stiffness: 400, damping: 30 }}
              className="
                fixed lg:relative bottom-3 left-3 right-3 lg:bottom-0 lg:left-0 lg:right-0
                w-auto lg:w-72 xl:w-80 shrink-0
                rounded-3xl
                bg-white/[0.03] backdrop-blur-3xl
                border border-white/[0.08]
                shadow-[0_20px_80px_rgba(0,0,0,0.6),inset_0_1px_0_rgba(255,255,255,0.08)]
                p-5 flex flex-col gap-4
                max-h-[60dvh] lg:max-h-full overflow-y-auto
                z-[60] custom-scrollbar
              "
            >
              {/* Close on mobile */}
              <button onClick={() => setSelectedNode(null)} className="lg:hidden absolute top-4 right-4 p-1.5 rounded-xl bg-white/5 text-gray-500 hover:text-white">
                <X size={14} />
              </button>

              {/* Identity */}
              <div className="flex items-start gap-3">
                <div
                  className="w-12 h-12 rounded-2xl flex items-center justify-center text-white font-black text-base shrink-0 shadow-lg"
                  style={{ background: `linear-gradient(135deg, ${selectedNode.color}30, ${selectedNode.color}10)`, border: `1px solid ${selectedNode.color}30` }}
                >
                  {selectedNode.type === "director"
                    ? <Users size={20} style={{ color: selectedNode.color }} />
                    : selectedNode.type === "internal"
                    ? <span style={{ color: selectedNode.color }}>{selectedNode.name.split(" ").map(w => w[0]).join("").slice(0, 2)}</span>
                    : <Building2 size={20} style={{ color: selectedNode.color }} />
                  }
                </div>
                <div className="flex-1 min-w-0">
                  <h2 className="text-base font-black text-white tracking-tight leading-tight truncate">{selectedNode.name}</h2>
                  <p className="text-[9px] font-black uppercase tracking-widest mt-0.5 truncate" style={{ color: selectedNode.color }}>{typeLabel(selectedNode.type)}</p>
                  {selectedNode.role && (
                    <p className="text-[10px] text-gray-500 font-medium mt-0.5 truncate">{selectedNode.role}</p>
                  )}
                </div>
              </div>

              {/* Score */}
              {selectedNode.score != null && (
                <div className="flex items-center justify-between p-3 rounded-2xl bg-white/[0.04] border border-white/[0.06]">
                  <div>
                    <div className="text-[8px] font-black text-gray-600 uppercase tracking-widest mb-0.5">Score M&A</div>
                    <div className="text-[9px] font-black text-gray-500 uppercase">{selectedNode.priority}</div>
                  </div>
                  <div className={`text-3xl font-black ${scoreColor(selectedNode.score)}`}>
                    {selectedNode.score}
                    <span className="text-base text-gray-700">/100</span>
                  </div>
                </div>
              )}

              {/* Director age */}
              {selectedNode.type === "director" && (selectedNode.age ?? 0) > 0 && (
                <div className={`flex items-center gap-2 p-3 rounded-2xl border ${(selectedNode.age ?? 0) >= 60 ? "bg-red-500/5 border-red-500/15" : "bg-white/[0.03] border-white/[0.06]"}`}>
                  <TrendingUp size={14} className={(selectedNode.age ?? 0) >= 60 ? "text-red-400" : "text-gray-500"} />
                  <div>
                    <span className="text-sm font-black text-white">{selectedNode.age} ans</span>
                    {(selectedNode.age ?? 0) >= 60 && (
                      <span className="ml-2 text-[9px] font-black text-red-400 uppercase tracking-wider">Signal succession</span>
                    )}
                  </div>
                </div>
              )}

              {/* Multi-mandate badge */}
              {selectedNode.multi_mandats && (
                <div className="flex items-center gap-2 p-3 rounded-2xl bg-orange-500/5 border border-orange-500/15">
                  <GitBranch size={14} className="text-orange-400 shrink-0" />
                  <div>
                    <div className="text-[9px] font-black text-orange-400 uppercase tracking-wider">Mandat croisé détecté</div>
                    <div className="text-[10px] text-gray-500 mt-0.5">Dirigeant présent dans plusieurs entreprises</div>
                  </div>
                </div>
              )}

              {/* Company info */}
              {(selectedNode.city || selectedNode.sector) && (
                <div className="space-y-1.5">
                  {selectedNode.sector && (
                    <div className="flex justify-between items-center py-1.5 border-b border-white/[0.04]">
                      <span className="text-[9px] font-black text-gray-600 uppercase tracking-widest">Secteur</span>
                      <span className="text-[10px] font-bold text-gray-300">{selectedNode.sector}</span>
                    </div>
                  )}
                  {selectedNode.city && (
                    <div className="flex justify-between items-center py-1.5 border-b border-white/[0.04]">
                      <span className="text-[9px] font-black text-gray-600 uppercase tracking-widest">Ville</span>
                      <span className="text-[10px] font-bold text-gray-300">{selectedNode.city}</span>
                    </div>
                  )}
                  {selectedNode.ca && selectedNode.ca !== "N/A" && (
                    <div className="flex justify-between items-center py-1.5">
                      <span className="text-[9px] font-black text-gray-600 uppercase tracking-widest">CA</span>
                      <span className="text-[10px] font-bold text-emerald-400">{selectedNode.ca}</span>
                    </div>
                  )}
                </div>
              )}

              {/* Signals */}
              {(selectedNode.signals_count ?? 0) > 0 && (selectedNode.signals?.length ?? 0) > 0 && (
                <div>
                  <div className="flex items-center gap-1.5 mb-2">
                    <AlertTriangle size={11} className="text-red-400" />
                    <span className="text-[9px] font-black text-gray-600 uppercase tracking-widest">Signaux actifs ({selectedNode.signals_count})</span>
                  </div>
                  <div className="space-y-1.5">
                    {(selectedNode.signals ?? []).slice(0, 4).map((sig, i) => (
                      <div key={i} className="flex items-start gap-2 p-2 rounded-xl bg-red-500/5 border border-red-500/10">
                        <div className="w-1 h-1 rounded-full bg-red-400 mt-1.5 shrink-0" />
                        <span className="text-[10px] text-gray-400 leading-snug">{sig}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* CTA */}
              {selectedNode.type === "company" && selectedNode.siren && (
                <Link
                  href={`/targets/${selectedNode.id}`}
                  className="mt-auto w-full py-3 rounded-2xl bg-white/8 hover:bg-white/12 border border-white/10 hover:border-white/20 text-white font-black text-[10px] uppercase tracking-widest flex items-center justify-center gap-2 transition-all shadow-[inset_0_1px_0_rgba(255,255,255,0.1)]"
                >
                  Ouvrir le dossier <ArrowUpRight size={13} />
                </Link>
              )}
            </motion.aside>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
