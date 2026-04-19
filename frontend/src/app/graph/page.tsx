"use client";

import {
  useState,
  useMemo,
  useRef,
  useEffect,
  useCallback,
  Component,
} from "react";
import type { ReactNode, ErrorInfo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Network,
  Search,
  X,
  ArrowUpRight,
  AlertTriangle,
  Building2,
  Users,
  GitBranch,
  Zap,
  Activity,
  TrendingUp,
  Eye,
  Layers,
  Box,
} from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import Lottie from "lottie-react";
import radarPulse from "../../../public/lottie/radar-pulse.json";

// ── Dynamic imports ──────────────────────────────────────────────────────────
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
});

// ForceGraph3D is optional — if the package isn't installed the button is hidden
let ForceGraph3D: any = null;
try {
  // Wrapped in try so build does not fail when package is absent
  ForceGraph3D = dynamic(
    () =>
      import("react-force-graph-3d").catch(() => {
        return { default: () => null };
      }),
    { ssr: false }
  );
} catch {
  ForceGraph3D = null;
}

// ── Error boundary ────────────────────────────────────────────────────────────
class GraphErrorBoundary extends Component<
  { children: ReactNode },
  { crashed: boolean }
> {
  state = { crashed: false };
  componentDidCatch(err: Error, info: ErrorInfo) {
    console.warn("[Graph] canvas error caught:", err, info);
  }
  static getDerivedStateFromError() {
    return { crashed: true };
  }
  render() {
    if (this.state.crashed) {
      return (
        <div className="flex items-center justify-center h-full">
          <div className="text-center space-y-3">
            <Activity size={32} className="text-indigo-400 mx-auto animate-pulse" />
            <p className="text-[11px] font-black text-gray-500 uppercase tracking-widest">
              Rechargement du graphe…
            </p>
            <button
              onClick={() => this.setState({ crashed: false })}
              className="text-[9px] font-black text-indigo-400 uppercase tracking-wider hover:text-indigo-300"
            >
              Réessayer
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

// ── Types ─────────────────────────────────────────────────────────────────────
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
  bodacc_recent?: boolean;
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

interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

interface GraphStats {
  nodes: number;
  links: number;
  companies: number;
  directors: number;
  cross_mandates: number;
  signals: number;
}

type FilterType = "all" | "company" | "director" | "internal" | "subsidiary";

// ── Constants ─────────────────────────────────────────────────────────────────
const NODE_COLORS = {
  company: "#6366f1",          // indigo-600
  company_bodacc: "#f43f5e",   // rose-500
  director: "#fbbf24",         // amber-400
  holding: "#a855f7",          // purple-500
  internal: "#6366f1",
  subsidiary: "#8b5cf6",
  default: "#64748b",
};

const FILTERS: {
  key: FilterType;
  label: string;
  icon: React.ReactNode;
  color: string;
}[] = [
  { key: "all", label: "Tout le réseau", icon: <Network size={13} />, color: "#ffffff" },
  { key: "company", label: "Cibles", icon: <Building2 size={13} />, color: "#10b981" },
  { key: "director", label: "Dirigeants", icon: <Users size={13} />, color: "#f59e0b" },
  { key: "internal", label: "Équipe EDR", icon: <Eye size={13} />, color: "#6366f1" },
  { key: "subsidiary", label: "Filiales", icon: <GitBranch size={13} />, color: "#8b5cf6" },
];

// ── Helpers ───────────────────────────────────────────────────────────────────
function hexToRgba(hex: string, alpha: number): string {
  const h = hex.replace("#", "");
  const r = parseInt(h.substring(0, 2), 16);
  const g = parseInt(h.substring(2, 4), 16);
  const b = parseInt(h.substring(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

function drawHexagon(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  r: number
) {
  ctx.beginPath();
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 3) * i - Math.PI / 6;
    const x = cx + r * Math.cos(angle);
    const y = cy + r * Math.sin(angle);
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }
  ctx.closePath();
}

function drawDiamond(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  r: number
) {
  ctx.beginPath();
  ctx.moveTo(cx, cy - r);
  ctx.lineTo(cx + r, cy);
  ctx.lineTo(cx, cy + r);
  ctx.lineTo(cx - r, cy);
  ctx.closePath();
}

// ── Score radar mini-chart ────────────────────────────────────────────────────
function ScoreRadarBars({
  score,
  signals_count,
  multi_mandats,
}: {
  score: number;
  signals_count?: number;
  multi_mandats?: boolean;
}) {
  const metrics = [
    {
      label: "Score global",
      value: score,
      max: 100,
      color: score >= 65 ? "#10b981" : score >= 45 ? "#f59e0b" : "#6366f1",
    },
    {
      label: "Signaux",
      value: Math.min((signals_count ?? 0) * 20, 100),
      max: 100,
      color: "#f43f5e",
    },
    {
      label: "Mandats",
      value: multi_mandats ? 100 : 0,
      max: 100,
      color: "#f97316",
    },
  ];

  return (
    <div className="space-y-2">
      {metrics.map((m) => (
        <div key={m.label}>
          <div className="flex justify-between mb-0.5">
            <span className="text-[8px] font-black text-gray-600 uppercase tracking-wider">
              {m.label}
            </span>
            <span className="text-[8px] font-bold" style={{ color: m.color }}>
              {m.value}
            </span>
          </div>
          <div className="h-1 rounded-full bg-white/5 overflow-hidden">
            <motion.div
              className="h-full rounded-full"
              style={{ backgroundColor: m.color }}
              initial={{ width: 0 }}
              animate={{ width: `${m.value}%` }}
              transition={{ duration: 0.6, ease: "easeOut" }}
            />
          </div>
        </div>
      ))}
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
  const [loading, setLoading] = useState(true);
  const [use3D, setUse3D] = useState(false);
  const [has3D, setHas3D] = useState(false);
  const fgRef = useRef<any>(null);
  // Global tick counter for animating BODACC link dash offset
  const tickRef = useRef<number>(0);
  const animFrameRef = useRef<number>(0);

  // Check if 3D package is available
  useEffect(() => {
    import("react-force-graph-3d")
      .then(() => setHas3D(true))
      .catch(() => setHas3D(false));
  }, []);

  // Tick animation loop for BODACC link animation
  useEffect(() => {
    const tick = () => {
      tickRef.current = (tickRef.current + 0.5) % 100;
      animFrameRef.current = requestAnimationFrame(tick);
    };
    animFrameRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animFrameRef.current);
  }, []);

  useEffect(() => {
    fetch("/api/graph")
      .then((r) => r.json())
      .then((d) => {
        setGraphData(d.data);
        setStats(d.stats);
        if (d.data.nodes.length > 3) {
          setSelectedNode(
            d.data.nodes.find((n: GraphNode) => n.type === "company") ||
              d.data.nodes[0]
          );
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const filteredData = useMemo(() => {
    let nodes = graphData.nodes;
    if (activeFilter !== "all") nodes = nodes.filter((n) => n.type === activeFilter);
    if (search)
      nodes = nodes.filter(
        (n) =>
          n.name.toLowerCase().includes(search.toLowerCase()) ||
          (n.company || "").toLowerCase().includes(search.toLowerCase()) ||
          (n.sector || "").toLowerCase().includes(search.toLowerCase())
      );
    const ids = new Set(nodes.map((n) => n.id));
    const links = graphData.links.filter(
      (l) =>
        ids.has(l.source as string) && ids.has(l.target as string)
    );
    return { nodes, links };
  }, [search, activeFilter, graphData]);

  // Compute director -> companies map for the detail panel
  const directorCompaniesMap = useMemo(() => {
    const map: Record<string, string[]> = {};
    graphData.links.forEach((l) => {
      const src =
        typeof l.source === "object" ? (l.source as GraphNode) : null;
      const tgt =
        typeof l.target === "object" ? (l.target as GraphNode) : null;
      // link type "dirigeant" from director -> company
      if (l.type === "dirigeant" || l.type === "directs") {
        const dirId =
          src && src.type === "director"
            ? src.id
            : tgt && tgt.type === "director"
            ? tgt.id
            : typeof l.source === "string"
            ? l.source
            : typeof l.target === "string"
            ? l.target
            : null;
        const compName =
          src && src.type === "company"
            ? src.name
            : tgt && tgt.type === "company"
            ? tgt.name
            : l.label || "";
        if (dirId && compName) {
          if (!map[dirId]) map[dirId] = [];
          if (!map[dirId].includes(compName)) map[dirId].push(compName);
        }
      }
    });
    return map;
  }, [graphData.links]);

  // ── Node canvas object ──────────────────────────────────────────────────────
  const nodeCanvasObject = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
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
        const t = Date.now() / 1000;

        // Resolve the canonical node color for this render
        let nodeColor: string;
        if (isDirector) {
          nodeColor = NODE_COLORS.director;
        } else if (isHolding) {
          nodeColor = NODE_COLORS.holding;
        } else if (isCompany && isBodacc) {
          nodeColor = NODE_COLORS.company_bodacc;
        } else if (isCompany) {
          nodeColor = NODE_COLORS.company;
        } else {
          nodeColor = node.color || NODE_COLORS.default;
        }

        // Outer glow
        if (isSelected || isHovered || (node.signals_count ?? 0) > 0) {
          const glowR = r * (isSelected ? 5 : isHovered ? 4 : 2.5);
          const grad = ctx.createRadialGradient(x, y, r * 0.5, x, y, glowR);
          grad.addColorStop(0, hexToRgba(nodeColor, 0.35));
          grad.addColorStop(1, hexToRgba(nodeColor, 0));
          ctx.beginPath();
          ctx.arc(x, y, glowR, 0, 2 * Math.PI);
          ctx.fillStyle = grad;
          ctx.fill();
        }

        // Pulsing ring for high-signal companies
        if (isCompany && (node.signals_count ?? 0) >= 2) {
          const pulse = r + 4 + Math.sin(t * 2.5) * 2;
          ctx.beginPath();
          ctx.arc(x, y, pulse, 0, 2 * Math.PI);
          ctx.strokeStyle = hexToRgba(nodeColor, 0.38);
          ctx.lineWidth = 1.5 / globalScale;
          ctx.stroke();
        }

        // Holding extra ring
        if (isHolding) {
          ctx.beginPath();
          ctx.arc(x, y, r + 4 / globalScale, 0, 2 * Math.PI);
          ctx.strokeStyle = hexToRgba(NODE_COLORS.holding, 0.25);
          ctx.lineWidth = 2 / globalScale;
          ctx.stroke();
        }

        // Selection ring
        if (isSelected) {
          ctx.beginPath();
          ctx.arc(x, y, r + 5 / globalScale, 0, 2 * Math.PI);
          ctx.strokeStyle = nodeColor;
          ctx.lineWidth = 2 / globalScale;
          ctx.stroke();
        }

        // ── Glow shadow via shadowBlur ────────────────────────────────────────
        ctx.save();
        ctx.shadowBlur = 15;
        ctx.shadowColor = nodeColor;

        // ── Draw shape ────────────────────────────────────────────────────────
        if (isDirector) {
          // Diamond
          drawDiamond(ctx, x, y, r);
          ctx.fillStyle = hexToRgba(nodeColor, 0.85);
          ctx.fill();
          ctx.strokeStyle = nodeColor;
          ctx.lineWidth = 1 / globalScale;
          ctx.stroke();
        } else if (isHolding) {
          // Hexagon
          drawHexagon(ctx, x, y, r);
          const gHex = ctx.createRadialGradient(
            x - r * 0.3,
            y - r * 0.3,
            0,
            x,
            y,
            r
          );
          gHex.addColorStop(0, hexToRgba(NODE_COLORS.holding, 1));
          gHex.addColorStop(1, hexToRgba(NODE_COLORS.holding, 0.7));
          ctx.fillStyle = gHex;
          ctx.fill();
          ctx.strokeStyle = NODE_COLORS.holding;
          ctx.lineWidth = 1 / globalScale;
          ctx.stroke();
        } else {
          // Circle (company / internal / default)
          ctx.beginPath();
          ctx.arc(x, y, r, 0, 2 * Math.PI);
          if (isCompany || isInternal) {
            const g = ctx.createRadialGradient(
              x - r * 0.35,
              y - r * 0.35,
              0,
              x,
              y,
              r
            );
            g.addColorStop(0, nodeColor + "FF");
            g.addColorStop(1, nodeColor + "CC");
            ctx.fillStyle = g;
          } else {
            ctx.fillStyle = hexToRgba(nodeColor, 0.8);
          }
          ctx.fill();
        }

        ctx.restore(); // remove shadow

        // Score number inside company node
        if (isCompany && (node.score ?? 0) > 0 && globalScale > 0.7) {
          const fs = Math.max(5, Math.min(9, 7 / globalScale));
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillStyle = "#ffffff";
          ctx.font = `bold ${fs}px Inter, sans-serif`;
          ctx.fillText(String(node.score), x, y);
        }

        // Initials for internal team nodes
        if (isInternal && globalScale > 0.8) {
          const initials = node.name
            .split(" ")
            .map((w: string) => w[0])
            .join("")
            .slice(0, 2);
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

        // Age warning dot (red) for senior directors
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

        // BODACC alert dot (rose)
        if (isBodacc && !isDirector) {
          const dotR = Math.max(2.5, 3.5 / globalScale);
          ctx.beginPath();
          ctx.arc(x + r * 0.8, y + r * 0.8, dotR, 0, 2 * Math.PI);
          ctx.fillStyle = NODE_COLORS.company_bodacc;
          ctx.fill();
          ctx.strokeStyle = "#000";
          ctx.lineWidth = 0.8 / globalScale;
          ctx.stroke();
        }

        // Label below node
        if (globalScale > 0.55) {
          const fs = Math.max(7, Math.min(13, 10 / globalScale));
          ctx.textAlign = "center";
          ctx.textBaseline = "top";
          const label =
            node.name.length > 14 ? node.name.slice(0, 14) + "…" : node.name;

          // Shadow pass
          ctx.fillStyle = "rgba(0,0,0,0.8)";
          ctx.font = `${isCompany ? "bold " : ""}${fs}px Inter, sans-serif`;
          ctx.fillText(label, x + 0.5, y + r + 5 / globalScale + 0.5);

          ctx.fillStyle = isCompany
            ? "rgba(255,255,255,0.95)"
            : "rgba(255,255,255,0.7)";
          ctx.fillText(label, x, y + r + 5 / globalScale);
        }
      } catch {
        /* prevent canvas errors from propagating to React */
      }
    },
    [selectedNode, hoveredNode]
  );

  // ── Link canvas object ──────────────────────────────────────────────────────
  const linkCanvasObject = useCallback(
    (link: any, ctx: CanvasRenderingContext2D) => {
      try {
        const start = link.source;
        const end = link.target;
        if (
          !isFinite(start?.x) ||
          !isFinite(start?.y) ||
          !isFinite(end?.x) ||
          !isFinite(end?.y)
        )
          return;

        const isCrossMandate = link.type === "cross_mandate";
        const isDirigeant =
          link.type === "dirigeant" || link.type === "directs";
        const isHolding = link.type === "holding";
        const isBodacc = link.type === "bodacc";
        const isSubsidiary = link.type === "subsidiary";

        ctx.beginPath();
        ctx.moveTo(start.x, start.y);
        ctx.lineTo(end.x, end.y);

        if (isBodacc) {
          // Animated amber dashed line
          const offset = tickRef.current;
          ctx.setLineDash([6, 4]);
          ctx.lineDashOffset = -offset;
          ctx.strokeStyle = "rgba(251,191,36,0.7)";
          ctx.lineWidth = 1.8;
        } else if (isDirigeant) {
          // Dashed indigo line
          ctx.setLineDash([4, 5]);
          ctx.strokeStyle = "rgba(99,102,241,0.55)";
          ctx.lineWidth = 1.2;
        } else if (isHolding) {
          // Solid purple line
          ctx.setLineDash([]);
          ctx.strokeStyle = "rgba(168,85,247,0.65)";
          ctx.lineWidth = 1.8;
        } else if (isCrossMandate) {
          ctx.setLineDash([5, 4]);
          ctx.strokeStyle = "rgba(249,115,22,0.65)";
          ctx.lineWidth = 2;
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
        ctx.lineDashOffset = 0;

        // Link label at midpoint
        if (link.label) {
          const mx = (start.x + end.x) / 2;
          const my = (start.y + end.y) / 2;
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.font = "7px Inter, sans-serif";
          ctx.fillStyle = "rgba(156,163,175,0.6)";
          ctx.fillText(link.label, mx, my);
        }
      } catch {
        /* prevent canvas errors from propagating to React */
      }
    },
    []
  );

  // ── Utility helpers ─────────────────────────────────────────────────────────
  const typeLabel = (type: string) => {
    const labels: Record<string, string> = {
      internal: "Équipe EDR",
      company: "Cible M&A",
      director: "Dirigeant",
      subsidiary: "Filiale",
      holding: "Holding",
    };
    return labels[type] || type;
  };

  const scoreColor = (score?: number | null) => {
    if (!score) return "text-gray-500";
    if (score >= 65) return "text-emerald-400";
    if (score >= 45) return "text-amber-400";
    return "text-indigo-400";
  };

  // Director companies from link data (runtime resolved objects)
  const directorCompanies = useMemo(() => {
    if (!selectedNode || selectedNode.type !== "director") return [];
    // Try resolved link objects first
    const names: string[] = [];
    graphData.links.forEach((l) => {
      const src = l.source as any;
      const tgt = l.target as any;
      const isDir =
        (src?.id === selectedNode.id && tgt?.type === "company") ||
        (tgt?.id === selectedNode.id && src?.type === "company");
      if (isDir) {
        const compName =
          src?.id === selectedNode.id ? src?.name || tgt?.name : tgt?.name || src?.name;
        if (compName && !names.includes(compName)) names.push(compName);
      }
    });
    // Fallback to the precomputed string-id map
    if (names.length === 0) {
      return directorCompaniesMap[selectedNode.id] || [];
    }
    return names;
  }, [selectedNode, graphData.links, directorCompaniesMap]);

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div
      className="flex flex-col h-[calc(100dvh-4rem)] pb-3 overflow-hidden gap-3"
      style={{ touchAction: "none" }}
    >
      {/* ── Header ── */}
      <header className="shrink-0 flex flex-col lg:flex-row lg:items-center justify-between gap-2 pt-2 px-1">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shrink-0">
            <Network size={18} className="text-indigo-400" />
          </div>
          <div>
            <h1 className="text-lg sm:text-2xl font-black tracking-tight text-white leading-none">
              Intelligence Réseau
            </h1>
            <p className="text-gray-600 text-[9px] sm:text-[10px] font-bold uppercase tracking-widest mt-0.5">
              Cartographie M&amp;A propriétaire
            </p>
          </div>
        </div>

        {/* ── Stats strip ── */}
        {stats && (
          <div className="flex items-center gap-1.5 flex-wrap">
            {[
              {
                icon: <Layers size={11} />,
                value: stats.nodes,
                label: "Nœuds",
                color: "text-gray-400",
              },
              {
                icon: <Activity size={11} />,
                value: stats.links,
                label: "Liens",
                color: "text-gray-400",
              },
              {
                icon: <Building2 size={11} />,
                value: stats.companies,
                label: "Entreprises",
                color: "text-emerald-400",
              },
              {
                icon: <Users size={11} />,
                value: stats.directors,
                label: "Dirigeants",
                color: "text-amber-400",
              },
              {
                icon: <GitBranch size={11} />,
                value: stats.cross_mandates,
                label: "Multi-mandats",
                color: "text-orange-400",
              },
              {
                icon: <Zap size={11} />,
                value: stats.signals,
                label: "Signaux BODACC",
                color: "text-red-400",
              },
            ].map((s) => (
              <div
                key={s.label}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-white/4 backdrop-blur-xl border border-white/8 shadow-[inset_0_1px_0_rgba(255,255,255,0.07)]"
              >
                <span className={s.color}>{s.icon}</span>
                <span className="text-white font-black text-xs">{s.value}</span>
                <span className="text-gray-600 text-[8px] font-black uppercase tracking-wider hidden sm:block">
                  {s.label}
                </span>
              </div>
            ))}
          </div>
        )}
      </header>

      {/* ── Main: Graph + Panel ── */}
      <div className="flex-1 flex gap-3 min-h-0">
        {/* ── Graph canvas ── */}
        <div className="flex-1 rounded-3xl bg-[#030305] border border-white/[0.06] relative overflow-hidden shadow-[0_8px_80px_rgba(0,0,0,0.9)]">

          {/* Top controls row */}
          <div className="absolute top-3 left-3 right-3 z-10 flex items-center gap-2 flex-wrap">
            {/* Search */}
            <div className="relative flex-1 min-w-[140px] max-w-[220px]">
              <Search
                size={13}
                className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-600"
              />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Rechercher..."
                className="w-full bg-black/60 backdrop-blur-xl border border-white/10 rounded-xl py-1.5 pl-8 pr-3 text-xs text-gray-200 placeholder-gray-600 outline-none focus:border-indigo-500/40 transition-all"
              />
            </div>

            {/* Filter tabs */}
            <div className="flex items-center gap-1 bg-black/50 backdrop-blur-xl border border-white/8 rounded-2xl p-1">
              {FILTERS.map((f) => (
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
                  <span
                    style={
                      activeFilter === f.key ? { color: f.color } : { opacity: 0.4 }
                    }
                  >
                    {f.icon}
                  </span>
                  <span className="hidden md:block">{f.label}</span>
                </button>
              ))}
            </div>

            {/* 3D toggle */}
            {has3D && (
              <button
                onClick={() => setUse3D((v) => !v)}
                title={use3D ? "Passer en 2D" : "Passer en 3D"}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-[9px] font-black uppercase tracking-wider transition-all duration-200 border ${
                  use3D
                    ? "bg-indigo-500/20 border-indigo-500/40 text-indigo-300"
                    : "bg-black/50 border-white/10 text-gray-500 hover:text-gray-300"
                }`}
              >
                <Box size={12} />
                <span className="hidden sm:block">{use3D ? "3D" : "2D"}</span>
              </button>
            )}
          </div>

          {/* ── Mini legend panel (bottom-left) ── */}
          <div
            className={`absolute bottom-3 left-3 z-10 flex-col gap-1.5 ${
              selectedNode ? "hidden lg:flex" : "flex"
            }`}
          >
            <div className="text-[7px] font-black text-gray-700 uppercase tracking-widest px-1 mb-0.5">
              Légende
            </div>

            {/* Entreprise */}
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-black/70 backdrop-blur-md border border-white/8 text-[8px] text-gray-400 font-bold uppercase tracking-wider">
              <div
                className="w-2.5 h-2.5 rounded-full shrink-0"
                style={{ backgroundColor: NODE_COLORS.company }}
              />
              Entreprise
            </div>

            {/* Dirigeant diamond */}
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-black/70 backdrop-blur-md border border-white/8 text-[8px] text-gray-400 font-bold uppercase tracking-wider">
              <svg width="11" height="11" viewBox="0 0 11 11" className="shrink-0">
                <polygon
                  points="5.5,1 10,5.5 5.5,10 1,5.5"
                  fill={NODE_COLORS.director}
                />
              </svg>
              Dirigeant
            </div>

            {/* Holding hexagon */}
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-black/70 backdrop-blur-md border border-white/8 text-[8px] text-gray-400 font-bold uppercase tracking-wider">
              <svg width="11" height="11" viewBox="0 0 11 11" className="shrink-0">
                <polygon
                  points="5.5,1 9.5,3.5 9.5,7.5 5.5,10 1.5,7.5 1.5,3.5"
                  fill={NODE_COLORS.holding}
                />
              </svg>
              Holding
            </div>

            {/* BODACC animated amber dashed */}
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-black/70 backdrop-blur-md border border-white/8 text-[8px] text-gray-400 font-bold uppercase tracking-wider">
              <svg width="18" height="4" viewBox="0 0 18 4" className="shrink-0">
                <line
                  x1="0"
                  y1="2"
                  x2="18"
                  y2="2"
                  stroke="#fbbf24"
                  strokeWidth="2"
                  strokeDasharray="5,3"
                />
              </svg>
              Lien BODACC
            </div>

            {/* Dirigeant indigo dashed */}
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-black/70 backdrop-blur-md border border-white/8 text-[8px] text-gray-400 font-bold uppercase tracking-wider">
              <svg width="18" height="4" viewBox="0 0 18 4" className="shrink-0">
                <line
                  x1="0"
                  y1="2"
                  x2="18"
                  y2="2"
                  stroke="#6366f1"
                  strokeWidth="2"
                  strokeDasharray="4,4"
                />
              </svg>
              Connexion dirigeant
            </div>
          </div>

          {/* Fit / zoom button */}
          <button
            onClick={() => fgRef.current?.zoomToFit?.(500, 40)}
            className="absolute bottom-3 right-3 z-10 w-8 h-8 rounded-xl bg-black/70 backdrop-blur-md border border-white/10 flex items-center justify-center text-gray-500 hover:text-white transition-colors"
          >
            <Activity size={14} />
          </button>

          {/* ── Graph or loading ── */}
          <div className="absolute inset-0">
            {loading ? (
              <div className="flex flex-col items-center justify-center h-full gap-6">
                <div className="w-32 h-32">
                  <Lottie animationData={radarPulse} loop />
                </div>
                <div className="space-y-1 text-center">
                  <p className="text-[11px] font-black text-indigo-400 uppercase tracking-[0.3em]">
                    Analyse du réseau
                  </p>
                  <p className="text-[9px] text-gray-600 font-medium">
                    Cartographie des connexions M&amp;A...
                  </p>
                </div>
              </div>
            ) : use3D && ForceGraph3D ? (
              <GraphErrorBoundary>
                <ForceGraph3D
                  ref={fgRef}
                  graphData={filteredData}
                  backgroundColor="#030305"
                  nodeLabel={() => ""}
                  onNodeClick={(node: any) => setSelectedNode(node)}
                  nodeColor={(node: any) =>
                    node.type === "director"
                      ? NODE_COLORS.director
                      : node.is_holding || node.type === "holding"
                      ? NODE_COLORS.holding
                      : node.bodacc_recent
                      ? NODE_COLORS.company_bodacc
                      : NODE_COLORS.company
                  }
                  linkColor={() => "rgba(255,255,255,0.12)"}
                  d3AlphaDecay={0.02}
                  d3VelocityDecay={0.3}
                  warmupTicks={60}
                  cooldownTicks={200}
                />
              </GraphErrorBoundary>
            ) : (
              <GraphErrorBoundary>
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
                  linkDirectionalParticles={(link: any) =>
                    link.type === "cross_mandate" ? 3 : 0
                  }
                  linkDirectionalParticleWidth={2}
                  linkDirectionalParticleColor={() => "#f97316"}
                  linkDirectionalParticleSpeed={0.005}
                  d3AlphaDecay={0.02}
                  d3VelocityDecay={0.3}
                  warmupTicks={60}
                  cooldownTicks={200}
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
              {/* Mobile close button */}
              <button
                onClick={() => setSelectedNode(null)}
                className="lg:hidden absolute top-4 right-4 p-1.5 rounded-xl bg-white/5 text-gray-500 hover:text-white"
              >
                <X size={14} />
              </button>

              {/* ── Identity ── */}
              <div className="flex items-start gap-3">
                <div
                  className="w-12 h-12 rounded-2xl flex items-center justify-center text-white font-black text-base shrink-0 shadow-lg"
                  style={{
                    background: `linear-gradient(135deg, ${
                      selectedNode.type === "director"
                        ? NODE_COLORS.director
                        : selectedNode.is_holding || selectedNode.type === "holding"
                        ? NODE_COLORS.holding
                        : selectedNode.bodacc_recent
                        ? NODE_COLORS.company_bodacc
                        : NODE_COLORS.company
                    }30, ${
                      selectedNode.type === "director"
                        ? NODE_COLORS.director
                        : selectedNode.is_holding || selectedNode.type === "holding"
                        ? NODE_COLORS.holding
                        : selectedNode.bodacc_recent
                        ? NODE_COLORS.company_bodacc
                        : NODE_COLORS.company
                    }10)`,
                    border: `1px solid ${
                      selectedNode.type === "director"
                        ? NODE_COLORS.director
                        : selectedNode.is_holding || selectedNode.type === "holding"
                        ? NODE_COLORS.holding
                        : selectedNode.bodacc_recent
                        ? NODE_COLORS.company_bodacc
                        : NODE_COLORS.company
                    }30`,
                  }}
                >
                  {selectedNode.type === "director" ? (
                    <Users
                      size={20}
                      style={{ color: NODE_COLORS.director }}
                    />
                  ) : selectedNode.type === "internal" ? (
                    <span style={{ color: NODE_COLORS.internal }}>
                      {selectedNode.name
                        .split(" ")
                        .map((w) => w[0])
                        .join("")
                        .slice(0, 2)}
                    </span>
                  ) : (
                    <Building2
                      size={20}
                      style={{
                        color: selectedNode.bodacc_recent
                          ? NODE_COLORS.company_bodacc
                          : NODE_COLORS.company,
                      }}
                    />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <h2 className="text-base font-black text-white tracking-tight leading-tight truncate">
                    {selectedNode.name}
                  </h2>
                  <p
                    className="text-[9px] font-black uppercase tracking-widest mt-0.5 truncate"
                    style={{
                      color:
                        selectedNode.type === "director"
                          ? NODE_COLORS.director
                          : selectedNode.is_holding || selectedNode.type === "holding"
                          ? NODE_COLORS.holding
                          : selectedNode.bodacc_recent
                          ? NODE_COLORS.company_bodacc
                          : NODE_COLORS.company,
                    }}
                  >
                    {typeLabel(selectedNode.type)}
                  </p>
                  {selectedNode.role && (
                    <p className="text-[10px] text-gray-500 font-medium mt-0.5 truncate">
                      {selectedNode.role}
                    </p>
                  )}
                  {selectedNode.siren && (
                    <p className="text-[9px] text-gray-600 font-mono mt-0.5">
                      SIREN {selectedNode.siren}
                    </p>
                  )}
                </div>
              </div>

              {/* ── BODACC flag ── */}
              {selectedNode.bodacc_recent && (
                <div className="flex items-center gap-2 p-3 rounded-2xl bg-rose-500/5 border border-rose-500/20">
                  <AlertTriangle size={14} className="text-rose-400 shrink-0" />
                  <div>
                    <div className="text-[9px] font-black text-rose-400 uppercase tracking-wider">
                      Publication BODACC récente
                    </div>
                    <div className="text-[10px] text-gray-500 mt-0.5">
                      Événement légal détecté sur cette cible
                    </div>
                  </div>
                </div>
              )}

              {/* ── Score + radar bars (company) ── */}
              {selectedNode.type === "company" && selectedNode.score != null && (
                <div className="p-3 rounded-2xl bg-white/4 border border-white/6 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-[8px] font-black text-gray-600 uppercase tracking-widest mb-0.5">
                        Score M&amp;A
                      </div>
                      <div className="text-[9px] font-black text-gray-500 uppercase">
                        {selectedNode.priority}
                      </div>
                    </div>
                    <div
                      className={`text-3xl font-black ${scoreColor(selectedNode.score)}`}
                    >
                      {selectedNode.score}
                      <span className="text-base text-gray-700">/100</span>
                    </div>
                  </div>
                  <ScoreRadarBars
                    score={selectedNode.score}
                    signals_count={selectedNode.signals_count}
                    multi_mandats={selectedNode.multi_mandats}
                  />
                </div>
              )}

              {/* ── Score (non-company) ── */}
              {selectedNode.type !== "company" && selectedNode.score != null && (
                <div className="flex items-center justify-between p-3 rounded-2xl bg-white/[0.04] border border-white/[0.06]">
                  <div>
                    <div className="text-[8px] font-black text-gray-600 uppercase tracking-widest mb-0.5">
                      Score M&amp;A
                    </div>
                    <div className="text-[9px] font-black text-gray-500 uppercase">
                      {selectedNode.priority}
                    </div>
                  </div>
                  <div
                    className={`text-3xl font-black ${scoreColor(selectedNode.score)}`}
                  >
                    {selectedNode.score}
                    <span className="text-base text-gray-700">/100</span>
                  </div>
                </div>
              )}

              {/* ── Director: companies list ── */}
              {selectedNode.type === "director" && (
                <div>
                  <div className="flex items-center gap-1.5 mb-2">
                    <Building2 size={11} className="text-amber-400" />
                    <span className="text-[9px] font-black text-gray-600 uppercase tracking-widest">
                      Entreprises dirigées
                      {directorCompanies.length > 0
                        ? ` (${directorCompanies.length})`
                        : ""}
                    </span>
                  </div>
                  {directorCompanies.length === 0 ? (
                    <p className="text-[10px] text-gray-600 italic">
                      Aucune entreprise associée dans le graphe courant
                    </p>
                  ) : (
                    <div className="space-y-1.5">
                      {directorCompanies.map((name, i) => (
                        <div
                          key={i}
                          className="flex items-center gap-2 p-2 rounded-xl bg-amber-500/5 border border-amber-500/10"
                        >
                          <div className="w-1 h-1 rounded-full bg-amber-400 shrink-0" />
                          <span className="text-[10px] text-gray-300 leading-snug">
                            {name}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* ── Director age ── */}
              {selectedNode.type === "director" &&
                (selectedNode.age ?? 0) > 0 && (
                  <div
                    className={`flex items-center gap-2 p-3 rounded-2xl border ${
                      (selectedNode.age ?? 0) >= 60
                        ? "bg-red-500/5 border-red-500/15"
                        : "bg-white/3 border-white/6"
                    }`}
                  >
                    <TrendingUp
                      size={14}
                      className={
                        (selectedNode.age ?? 0) >= 60
                          ? "text-red-400"
                          : "text-gray-500"
                      }
                    />
                    <div>
                      <span className="text-sm font-black text-white">
                        {selectedNode.age} ans
                      </span>
                      {(selectedNode.age ?? 0) >= 60 && (
                        <span className="ml-2 text-[9px] font-black text-red-400 uppercase tracking-wider">
                          Signal succession
                        </span>
                      )}
                    </div>
                  </div>
                )}

              {/* ── Multi-mandate badge ── */}
              {selectedNode.multi_mandats && (
                <div className="flex items-center gap-2 p-3 rounded-2xl bg-orange-500/5 border border-orange-500/15">
                  <GitBranch size={14} className="text-orange-400 shrink-0" />
                  <div>
                    <div className="text-[9px] font-black text-orange-400 uppercase tracking-wider">
                      Mandat croisé détecté
                    </div>
                    <div className="text-[10px] text-gray-500 mt-0.5">
                      Dirigeant présent dans plusieurs entreprises
                    </div>
                  </div>
                </div>
              )}

              {/* ── Company metadata ── */}
              {(selectedNode.city || selectedNode.sector || selectedNode.ca) && (
                <div className="space-y-1.5">
                  {selectedNode.sector && (
                    <div className="flex justify-between items-center py-1.5 border-b border-white/[0.04]">
                      <span className="text-[9px] font-black text-gray-600 uppercase tracking-widest">
                        Secteur
                      </span>
                      <span className="text-[10px] font-bold text-gray-300">
                        {selectedNode.sector}
                      </span>
                    </div>
                  )}
                  {selectedNode.city && (
                    <div className="flex justify-between items-center py-1.5 border-b border-white/[0.04]">
                      <span className="text-[9px] font-black text-gray-600 uppercase tracking-widest">
                        Ville
                      </span>
                      <span className="text-[10px] font-bold text-gray-300">
                        {selectedNode.city}
                      </span>
                    </div>
                  )}
                  {selectedNode.ca && selectedNode.ca !== "N/A" && (
                    <div className="flex justify-between items-center py-1.5 border-b border-white/[0.04]">
                      <span className="text-[9px] font-black text-gray-600 uppercase tracking-widest">
                        CA
                      </span>
                      <span className="text-[10px] font-bold text-emerald-400">
                        {selectedNode.ca}
                      </span>
                    </div>
                  )}
                  {selectedNode.ebitda && selectedNode.ebitda !== "N/A" && (
                    <div className="flex justify-between items-center py-1.5">
                      <span className="text-[9px] font-black text-gray-600 uppercase tracking-widest">
                        EBITDA
                      </span>
                      <span className="text-[10px] font-bold text-emerald-300">
                        {selectedNode.ebitda}
                      </span>
                    </div>
                  )}
                </div>
              )}

              {/* ── Signals ── */}
              {(selectedNode.signals_count ?? 0) > 0 &&
                (selectedNode.signals?.length ?? 0) > 0 && (
                  <div>
                    <div className="flex items-center gap-1.5 mb-2">
                      <AlertTriangle size={11} className="text-red-400" />
                      <span className="text-[9px] font-black text-gray-600 uppercase tracking-widest">
                        Signaux actifs ({selectedNode.signals_count})
                      </span>
                    </div>
                    <div className="space-y-1.5">
                      {(selectedNode.signals ?? []).slice(0, 4).map((sig, i) => (
                        <div
                          key={i}
                          className="flex items-start gap-2 p-2 rounded-xl bg-red-500/5 border border-red-500/10"
                        >
                          <div className="w-1 h-1 rounded-full bg-red-400 mt-1.5 shrink-0" />
                          <span className="text-[10px] text-gray-400 leading-snug">
                            {sig}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              {/* ── CTA: open company file ── */}
              {selectedNode.type === "company" && selectedNode.siren && (
                <Link
                  href={`/targets/${selectedNode.siren}`}
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
