"use client";

import { useState, useMemo, useRef, useEffect, useCallback, Component, Suspense } from "react";
import type { ReactNode, ErrorInfo } from "react";
import {
  Network, Search, X, AlertTriangle, Building2, Users,
  GitBranch, Zap, Activity, TrendingUp, Layers, ZoomIn, ZoomOut,
  Maximize2, Filter, ChevronRight, MapPin, BarChart2,
} from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

const M = { fontFamily: "'JetBrains Mono',monospace" } as const;
const S = { fontFamily: "Inter,sans-serif" } as const;

class GraphErrorBoundary extends Component<{ children: ReactNode }, { crashed: boolean }> {
  state = { crashed: false };
  componentDidCatch(e: Error, i: ErrorInfo) { console.warn("[Graph]", e, i); }
  static getDerivedStateFromError() { return { crashed: true }; }
  render() {
    if (this.state.crashed) return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", flexDirection: "column", gap: 12 }}>
        <Activity size={24} style={{ color: "#FF4500" }} />
        <span style={{ ...M, fontSize: 9, color: "#444444", letterSpacing: "0.15em" }}>ERREUR_GRAPHE</span>
        <button onClick={() => this.setState({ crashed: false })} style={{ ...M, fontSize: 9, color: "#FF4500", background: "transparent", border: "none", cursor: "pointer" }}>
          RÉESSAYER
        </button>
      </div>
    );
    return this.props.children;
  }
}

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
  label: string; value: number; type?: string;
}
interface GraphData { nodes: GraphNode[]; links: GraphLink[]; }
interface GraphStats { nodes: number; links: number; companies: number; directors: number; cross_mandates: number; signals: number; }
type PanelTab = "profil" | "connexions" | "signaux";

const NODE_COLORS = {
  company: "#FF4500", company_bodacc: "#FF6600", director: "#FAFAFA",
  holding: "#884422", default: "#444444",
};

function hexToRgba(hex: string, alpha: number): string {
  const h = hex.replace("#", "");
  return `rgba(${parseInt(h.slice(0,2),16)},${parseInt(h.slice(2,4),16)},${parseInt(h.slice(4,6),16)},${alpha})`;
}

function drawDiamond(ctx: CanvasRenderingContext2D, cx: number, cy: number, r: number) {
  ctx.beginPath();
  ctx.moveTo(cx, cy - r); ctx.lineTo(cx + r, cy);
  ctx.lineTo(cx, cy + r); ctx.lineTo(cx - r, cy);
  ctx.closePath();
}

