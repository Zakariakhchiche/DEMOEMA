"use client";

import {
  useState, useMemo, useRef, useEffect, useCallback, Component,
} from "react";
import type { ReactNode, ErrorInfo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Network, Search, X, ArrowUpRight, AlertTriangle, Building2, Users,
  GitBranch, Zap, Activity, TrendingUp, Layers, ZoomIn, ZoomOut,
  Maximize2, Filter, ChevronRight, MapPin, BarChart2,
} from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import Lottie from "lottie-react";
import radarPulse from "../../../public/lottie/radar-pulse.json";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

// ── Error boundary ───────────────────────────────────────────────────────────
class GraphErrorBoundary extends Component<{ children: ReactNode }, { crashed: boolean }> {
  state = { crashed: false };
  componentDidCatch(err: Error, info: ErrorInfo) { console.warn("[Graph]", err, info); }
  static getDerivedStateFromError() { return { crashed: true }; }
  render() {
    if (this.state.crashed) return (
      <div className="flex items-center justify-center h-full gap-3 flex-col">
        <Activity size={28} className="text-indigo-400 animate-pulse" />
        <p className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Rechargement…</p>
        <button onClick={() => this.setState({ crashed: false })} className="text-[9px] font-black text-indigo-400 uppercase tracking-wider hover:text-indigo-300">Réessayer</button>
      </div>
    );
    return this.props.children;
  }
}

// ── Types ────────────────────────────────────────────────────────────────────
interface GraphNode {
  id: string; name: string; type: string; role: string; color: string;
  company?: string; score?: number | null; signals_count?: number;
  signals?: string[]; is_holding?: boolean; age?: number; age_signal?: boolean;
  multi_mandats?: boolean; sector?: string; city?: string; siren?: string;
  ca?: string; ebitda?: string; priority?: string; node_size?: number;
  bodacc_recent?: boolean; x?: number; y?: number;
}
interface GraphLink {
  source: string | GraphNode; target: string | GraphNode;
  label: string; value: number; type?: string; director?: string;
}
interface GraphData { nodes: GraphNode[]; links: GraphLink[]; }
interface GraphStats { nodes: number; links: number; companies: number; directors: number; cross_mandates: number; signals: number; }
type FilterType = "all" | "company" | "director" | "internal" | "subsidiary";
type PanelTab = "profil" | "connexions" | "signaux";

// ── Colors ───────────────────────────────────────────────────────────────────
const NODE_COLORS = {
  company: "#6366f1", company_bodacc: "#f43f5e", director: "#fbbf24",
  holding: "#a855f7", internal: "#6366f1", subsidiary: "#8b5cf6", default: "#64748b",
};

const SECTOR_COLORS: Record<string, string> = {
  "Industrie": "#3b82f6", "Distribution": "#10b981", "Services": "#8b5cf6",
  "Santé": "#ec4899", "Tech": "#06b6d4", "Immobilier": "#f59e0b",
  "Finance": "#6366f1", "Agroalimentaire": "#84cc16", "BTP": "#f97316",
};

function getSectorColor(sector?: string): string {
  if (!sector) return NODE_COLORS.company;
  for (const [key, color] of Object.entries(SECTOR_COLORS)) {
    if (sector.toLowerCase().includes(key.toLowerCase())) return color;
  }
  return NODE_COLORS.company;
}

// ── Helpers ──────────────────────────────────────────────────────────────────
function hexToRgba(hex: string, alpha: number): string {
  const h = hex.replace("#", "");
  return `rgba(${parseInt(h.slice(0,2),16)},${parseInt(h.slice(2,4),16)},${parseInt(h.slice(4,6),16)},${alpha})`;
}

function drawHexagon(ctx: CanvasRenderingContext2D, cx: number, cy: number, r: number) {
  ctx.beginPath();
  for (let i = 0; i < 6; i++) {
    const a = (Math.PI / 3) * i - Math.PI / 6;
    i === 0 ? ctx.moveTo(cx + r * Math.cos(a), cy + r * Math.sin(a)) : ctx.lineTo(cx + r * Math.cos(a), cy + r * Math.sin(a));
  }
  ctx.closePath();
}

function drawDiamond(ctx: CanvasRenderingContext2D, cx: number, cy: number, r: number) {
  ctx.beginPath();
  ctx.moveTo(cx, cy - r); ctx.lineTo(cx + r, cy);
  ctx.lineTo(cx, cy + r); ctx.lineTo(cx - r, cy);
  ctx.closePath();
}

// ── Score bar mini ───────────────────────────────────────────────────────────
function ScoreBar({ label, value, max = 100, color }: { label: string; value: number; max?: number; color: string }) {
  return (
    <div>
      <div className="flex justify-between mb-1">
        <span className="text-[8px] font-black text-gray-600 uppercase tracking-wider">{label}</span>
        <span className="text-[8px] font-bold" style={{ color }}>{value}</span>
      </div>
      <div className="h-1 rounded-full bg-white/5 overflow-hidden">
        <motion.div className="h-full rounded-full" style={{ backgroundColor: color }}
          initial={{ width: 0 }} animate={{ width: `${(value / max) * 100}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }} />
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function RelationshipGraph() {
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [stats, setStats] = useState<GraphStats | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState<FilterType>("all");
  const [focusMode, setFocusMode] = useState(false);
  const [activeTab, setActiveTab] = useState<PanelTab>("profil");
  const [loading, setLoading] = useState(true);
  const [showLegend, setShowLegend] = useState(false);
  const fgRef = useRef<any>(null);
  const tickRef = useRef<number>(0);
  const animFrameRef = useRef<number>(0);

  // BODACC link animation loop
  useEffect(() => {
    const tick = () => { tickRef.current = (tickRef.current + 0.5) % 100; animFrameRef.current = requestAnimationFrame(tick); };
    animFrameRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animFrameRef.current);
  }, []);

  useEffect(() => {
    fetch("/api/graph").then(r => r.json()).then(d => {
      setGraphData(d.data);
      setStats(d.stats);
      if (d.data.nodes.length > 3) {
        setSelectedNode(d.data.nodes.find((n: GraphNode) => n.type === "company") || d.data.nodes[0]);
      }
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  // Precompute neighbor set for focus mode
  const neighborIds = useMemo(() => {
    if (!selectedNode || !focusMode) return null;
    const ids = new Set<string>();
    ids.add(selectedNode.id);
    graphData.links.forEach(l => {
      const srcId = typeof l.source === "object" ? (l.source as GraphNode).id : l.source;
      const tgtId = typeof l.target === "object" ? (l.target as GraphNode).id : l.target;
      if (srcId === selectedNode.id) ids.add(tgtId);
      if (tgtId === selectedNode.id) ids.add(srcId);
    });
    return ids;
  }, [selectedNode, focusMode, graphData.links]);

  // Director -> companies map
  const directorCompaniesMap = useMemo(() => {
    const map: Record<string, { id: string; name: string; score?: number | null; siren?: string }[]> = {};
    graphData.links.forEach(l => {
      const src = l.source as any; const tgt = l.target as any;
      if (l.type === "dirigeant" || l.type === "directs") {
        const dirId = src?.type === "director" ? src.id : tgt?.type === "director" ? tgt.id : null;
        const comp = src?.type === "company" ? src : tgt?.type === "company" ? tgt : null;
        if (dirId && comp) {
          if (!map[dirId]) map[dirId] = [];
          if (!map[dirId].find(c => c.id === comp.id)) map[dirId].push({ id: comp.id, name: comp.name, score: comp.score, siren: comp.siren });
        }
      }
    });
    return map;
  }, [graphData.links]);

  const filteredData = useMemo(() => {
    let nodes = graphData.nodes;
    if (activeFilter !== "all") nodes = nodes.filter(n => n.type === activeFilter);
    if (search) nodes = nodes.filter(n =>
      n.name.toLowerCase().includes(search.toLowerCase()) ||
      (n.sector || "").toLowerCase().includes(search.toLowerCase()) ||
      (n.city || "").toLowerCase().includes(search.toLowerCase())
    );
    const ids = new Set(nodes.map(n => n.id));
    const links = graphData.links.filter(l => ids.has(l.source as string) && ids.has(l.target as string));
    return { nodes, links };
  }, [search, activeFilter, graphData]);

  // ── Node canvas ──────────────────────────────────────────────────────────────
  const nodeCanvasObject = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    try {
      const { x, y } = node;
      if (!isFinite(x) || !isFinite(y)) return;

      const r = node.node_size || 6;
      const isSelected = selectedNode?.id === node.id;
      const isHovered = hoveredNode?.id === node.id;
      const isCompany = node.type === "company";
      const isDirector = node.type === "director";
      const isHolding = node.is_holding || node.type === "holding";
      const isInternal = node.type === "internal";
      const isBodacc = !!node.bodacc_recent;
      const isFaded = neighborIds != null && !neighborIds.has(node.id);

      const t = Date.now() / 1000;
      let nodeColor: string;
      if (isDirector) nodeColor = NODE_COLORS.director;
      else if (isHolding) nodeColor = NODE_COLORS.holding;
      else if (isCompany && isBodacc) nodeColor = NODE_COLORS.company_bodacc;
      else if (isCompany) nodeColor = getSectorColor(node.sector);
      else nodeColor = node.color || NODE_COLORS.default;

      const baseAlpha = isFaded ? 0.12 : 1;

      // Glow
      if ((isSelected || isHovered || (node.signals_count ?? 0) > 0) && !isFaded) {
        const glowR = r * (isSelected ? 5.5 : isHovered ? 4 : 2.5);
        const grad = ctx.createRadialGradient(x, y, r * 0.5, x, y, glowR);
        grad.addColorStop(0, hexToRgba(nodeColor, isSelected ? 0.45 : 0.25));
        grad.addColorStop(1, hexToRgba(nodeColor, 0));
        ctx.beginPath(); ctx.arc(x, y, glowR, 0, 2 * Math.PI);
        ctx.fillStyle = grad; ctx.fill();
      }

      // Pulse ring
      if (isCompany && (node.signals_count ?? 0) >= 2 && !isFaded) {
        const pulse = r + 4 + Math.sin(t * 2.5) * 2;
        ctx.beginPath(); ctx.arc(x, y, pulse, 0, 2 * Math.PI);
        ctx.strokeStyle = hexToRgba(nodeColor, 0.35); ctx.lineWidth = 1.5 / globalScale; ctx.stroke();
      }

      // Selection ring
      if (isSelected) {
        ctx.beginPath(); ctx.arc(x, y, r + 5 / globalScale, 0, 2 * Math.PI);
        ctx.strokeStyle = nodeColor; ctx.lineWidth = 2 / globalScale; ctx.stroke();
      }

      ctx.save();
      ctx.globalAlpha = baseAlpha;
      ctx.shadowBlur = isFaded ? 0 : 14;
      ctx.shadowColor = nodeColor;

      // Shape
      if (isDirector) {
        drawDiamond(ctx, x, y, r);
        ctx.fillStyle = hexToRgba(nodeColor, 0.85); ctx.fill();
        ctx.strokeStyle = nodeColor; ctx.lineWidth = 1 / globalScale; ctx.stroke();
      } else if (isHolding) {
        drawHexagon(ctx, x, y, r);
        const g = ctx.createRadialGradient(x - r * 0.3, y - r * 0.3, 0, x, y, r);
        g.addColorStop(0, hexToRgba(NODE_COLORS.holding, 1)); g.addColorStop(1, hexToRgba(NODE_COLORS.holding, 0.7));
        ctx.fillStyle = g; ctx.fill();
        ctx.strokeStyle = NODE_COLORS.holding; ctx.lineWidth = 1 / globalScale; ctx.stroke();
      } else {
        ctx.beginPath(); ctx.arc(x, y, r, 0, 2 * Math.PI);
        if (isCompany || isInternal) {
          const g = ctx.createRadialGradient(x - r * 0.35, y - r * 0.35, 0, x, y, r);
          g.addColorStop(0, nodeColor + "FF"); g.addColorStop(1, nodeColor + "CC");
          ctx.fillStyle = g;
        } else ctx.fillStyle = hexToRgba(nodeColor, 0.8);
        ctx.fill();
      }
      ctx.restore();

      ctx.save();
      ctx.globalAlpha = baseAlpha;
      // Score inside
      if (isCompany && (node.score ?? 0) > 0 && globalScale > 0.7) {
        ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillStyle = "#ffffff";
        ctx.font = `bold ${Math.max(5, Math.min(9, 7 / globalScale))}px Inter,sans-serif`;
        ctx.fillText(String(node.score), x, y);
      }
      if (isInternal && globalScale > 0.8) {
        const initials = node.name.split(" ").map((w: string) => w[0]).join("").slice(0, 2);
        ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillStyle = "#fff";
        ctx.font = `bold ${Math.max(6, 8 / globalScale)}px Inter,sans-serif`;
        ctx.fillText(initials, x, y);
      }
      // Dots
      const dotR = Math.max(2.5, 3.5 / globalScale);
      if (node.multi_mandats) {
        ctx.beginPath(); ctx.arc(x + r * 0.8, y - r * 0.8, dotR, 0, 2 * Math.PI);
        ctx.fillStyle = "#f97316"; ctx.fill();
        ctx.strokeStyle = "#000"; ctx.lineWidth = 0.8 / globalScale; ctx.stroke();
      }
      if (isDirector && node.age_signal) {
        ctx.beginPath(); ctx.arc(x - r * 0.8, y - r * 0.8, dotR, 0, 2 * Math.PI);
        ctx.fillStyle = "#ef4444"; ctx.fill();
        ctx.strokeStyle = "#000"; ctx.lineWidth = 0.8 / globalScale; ctx.stroke();
      }
      if (isBodacc && !isDirector) {
        ctx.beginPath(); ctx.arc(x + r * 0.8, y + r * 0.8, dotR, 0, 2 * Math.PI);
        ctx.fillStyle = NODE_COLORS.company_bodacc; ctx.fill();
        ctx.strokeStyle = "#000"; ctx.lineWidth = 0.8 / globalScale; ctx.stroke();
      }
      // Label
      if (globalScale > 0.55 && !isFaded) {
        const fs = Math.max(7, Math.min(13, 10 / globalScale));
        const label = node.name.length > 16 ? node.name.slice(0, 16) + "…" : node.name;
        ctx.textAlign = "center"; ctx.textBaseline = "top";
        ctx.fillStyle = "rgba(0,0,0,0.8)";
        ctx.font = `${isCompany ? "bold " : ""}${fs}px Inter,sans-serif`;
        ctx.fillText(label, x + 0.5, y + r + 5 / globalScale + 0.5);
        ctx.fillStyle = isCompany ? "rgba(255,255,255,0.95)" : "rgba(255,255,255,0.65)";
        ctx.fillText(label, x, y + r + 5 / globalScale);
      }
      ctx.restore();
    } catch { /* canvas safety */ }
  }, [selectedNode, hoveredNode, neighborIds]);

  // ── Link canvas ──────────────────────────────────────────────────────────────
  const linkCanvasObject = useCallback((link: any, ctx: CanvasRenderingContext2D) => {
    try {
      const { source: s, target: t } = link;
      if (!isFinite(s?.x) || !isFinite(s?.y) || !isFinite(t?.x) || !isFinite(t?.y)) return;
      const isFaded = neighborIds != null && (!neighborIds.has(s.id) || !neighborIds.has(t.id));
      ctx.save();
      ctx.globalAlpha = isFaded ? 0.04 : 1;
      ctx.beginPath(); ctx.moveTo(s.x, s.y); ctx.lineTo(t.x, t.y);
      if (link.type === "bodacc") {
        ctx.setLineDash([6, 4]); ctx.lineDashOffset = -tickRef.current;
        ctx.strokeStyle = "rgba(251,191,36,0.85)"; ctx.lineWidth = 2;
      } else if (link.type === "dirigeant" || link.type === "directs") {
        ctx.setLineDash([5, 5]); ctx.strokeStyle = "rgba(99,102,241,0.75)"; ctx.lineWidth = 1.5;
      } else if (link.type === "holding") {
        ctx.setLineDash([]); ctx.strokeStyle = "rgba(168,85,247,0.80)"; ctx.lineWidth = 2;
      } else if (link.type === "cross_mandate") {
        ctx.setLineDash([5, 4]); ctx.strokeStyle = "rgba(249,115,22,0.80)"; ctx.lineWidth = 2.2;
      } else if (link.type === "subsidiary") {
        ctx.setLineDash([3, 5]); ctx.strokeStyle = "rgba(139,92,246,0.45)"; ctx.lineWidth = 1.2;
      } else {
        ctx.setLineDash([]); ctx.strokeStyle = "rgba(255,255,255,0.18)"; ctx.lineWidth = 1;
      }
      ctx.stroke();
      ctx.setLineDash([]); ctx.lineDashOffset = 0;
      ctx.restore();
    } catch { /* canvas safety */ }
  }, [neighborIds]);

  const typeLabel = (type: string) => ({ internal: "Équipe EDR", company: "Cible M&A", director: "Dirigeant", subsidiary: "Filiale", holding: "Holding" }[type] || type);
  const scoreColor = (s?: number | null) => !s ? "text-gray-500" : s >= 65 ? "text-emerald-400" : s >= 45 ? "text-amber-400" : "text-indigo-400";
  const nodeColor = (n: GraphNode) => n.type === "director" ? NODE_COLORS.director : n.is_holding || n.type === "holding" ? NODE_COLORS.holding : n.bodacc_recent ? NODE_COLORS.company_bodacc : getSectorColor(n.sector);

  const directorCompanies = useMemo(() => {
    if (!selectedNode || selectedNode.type !== "director") return [];
    const fromLinks = directorCompaniesMap[selectedNode.id] || [];
    if (fromLinks.length > 0) return fromLinks;
    const names: { id: string; name: string; score?: number | null; siren?: string }[] = [];
    graphData.links.forEach(l => {
      const src = l.source as any; const tgt = l.target as any;
      if ((src?.id === selectedNode.id && tgt?.type === "company") || (tgt?.id === selectedNode.id && src?.type === "company")) {
        const comp = src?.id === selectedNode.id ? tgt : src;
        if (comp && !names.find(c => c.id === comp.id)) names.push({ id: comp.id, name: comp.name, score: comp.score, siren: comp.siren });
      }
    });
    return names;
  }, [selectedNode, graphData.links, directorCompaniesMap]);

  // ── Render ───────────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-[calc(100dvh-4rem)] pb-3 overflow-hidden gap-3" style={{ touchAction: "none" }}>

      {/* ── Header ── */}
      <header className="shrink-0 flex flex-col lg:flex-row lg:items-center justify-between gap-3 pt-1 px-1">
        <div className="flex items-center gap-3">
          <div className="relative w-10 h-10 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shrink-0">
            <Network size={18} className="text-indigo-400" />
            <div className="absolute -top-1 -right-1 w-3 h-3 bg-emerald-500 rounded-full border-2 border-[#080810] animate-pulse" />
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-black tracking-tighter text-white leading-none uppercase italic">Graphe Intelligence</h1>
            <p className="text-gray-600 text-[9px] font-black uppercase tracking-[0.25em] mt-0.5">Cartographie M&amp;A · Réseau propriétaire</p>
          </div>
        </div>

        {/* Stats strip */}
        {stats && (
          <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-hide">
            {[
              { icon: <Building2 size={12} />, value: stats.companies, label: "Cibles", color: "#6366f1" },
              { icon: <Users size={12} />, value: stats.directors, label: "Dirigeants", color: "#fbbf24" },
              { icon: <GitBranch size={12} />, value: stats.cross_mandates, label: "Multi-mandats", color: "#f97316" },
              { icon: <Zap size={12} />, value: stats.signals, label: "Signaux", color: "#f43f5e" },
              { icon: <Layers size={12} />, value: stats.links, label: "Liens", color: "#8b5cf6" },
            ].map(s => (
              <div key={s.label} className="flex items-center gap-2 px-3 py-2 rounded-xl border border-white/8 bg-white/[0.03] backdrop-blur-xl shrink-0">
                <span style={{ color: s.color }}>{s.icon}</span>
                <span className="text-white font-black text-sm">{s.value}</span>
                <span className="text-gray-600 text-[8px] font-black uppercase tracking-wider hidden sm:block">{s.label}</span>
              </div>
            ))}
          </div>
        )}
      </header>

      {/* ── Body: Graph + Panel ── */}
      <div className="flex-1 flex gap-3 min-h-0">

        {/* ── Canvas container ── */}
        <div className="flex-1 rounded-3xl bg-[#020208] border border-white/[0.06] relative overflow-hidden shadow-[0_8px_80px_rgba(0,0,0,0.95),0_0_0_1px_rgba(99,102,241,0.05)]">

          {/* Top controls */}
          <div className="absolute top-3 left-3 right-3 z-10 flex items-center gap-2">
            {/* Search */}
            <div className="relative min-w-[130px] max-w-[200px]">
              <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-600" />
              <input value={search} onChange={e => setSearch(e.target.value)}
                placeholder="Rechercher…"
                className="w-full bg-black/70 backdrop-blur-xl border border-white/10 rounded-xl py-2 pl-8 pr-3 text-xs text-gray-200 placeholder-gray-700 outline-none focus:border-indigo-500/40 transition-all" />
            </div>

            {/* Filter tabs */}
            <div className="flex items-center gap-0.5 bg-black/60 backdrop-blur-xl border border-white/8 rounded-2xl p-1 flex-1 overflow-x-auto scrollbar-hide">
              {([
                { key: "all", label: "Tout", icon: <Network size={11} />, color: "#fff" },
                { key: "company", label: "Cibles", icon: <Building2 size={11} />, color: "#6366f1" },
                { key: "director", label: "Dirigeants", icon: <Users size={11} />, color: "#fbbf24" },
              ] as const).map(f => (
                <button key={f.key} onClick={() => setActiveFilter(f.key as FilterType)}
                  className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-[9px] font-black uppercase tracking-wider transition-all shrink-0 ${activeFilter === f.key ? "bg-white/10 text-white shadow-inner" : "text-gray-600 hover:text-gray-400"}`}
                  style={activeFilter === f.key ? { color: f.color } : {}}>
                  <span style={activeFilter === f.key ? { color: f.color } : { opacity: 0.4 }}>{f.icon}</span>
                  <span className="hidden sm:block">{f.label}</span>
                </button>
              ))}
            </div>

            {/* Focus mode toggle */}
            {selectedNode && (
              <button onClick={() => setFocusMode(v => !v)}
                className={`flex items-center gap-1.5 px-2.5 py-2 rounded-xl text-[9px] font-black uppercase tracking-wider border transition-all shrink-0 ${focusMode ? "bg-indigo-500/20 border-indigo-500/40 text-indigo-300" : "bg-black/60 border-white/10 text-gray-500 hover:text-gray-300"}`}>
                <Filter size={11} />
                <span className="hidden sm:block">Focus</span>
              </button>
            )}

            {/* Legend toggle */}
            <button onClick={() => setShowLegend(v => !v)}
              className="flex items-center gap-1.5 px-2.5 py-2 rounded-xl text-[9px] font-black uppercase tracking-wider border bg-black/60 border-white/10 text-gray-500 hover:text-gray-300 transition-all shrink-0">
              <BarChart2 size={11} />
            </button>
          </div>

          {/* Legend overlay */}
          <AnimatePresence>
            {showLegend && (
              <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
                className="absolute top-14 left-3 z-20 p-3 rounded-2xl bg-black/90 backdrop-blur-xl border border-white/10 flex flex-col gap-2">
                <div className="text-[7px] font-black text-gray-600 uppercase tracking-widest mb-1">Légende</div>
                {[
                  { shape: <div className="w-3 h-3 rounded-full" style={{ background: NODE_COLORS.company }} />, label: "Entreprise" },
                  { shape: <svg width="12" height="12"><polygon points="6,1 11,6 6,11 1,6" fill={NODE_COLORS.director} /></svg>, label: "Dirigeant" },
                  { shape: <svg width="12" height="12"><polygon points="6,1 10,3.5 10,8.5 6,11 2,8.5 2,3.5" fill={NODE_COLORS.holding} /></svg>, label: "Holding" },
                  { shape: <div className="w-3 h-3 rounded-full" style={{ background: NODE_COLORS.company_bodacc }} />, label: "Alerte BODACC" },
                ].map(l => (
                  <div key={l.label} className="flex items-center gap-2 text-[9px] text-gray-400 font-bold uppercase tracking-wider">
                    <div className="shrink-0">{l.shape}</div> {l.label}
                  </div>
                ))}
                <div className="border-t border-white/8 pt-2 mt-1 flex flex-col gap-1.5">
                  {[
                    { color: "#fbbf24", dash: true, label: "Lien BODACC" },
                    { color: "#6366f1", dash: true, label: "Dirigeant" },
                    { color: "#a855f7", dash: false, label: "Holding" },
                    { color: "#f97316", dash: true, label: "Multi-mandat" },
                  ].map(l => (
                    <div key={l.label} className="flex items-center gap-2 text-[9px] text-gray-400 font-bold uppercase tracking-wider">
                      <svg width="18" height="4"><line x1="0" y1="2" x2="18" y2="2" stroke={l.color} strokeWidth="2" strokeDasharray={l.dash ? "5,3" : "0"} /></svg>
                      {l.label}
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Zoom controls */}
          <div className="absolute bottom-3 right-3 z-10 flex flex-col gap-1.5">
            <button onClick={() => fgRef.current?.zoom?.((fgRef.current?.zoom?.() || 1) * 1.3, 200)}
              className="w-8 h-8 rounded-xl bg-black/70 backdrop-blur-md border border-white/10 flex items-center justify-center text-gray-500 hover:text-white transition-colors">
              <ZoomIn size={14} />
            </button>
            <button onClick={() => fgRef.current?.zoom?.((fgRef.current?.zoom?.() || 1) * 0.7, 200)}
              className="w-8 h-8 rounded-xl bg-black/70 backdrop-blur-md border border-white/10 flex items-center justify-center text-gray-500 hover:text-white transition-colors">
              <ZoomOut size={14} />
            </button>
            <button onClick={() => fgRef.current?.zoomToFit?.(500, 40)}
              className="w-8 h-8 rounded-xl bg-black/70 backdrop-blur-md border border-white/10 flex items-center justify-center text-gray-500 hover:text-white transition-colors">
              <Maximize2 size={13} />
            </button>
          </div>

          {/* Focus mode indicator */}
          {focusMode && selectedNode && (
            <div className="absolute bottom-3 left-3 z-10 flex items-center gap-2 px-3 py-1.5 rounded-xl bg-indigo-500/15 border border-indigo-500/30 text-indigo-300 text-[9px] font-black uppercase tracking-widest">
              <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
              Focus: {selectedNode.name.slice(0, 18)}
              <button onClick={() => setFocusMode(false)} className="text-gray-500 hover:text-white ml-1"><X size={10} /></button>
            </div>
          )}

          {/* Graph */}
          <div className="absolute inset-0">
            {loading ? (
              <div className="flex flex-col items-center justify-center h-full gap-5">
                <div className="w-28 h-28"><Lottie animationData={radarPulse} loop /></div>
                <div className="space-y-1 text-center">
                  <p className="text-[11px] font-black text-indigo-400 uppercase tracking-[0.3em]">Analyse du réseau</p>
                  <p className="text-[9px] text-gray-600">Cartographie des connexions M&amp;A…</p>
                </div>
              </div>
            ) : (
              <GraphErrorBoundary>
                <ForceGraph2D
                  ref={fgRef}
                  graphData={filteredData}
                  backgroundColor="#020208"
                  nodeLabel={() => ""}
                  nodeCanvasObject={nodeCanvasObject}
                  linkCanvasObject={linkCanvasObject}
                  onNodeClick={(node: any) => {
                    setSelectedNode(node);
                    setActiveTab("profil");
                    if (focusMode) setFocusMode(true);
                  }}
                  onNodeHover={(node: any) => setHoveredNode(node)}
                  onBackgroundClick={() => { if (focusMode) setFocusMode(false); }}
                  nodeRelSize={1}
                  linkDirectionalParticles={(l: any) => l.type === "cross_mandate" ? 3 : 0}
                  linkDirectionalParticleWidth={2}
                  linkDirectionalParticleColor={() => "#f97316"}
                  linkDirectionalParticleSpeed={0.005}
                  d3AlphaDecay={0.02}
                  d3VelocityDecay={0.3}
                  warmupTicks={80}
                  cooldownTicks={300}
                />
              </GraphErrorBoundary>
            )}
          </div>
        </div>

        {/* ── Right detail panel ── */}
        <AnimatePresence mode="wait">
          {selectedNode && (
            <motion.aside
              key={selectedNode.id}
              initial={{ opacity: 0, x: 28, scale: 0.97 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 28, scale: 0.97 }}
              transition={{ type: "spring", stiffness: 380, damping: 28 }}
              className="fixed lg:relative bottom-3 left-3 right-3 lg:inset-0 w-auto lg:w-72 xl:w-80 shrink-0 rounded-3xl flex flex-col max-h-[62dvh] lg:max-h-full overflow-hidden z-[60] bg-[#080812]/98 backdrop-blur-3xl border border-white/8 shadow-[0_30px_100px_rgba(0,0,0,0.8),inset_0_1px_0_rgba(255,255,255,0.07)]"
            >
              {/* Top color bar */}
              <div className="h-0.5 w-full shrink-0" style={{ background: `linear-gradient(90deg, ${nodeColor(selectedNode)}80, transparent)` }} />

              {/* Header */}
              <div className="px-4 pt-4 pb-3 shrink-0">
                <div className="flex items-start gap-3">
                  <div className="w-11 h-11 rounded-2xl flex items-center justify-center shrink-0 shadow-lg"
                    style={{ background: `linear-gradient(135deg, ${nodeColor(selectedNode)}25, ${nodeColor(selectedNode)}08)`, border: `1px solid ${nodeColor(selectedNode)}30` }}>
                    {selectedNode.type === "director"
                      ? <Users size={18} style={{ color: NODE_COLORS.director }} />
                      : <Building2 size={18} style={{ color: nodeColor(selectedNode) }} />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h2 className="text-[13px] font-black text-white tracking-tight leading-tight line-clamp-2">{selectedNode.name}</h2>
                    <p className="text-[8px] font-black uppercase tracking-widest mt-0.5" style={{ color: nodeColor(selectedNode) }}>{typeLabel(selectedNode.type)}</p>
                    {selectedNode.role && <p className="text-[9px] text-gray-500 mt-0.5 truncate">{selectedNode.role}</p>}
                  </div>
                  <button onClick={() => setSelectedNode(null)} className="p-1.5 rounded-xl bg-white/5 text-gray-600 hover:text-white transition-colors shrink-0"><X size={13} /></button>
                </div>

                {/* Score pill */}
                {selectedNode.score != null && (
                  <div className="flex items-center gap-2 mt-3">
                    <div className={`text-2xl font-black ${scoreColor(selectedNode.score)}`}>{selectedNode.score}<span className="text-sm text-gray-700">/100</span></div>
                    <div className="flex-1">
                      <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
                        <motion.div className="h-full rounded-full" style={{ backgroundColor: (selectedNode.score ?? 0) >= 65 ? "#10b981" : (selectedNode.score ?? 0) >= 45 ? "#f59e0b" : "#6366f1" }}
                          initial={{ width: 0 }} animate={{ width: `${selectedNode.score}%` }} transition={{ duration: 0.5 }} />
                      </div>
                      <p className="text-[8px] font-black text-gray-600 uppercase tracking-wider mt-0.5">{selectedNode.priority || "—"}</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Tabs */}
              <div className="flex items-center gap-0.5 px-4 border-b border-white/5 shrink-0">
                {([
                  { id: "profil", label: "Profil" },
                  { id: "connexions", label: "Connexions" },
                  { id: "signaux", label: `Signaux${(selectedNode.signals_count ?? 0) > 0 ? ` (${selectedNode.signals_count})` : ""}` },
                ] as const).map(tab => (
                  <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                    className={`px-3 py-2.5 text-[9px] font-black uppercase tracking-widest border-b-2 transition-all ${activeTab === tab.id ? "border-indigo-500 text-indigo-300" : "border-transparent text-gray-600 hover:text-gray-400"}`}>
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Tab content */}
              <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-3">

                {/* ── PROFIL TAB ── */}
                {activeTab === "profil" && (
                  <>
                    {/* BODACC alert */}
                    {selectedNode.bodacc_recent && (
                      <div className="flex items-center gap-2 p-3 rounded-2xl bg-rose-500/6 border border-rose-500/20">
                        <AlertTriangle size={13} className="text-rose-400 shrink-0" />
                        <div>
                          <div className="text-[9px] font-black text-rose-400 uppercase tracking-wider">Publication BODACC récente</div>
                          <div className="text-[9px] text-gray-500 mt-0.5">Événement légal détecté</div>
                        </div>
                      </div>
                    )}

                    {/* Score bars */}
                    {selectedNode.type === "company" && selectedNode.score != null && (
                      <div className="p-3 rounded-2xl bg-white/[0.03] border border-white/6 space-y-2.5">
                        <ScoreBar label="Score global" value={selectedNode.score ?? 0} color={(selectedNode.score ?? 0) >= 65 ? "#10b981" : (selectedNode.score ?? 0) >= 45 ? "#f59e0b" : "#6366f1"} />
                        <ScoreBar label="Signaux M&A" value={Math.min((selectedNode.signals_count ?? 0) * 20, 100)} color="#f43f5e" />
                        {selectedNode.multi_mandats && <ScoreBar label="Mandats croisés" value={100} color="#f97316" />}
                      </div>
                    )}

                    {/* Metadata */}
                    <div className="space-y-0">
                      {[
                        { label: "Secteur", value: selectedNode.sector, icon: <BarChart2 size={11} /> },
                        { label: "Ville", value: selectedNode.city, icon: <MapPin size={11} /> },
                        { label: "SIREN", value: selectedNode.siren, icon: <Layers size={11} /> },
                        { label: "CA", value: selectedNode.ca && selectedNode.ca !== "N/A" ? selectedNode.ca : null, icon: <TrendingUp size={11} /> },
                        { label: "EBITDA", value: selectedNode.ebitda && selectedNode.ebitda !== "N/A" ? selectedNode.ebitda : null, icon: <Activity size={11} /> },
                        { label: "Âge dirigeant", value: selectedNode.age ? `${selectedNode.age} ans${(selectedNode.age ?? 0) >= 60 ? " ⚡ Succession" : ""}` : null, icon: <Users size={11} /> },
                      ].filter(r => r.value).map(row => (
                        <div key={row.label} className="flex items-center justify-between py-2 border-b border-white/[0.04]">
                          <div className="flex items-center gap-1.5 text-[8px] font-black text-gray-600 uppercase tracking-wider">
                            <span className="text-gray-700">{row.icon}</span>{row.label}
                          </div>
                          <span className={`text-[10px] font-bold max-w-[130px] text-right truncate ${row.label.includes("CA") || row.label.includes("EBITDA") ? "text-emerald-400" : row.label.includes("Âge") && (selectedNode.age ?? 0) >= 60 ? "text-amber-400" : "text-gray-300"}`}>
                            {row.value}
                          </span>
                        </div>
                      ))}
                    </div>

                    {/* Badges */}
                    <div className="flex flex-wrap gap-1.5">
                      {selectedNode.multi_mandats && (
                        <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-orange-500/10 border border-orange-500/20 text-[8px] font-black text-orange-400 uppercase tracking-wider">
                          <GitBranch size={9} /> Mandats croisés
                        </div>
                      )}
                      {selectedNode.age_signal && (
                        <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-red-500/10 border border-red-500/20 text-[8px] font-black text-red-400 uppercase tracking-wider">
                          <TrendingUp size={9} /> Signal succession
                        </div>
                      )}
                    </div>
                  </>
                )}

                {/* ── CONNEXIONS TAB ── */}
                {activeTab === "connexions" && (
                  <>
                    {selectedNode.type === "director" && directorCompanies.length > 0 ? (
                      <div className="space-y-2">
                        <p className="text-[8px] font-black text-gray-600 uppercase tracking-widest">Entreprises dirigées ({directorCompanies.length})</p>
                        {directorCompanies.map((c, i) => (
                          <div key={i} className="flex items-center justify-between p-2.5 rounded-xl bg-amber-500/5 border border-amber-500/10 group hover:border-amber-500/25 transition-all">
                            <div className="flex items-center gap-2 min-w-0">
                              <div className="w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />
                              <span className="text-[10px] text-gray-300 truncate">{c.name}</span>
                            </div>
                            {c.score != null && <span className={`text-[9px] font-black shrink-0 ml-2 ${scoreColor(c.score)}`}>{c.score}</span>}
                          </div>
                        ))}
                      </div>
                    ) : selectedNode.type === "company" ? (
                      <div className="space-y-2">
                        <p className="text-[8px] font-black text-gray-600 uppercase tracking-widest mb-2">Dirigeants liés</p>
                        {graphData.links.filter(l => {
                          const s = l.source as any; const t = l.target as any;
                          return (s?.id === selectedNode.id || t?.id === selectedNode.id) && (s?.type === "director" || t?.type === "director");
                        }).slice(0, 6).map((l, i) => {
                          const dir = (l.source as any)?.type === "director" ? l.source as GraphNode : l.target as GraphNode;
                          return (
                            <div key={i} className="flex items-center gap-2 p-2.5 rounded-xl bg-amber-500/5 border border-amber-500/10">
                              <div className="w-7 h-7 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center shrink-0">
                                <Users size={12} className="text-amber-400" />
                              </div>
                              <div className="min-w-0">
                                <div className="text-[10px] text-gray-200 font-bold truncate">{(dir as GraphNode).name || "—"}</div>
                                <div className="text-[8px] text-gray-600 uppercase">{(dir as GraphNode).role || l.label || "Dirigeant"}</div>
                              </div>
                              {(dir as GraphNode).age_signal && <AlertTriangle size={10} className="text-red-400 shrink-0" />}
                              {(dir as GraphNode).multi_mandats && <GitBranch size={10} className="text-orange-400 shrink-0" />}
                            </div>
                          );
                        })}
                        {graphData.links.filter(l => {
                          const s = l.source as any; const t = l.target as any;
                          return (s?.id === selectedNode.id || t?.id === selectedNode.id) && (s?.type === "director" || t?.type === "director");
                        }).length === 0 && <p className="text-[10px] text-gray-600 italic">Aucun dirigeant dans le graphe courant</p>}
                      </div>
                    ) : (
                      <p className="text-[10px] text-gray-600 italic">Aucune connexion à afficher</p>
                    )}

                    {/* Focus button */}
                    <button onClick={() => setFocusMode(v => !v)}
                      className={`w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-[9px] font-black uppercase tracking-widest border transition-all ${focusMode ? "bg-indigo-500/20 border-indigo-500/30 text-indigo-300" : "bg-white/4 border-white/8 text-gray-500 hover:text-white hover:border-white/20"}`}>
                      <Filter size={11} />
                      {focusMode ? "Désactiver le focus" : "Isoler ce nœud"}
                    </button>
                  </>
                )}

                {/* ── SIGNAUX TAB ── */}
                {activeTab === "signaux" && (
                  <>
                    {(selectedNode.signals?.length ?? 0) > 0 ? (
                      <div className="space-y-2">
                        {(selectedNode.signals ?? []).map((sig, i) => (
                          <div key={i} className="flex items-start gap-2 p-2.5 rounded-xl bg-red-500/5 border border-red-500/10">
                            <div className="w-1.5 h-1.5 rounded-full bg-red-400 mt-1.5 shrink-0" />
                            <span className="text-[10px] text-gray-300 leading-snug">{sig}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="flex flex-col items-center justify-center py-8 gap-2 text-center">
                        <Zap size={20} className="text-gray-700" />
                        <p className="text-[9px] font-black text-gray-600 uppercase tracking-widest">Aucun signal actif</p>
                      </div>
                    )}
                  </>
                )}
              </div>

              {/* Footer CTA */}
              {selectedNode.type === "company" && selectedNode.siren && (
                <div className="p-4 shrink-0 border-t border-white/5">
                  <Link href={`/targets/${selectedNode.siren}`}
                    className="w-full flex items-center justify-between py-3 px-4 rounded-2xl bg-gradient-to-r from-indigo-600/20 to-indigo-700/10 hover:from-indigo-600/30 border border-indigo-500/20 hover:border-indigo-500/35 text-white font-black text-[10px] uppercase tracking-widest transition-all group shadow-[0_4px_20px_rgba(99,102,241,0.1)]">
                    <span>Ouvrir le dossier</span>
                    <ChevronRight size={14} className="text-indigo-400 group-hover:translate-x-0.5 transition-transform" />
                  </Link>
                </div>
              )}
            </motion.aside>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