function GraphPageInner() {
  const searchParams = useSearchParams();
  const siren = searchParams?.get("siren");

  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [stats, setStats] = useState<GraphStats | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [search, setSearch] = useState("");
  const [focusMode, setFocusMode] = useState(false);
  const [activeTab, setActiveTab] = useState<PanelTab>("profil");
  const [loading, setLoading] = useState(true);
  const fgRef = useRef<any>(null);
  const tickRef = useRef<number>(0);
  const animRef = useRef<number>(0);

  useEffect(() => {
    const tick = () => { tickRef.current = (tickRef.current + 0.5) % 100; animRef.current = requestAnimationFrame(tick); };
    animRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animRef.current);
  }, []);

  useEffect(() => {
    const url = siren ? `/api/graph?siren=${siren}` : "/api/graph";
    fetch(url).then(r => r.json()).then(d => {
      setGraphData(d.data);
      setStats(d.stats);
      if (d.data.nodes.length > 0) {
        setSelectedNode(d.data.nodes.find((n: GraphNode) => n.type === "company") ?? d.data.nodes[0]);
      }
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [siren]);

  const neighborIds = useMemo(() => {
    if (!selectedNode || !focusMode) return null;
    const ids = new Set<string>([selectedNode.id]);
    graphData.links.forEach(l => {
      const s = typeof l.source === "object" ? (l.source as GraphNode).id : l.source;
      const t = typeof l.target === "object" ? (l.target as GraphNode).id : l.target;
      if (s === selectedNode.id) ids.add(t);
      if (t === selectedNode.id) ids.add(s);
    });
    return ids;
  }, [selectedNode, focusMode, graphData.links]);

  const filteredData = useMemo(() => {
    let nodes = graphData.nodes;
    if (search) nodes = nodes.filter(n =>
      n.name.toLowerCase().includes(search.toLowerCase()) ||
      (n.sector ?? "").toLowerCase().includes(search.toLowerCase())
    );
    const ids = new Set(nodes.map(n => n.id));
    return { nodes, links: graphData.links.filter(l => ids.has(l.source as string) && ids.has(l.target as string)) };
  }, [search, graphData]);

  const nodeCanvasObject = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    try {
      const { x, y } = node;
      if (!isFinite(x) || !isFinite(y)) return;
      const r = node.node_size || 6;
      const isSelected = selectedNode?.id === node.id;
      const isHovered = hoveredNode?.id === node.id;
      const isDirector = node.type === "director";
      const isHolding = node.is_holding || node.type === "holding";
      const isBodacc = !!node.bodacc_recent;
      const isFaded = neighborIds != null && !neighborIds.has(node.id);

      let nodeColor: string;
      if (isDirector) nodeColor = NODE_COLORS.director;
      else if (isHolding) nodeColor = NODE_COLORS.holding;
      else if (isBodacc) nodeColor = NODE_COLORS.company_bodacc;
      else nodeColor = NODE_COLORS.company;

      const alpha = isFaded ? 0.1 : 1;

      if ((isSelected || isHovered) && !isFaded) {
        ctx.beginPath(); ctx.arc(x, y, r * 4, 0, 2 * Math.PI);
        const g = ctx.createRadialGradient(x, y, r * 0.5, x, y, r * 4);
        g.addColorStop(0, hexToRgba(nodeColor, isSelected ? 0.3 : 0.15));
        g.addColorStop(1, hexToRgba(nodeColor, 0));
        ctx.fillStyle = g; ctx.fill();
      }

      if (isSelected) {
        ctx.beginPath(); ctx.arc(x, y, r + 4 / globalScale, 0, 2 * Math.PI);
        ctx.strokeStyle = nodeColor; ctx.lineWidth = 1.5 / globalScale; ctx.stroke();
      }

      ctx.save();
      ctx.globalAlpha = alpha;
      ctx.shadowBlur = isFaded ? 0 : 8;
      ctx.shadowColor = nodeColor;

      if (isDirector) {
        drawDiamond(ctx, x, y, r);
        ctx.fillStyle = hexToRgba(nodeColor, 0.9); ctx.fill();
        ctx.strokeStyle = "#1F1F1F"; ctx.lineWidth = 1 / globalScale; ctx.stroke();
      } else {
        ctx.beginPath(); ctx.arc(x, y, r, 0, 2 * Math.PI);
        ctx.fillStyle = nodeColor; ctx.fill();
      }

      if (isHolding) {
        ctx.beginPath(); ctx.arc(x, y, r + 2 / globalScale, 0, 2 * Math.PI);
        ctx.strokeStyle = hexToRgba(nodeColor, 0.5); ctx.lineWidth = 1 / globalScale; ctx.stroke();
      }
      ctx.restore();

      ctx.save();
      ctx.globalAlpha = alpha;
      if (!isDirector && (node.score ?? 0) > 0 && globalScale > 0.7) {
        ctx.textAlign = "center"; ctx.textBaseline = "middle";
        ctx.fillStyle = "#0A0A0A";
        ctx.font = `bold ${Math.max(5, Math.min(8, 6 / globalScale))}px monospace`;
        ctx.fillText(String(node.score), x, y);
      }
      if (globalScale > 0.6 && !isFaded) {
        const fs = Math.max(7, Math.min(11, 9 / globalScale));
        const label = node.name.length > 14 ? node.name.slice(0, 14) + "…" : node.name;
        ctx.textAlign = "center"; ctx.textBaseline = "top";
        ctx.fillStyle = isDirector ? "#FAFAFA" : "#FAFAFA";
        ctx.font = `${fs}px monospace`;
        ctx.fillText(label, x, y + r + 3 / globalScale);
      }
      ctx.restore();
    } catch { /* safe */ }
  }, [selectedNode, hoveredNode, neighborIds]);

  const linkCanvasObject = useCallback((link: any, ctx: CanvasRenderingContext2D) => {
    try {
      const { source: s, target: t } = link;
      if (!isFinite(s?.x) || !isFinite(t?.x)) return;
      const isFaded = neighborIds != null && (!neighborIds.has(s.id) || !neighborIds.has(t.id));
      ctx.save();
      ctx.globalAlpha = isFaded ? 0.03 : 1;
      ctx.beginPath(); ctx.moveTo(s.x, s.y); ctx.lineTo(t.x, t.y);
      if (link.type === "bodacc") {
        ctx.setLineDash([6, 4]); ctx.lineDashOffset = -tickRef.current;
        ctx.strokeStyle = "rgba(255,69,0,0.6)"; ctx.lineWidth = 1.5;
      } else if (link.type === "dirigeant" || link.type === "directs") {
        ctx.setLineDash([4, 4]); ctx.strokeStyle = "rgba(250,250,250,0.3)"; ctx.lineWidth = 1;
      } else if (link.type === "holding") {
        ctx.setLineDash([]); ctx.strokeStyle = "rgba(136,68,34,0.7)"; ctx.lineWidth = 2;
      } else if (link.type === "cross_mandate") {
        ctx.setLineDash([5, 4]); ctx.strokeStyle = "rgba(255,69,0,0.5)"; ctx.lineWidth = 1.5;
      } else {
        ctx.setLineDash([]); ctx.strokeStyle = "rgba(255,255,255,0.1)"; ctx.lineWidth = 1;
      }
      ctx.stroke();
      ctx.setLineDash([]); ctx.lineDashOffset = 0;
      ctx.restore();
    } catch { /* safe */ }
  }, [neighborIds]);

  const panelLinks = useMemo(() => {
    if (!selectedNode) return [];
    return graphData.links.filter(l => {
      const s = typeof l.source === "object" ? (l.source as GraphNode).id : l.source;
      const t = typeof l.target === "object" ? (l.target as GraphNode).id : l.target;
      return s === selectedNode.id || t === selectedNode.id;
    }).slice(0, 8);
  }, [selectedNode, graphData.links]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100dvh", overflow: "hidden", background: "#0A0A0A" }}>
      {/* Header */}
      <div style={{
        height: 40, borderBottom: "1px solid #1F1F1F", flexShrink: 0,
        display: "flex", alignItems: "center", padding: "0 16px", gap: 12,
        background: "#050505",
      }}>
        <Network size={11} style={{ color: "#FF4500" }} />
        <span style={{ ...M, fontSize: 10, color: "#444444", letterSpacing: "0.15em" }}>RÉSEAU_INTELLIGENCE_M&A</span>
        <div style={{ flex: 1 }} />
        {stats && (
          <div style={{ display: "flex", gap: 16 }}>
            {[
              { v: stats.companies, l: "CIB" },
              { v: stats.directors, l: "DIR" },
              { v: stats.cross_mandates, l: "CROSS" },
              { v: stats.signals, l: "SIG" },
            ].map(s => (
              <span key={s.l} style={{ ...M, fontSize: 8, color: "#333333" }}>
                <span style={{ color: "#FAFAFA" }}>{s.v}</span> {s.l}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Toolbar */}
      <div style={{
        height: 36, borderBottom: "1px solid #1F1F1F", flexShrink: 0,
        display: "flex", alignItems: "center", padding: "0 16px", gap: 8,
        background: "#080808",
      }}>
        <Search size={11} style={{ color: "#333333" }} />
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Rechercher nœud…"
          style={{
            background: "transparent", border: "none", outline: "none",
            color: "#FAFAFA", ...M, fontSize: 10, flex: 1,
          }}
        />
        {selectedNode && (
          <button
            onClick={() => setFocusMode(p => !p)}
            style={{
              ...M, fontSize: 8, padding: "3px 8px",
              background: focusMode ? "rgba(255,69,0,0.1)" : "transparent",
              border: `1px solid ${focusMode ? "#FF4500" : "#1F1F1F"}`,
              color: focusMode ? "#FF4500" : "#444444",
              cursor: "pointer", display: "flex", alignItems: "center", gap: 4, letterSpacing: "0.08em",
            }}
          >
            <Filter size={9} /> FOCUS
          </button>
        )}
        <div style={{ display: "flex", gap: 4 }}>
          <button onClick={() => fgRef.current?.zoom?.((fgRef.current?.zoom?.() || 1) * 1.3, 200)}
            style={{ ...M, fontSize: 8, color: "#444444", background: "transparent", border: "1px solid #1F1F1F", padding: "3px 6px", cursor: "pointer" }}>
            <ZoomIn size={10} />
          </button>
          <button onClick={() => fgRef.current?.zoom?.((fgRef.current?.zoom?.() || 1) * 0.7, 200)}
            style={{ ...M, fontSize: 8, color: "#444444", background: "transparent", border: "1px solid #1F1F1F", padding: "3px 6px", cursor: "pointer" }}>
            <ZoomOut size={10} />
          </button>
          <button onClick={() => fgRef.current?.zoomToFit?.(500, 40)}
            style={{ ...M, fontSize: 8, color: "#444444", background: "transparent", border: "1px solid #1F1F1F", padding: "3px 6px", cursor: "pointer" }}>
            <Maximize2 size={10} />
          </button>
        </div>
      </div>

      {/* Main */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>

        {/* Canvas */}
        <div style={{ flex: 1, position: "relative", overflow: "hidden" }}>
          {loading ? (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", flexDirection: "column", gap: 16 }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#FF4500", animation: "ping 1.5s cubic-bezier(0,0,0.2,1) infinite" }} />
              <span style={{ ...M, fontSize: 9, color: "#444444", letterSpacing: "0.2em" }}>CHARGEMENT_GRAPHE…</span>
            </div>
          ) : (
            <GraphErrorBoundary>
              <ForceGraph2D
                ref={fgRef}
                graphData={filteredData}
                backgroundColor="#0A0A0A"
                nodeLabel={() => ""}
                nodeCanvasObject={nodeCanvasObject}
                linkCanvasObject={linkCanvasObject}
                onNodeClick={(n: any) => { setSelectedNode(n); setActiveTab("profil"); }}
                onNodeHover={(n: any) => setHoveredNode(n)}
                onBackgroundClick={() => focusMode && setFocusMode(false)}
                nodeRelSize={1}
                linkDirectionalParticles={(l: any) => l.type === "cross_mandate" ? 2 : 0}
                linkDirectionalParticleWidth={1.5}
                linkDirectionalParticleColor={() => "#FF4500"}
                linkDirectionalParticleSpeed={0.004}
                d3AlphaDecay={0.02}
                d3VelocityDecay={0.3}
                warmupTicks={80}
                cooldownTicks={300}
              />
            </GraphErrorBoundary>
          )}

          {/* Scanning overlay */}
          <div style={{
            position: "absolute", left: 0, right: 0, height: 1,
            background: "rgba(255,69,0,0.15)",
            animation: "scanLine 6s linear infinite",
            pointerEvents: "none",
          }} />

          {/* Legend */}
          <div style={{ position: "absolute", bottom: 12, left: 12, display: "flex", gap: 12 }}>
            {[
              { c: "#FF4500", l: "CIBLE" },
              { c: "#FAFAFA", l: "DIRIGEANT" },
              { c: "#884422", l: "HOLDING" },
            ].map(item => (
              <div key={item.l} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: item.c, display: "block" }} />
                <span style={{ ...M, fontSize: 7, color: "#333333", letterSpacing: "0.1em" }}>{item.l}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Panel */}
        {selectedNode && (
          <div style={{
            width: 260, flexShrink: 0,
            borderLeft: "1px solid #1F1F1F",
            display: "flex", flexDirection: "column",
            background: "#0A0A0A",
          }}>
            {/* Panel header */}
            <div style={{
              height: 40, borderBottom: "1px solid #1F1F1F",
              display: "flex", alignItems: "center", justifyContent: "space-between",
              padding: "0 12px", flexShrink: 0, background: "#080808",
            }}>
              <span style={{ ...M, fontSize: 8, color: "#333333", letterSpacing: "0.12em" }}>NODE_ANALYSIS</span>
              <button onClick={() => setSelectedNode(null)} style={{ background: "transparent", border: "none", cursor: "pointer", color: "#333333", display: "flex" }}>
                <X size={12} />
              </button>
            </div>

            {/* Node name */}
            <div style={{ padding: "12px 16px", borderBottom: "1px solid #1A1A1A" }}>
              <div style={{ ...S, fontSize: 14, color: "#FAFAFA", fontStyle: "italic", marginBottom: 4, lineHeight: 1.2 }}>
                {selectedNode.name}
              </div>
              <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                <span style={{ ...M, fontSize: 8, color: selectedNode.type === "director" ? "#FAFAFA" : "#FF4500", letterSpacing: "0.1em" }}>
                  {selectedNode.type === "director" ? "DIRIGEANT" : selectedNode.is_holding ? "HOLDING" : "CIBLE_M&A"}
                </span>
                {selectedNode.score != null && (
                  <span style={{ ...M, fontSize: 20, color: "#FF4500", lineHeight: 1, marginLeft: "auto" }}>{selectedNode.score}</span>
                )}
              </div>
            </div>

            {/* Tabs */}
            <div style={{ display: "flex", borderBottom: "1px solid #1A1A1A", flexShrink: 0 }}>
              {(["profil", "connexions", "signaux"] as PanelTab[]).map(tab => (
                <button key={tab} onClick={() => setActiveTab(tab)} style={{
                  flex: 1, height: 32, background: "transparent",
                  border: "none", borderBottom: `2px solid ${activeTab === tab ? "#FF4500" : "transparent"}`,
                  cursor: "pointer", ...M, fontSize: 8,
                  color: activeTab === tab ? "#FAFAFA" : "#333333",
                  letterSpacing: "0.1em",
                }}>
                  {tab === "profil" ? "PROFIL" : tab === "connexions" ? "LIENS" : "SIGNAUX"}
                </button>
              ))}
            </div>

            {/* Tab content */}
            <div style={{ flex: 1, overflowY: "auto", padding: "12px 16px" }} className="thin-scrollbar">
              {activeTab === "profil" && (
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {selectedNode.bodacc_recent && (
                    <div style={{
                      display: "flex", gap: 6, alignItems: "center",
                      padding: "6px 10px", background: "rgba(255,69,0,0.05)",
                      border: "1px solid rgba(255,69,0,0.2)",
                    }}>
                      <AlertTriangle size={10} style={{ color: "#FF4500", flexShrink: 0 }} />
                      <span style={{ ...M, fontSize: 8, color: "#FF4500", letterSpacing: "0.1em" }}>BODACC_RÉCENT</span>
                    </div>
                  )}
                  {[
                    { k: "SECTEUR", v: selectedNode.sector },
                    { k: "VILLE", v: selectedNode.city },
                    { k: "SIREN", v: selectedNode.siren },
                    { k: "CA", v: selectedNode.ca },
                    { k: "EBITDA", v: selectedNode.ebitda },
                    { k: "RÔLE", v: selectedNode.role },
                    { k: "PRIORITÉ", v: selectedNode.priority },
                  ].filter(r => r.v && r.v !== "N/A").map(row => (
                    <div key={row.k} style={{ background: "#111111", border: "1px solid #1A1A1A", padding: "6px 10px" }}>
                      <div style={{ ...M, fontSize: 7, color: "#444444", marginBottom: 2, letterSpacing: "0.12em" }}>{row.k}</div>
                      <div style={{ ...M, fontSize: 10, color: "#FAFAFA" }}>{row.v}</div>
                    </div>
                  ))}
                  {selectedNode.multi_mandats && (
                    <div style={{ display: "flex", gap: 4, alignItems: "center", padding: "4px 8px", border: "1px solid #2A2A2A" }}>
                      <GitBranch size={9} style={{ color: "#FF4500" }} />
                      <span style={{ ...M, fontSize: 8, color: "#FF4500", letterSpacing: "0.1em" }}>MULTI_MANDATS</span>
                    </div>
                  )}
                  {selectedNode.age_signal && (
                    <div style={{ display: "flex", gap: 4, alignItems: "center", padding: "4px 8px", border: "1px solid #2A2A2A" }}>
                      <TrendingUp size={9} style={{ color: "#FF4500" }} />
                      <span style={{ ...M, fontSize: 8, color: "#FF4500", letterSpacing: "0.1em" }}>SIGNAL_SUCCESSION</span>
                    </div>
                  )}
                </div>
              )}

              {activeTab === "connexions" && (
                <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  {panelLinks.length === 0 ? (
                    <span style={{ ...M, fontSize: 9, color: "#333333" }}>Aucune connexion visible</span>
                  ) : panelLinks.map((l, i) => {
                    const other = (typeof l.source === "object" ? (l.source as GraphNode).id : l.source) === selectedNode.id
                      ? (typeof l.target === "object" ? l.target as GraphNode : null)
                      : (typeof l.source === "object" ? l.source as GraphNode : null);
                    return (
                      <div key={i} style={{
                        borderLeft: "2px solid #1F1F1F", paddingLeft: 8, paddingBottom: 6,
                        transition: "border-color 0.15s",
                      }}
                        onMouseEnter={e => (e.currentTarget.style.borderLeftColor = "#FF4500")}
                        onMouseLeave={e => (e.currentTarget.style.borderLeftColor = "#1F1F1F")}
                      >
                        <div style={{ ...M, fontSize: 10, color: "#FAFAFA" }}>{other?.name?.slice(0, 18) ?? "—"}</div>
                        <div style={{ ...M, fontSize: 8, color: "#555555" }}>{l.type?.toUpperCase()} // {l.label?.slice(0, 20)}</div>
                      </div>
                    );
                  })}
                  <button
                    onClick={() => setFocusMode(p => !p)}
                    style={{
                      marginTop: 8, width: "100%", height: 32,
                      border: `1px solid ${focusMode ? "#FF4500" : "#1F1F1F"}`,
                      background: focusMode ? "rgba(255,69,0,0.05)" : "transparent",
                      ...M, fontSize: 8, color: focusMode ? "#FF4500" : "#444444",
                      cursor: "pointer", letterSpacing: "0.1em",
                      display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
                    }}
                  >
                    <Filter size={9} />
                    {focusMode ? "DÉSACTIVER_FOCUS" : "ISOLER_CE_NŒUD"}
                  </button>
                </div>
              )}

              {activeTab === "signaux" && (
                <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  {(selectedNode.signals?.length ?? 0) === 0 ? (
                    <span style={{ ...M, fontSize: 9, color: "#333333" }}>Aucun signal actif</span>
                  ) : selectedNode.signals?.map((sig, i) => (
                    <div key={i} style={{
                      borderLeft: "2px solid #FF4500", paddingLeft: 8, paddingBottom: 4,
                    }}>
                      <div style={{ ...M, fontSize: 9, color: "#FAFAFA", lineHeight: 1.5 }}>{sig}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Footer CTA */}
            {selectedNode.type === "company" && selectedNode.siren && (
              <div style={{ padding: "10px 16px", borderTop: "1px solid #1A1A1A", flexShrink: 0 }}>
                <Link href={`/targets/${selectedNode.siren}`} style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  padding: "10px 14px",
                  background: "#111111", border: "1px solid #1F1F1F",
                  textDecoration: "none",
                  transition: "border-color 0.15s, background 0.15s",
                }}
                  onMouseEnter={e => { (e.currentTarget as HTMLAnchorElement).style.borderColor = "#FF4500"; (e.currentTarget as HTMLAnchorElement).style.background = "rgba(255,69,0,0.05)"; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLAnchorElement).style.borderColor = "#1F1F1F"; (e.currentTarget as HTMLAnchorElement).style.background = "#111111"; }}
                >
                  <span style={{ ...M, fontSize: 9, color: "#FAFAFA", letterSpacing: "0.1em" }}>OUVRIR_DOSSIER</span>
                  <ChevronRight size={12} style={{ color: "#FF4500" }} />
                </Link>
              </div>
            )}
          </div>
        )}
      </div>

      <style>{`
        @keyframes scanLine { from { top: -2% } to { top: 102% } }
        @keyframes ping { 75%, 100% { transform: scale(2); opacity: 0; } }
      `}</style>
    </div>
  );
}

export default function GraphPage() {
  return (
    <Suspense fallback={<div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100dvh", background: "#0A0A0A", fontFamily: "'JetBrains Mono',monospace", fontSize: 9, color: "#444444", letterSpacing: "0.15em" }}>CHARGEMENT_GRAPHE…</div>}>
      <GraphPageInner />
    </Suspense>
  );
}
