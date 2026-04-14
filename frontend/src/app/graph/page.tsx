"use client";

import { useState, useMemo, useCallback } from "react";
import { Network, Search, Filter, Download, Info } from "lucide-react";
import dynamic from "next/dynamic";
import NodeDetailSheet from "@/components/graph/NodeDetailSheet";
import LayoutSwitcher from "@/components/graph/LayoutSwitcher";
import { useGraph } from "@/lib/queries/useGraph";

const GraphCanvas = dynamic(() => import("@/components/graph/GraphCanvas"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full">
      <div className="text-center space-y-4">
        <div className="w-12 h-12 border-4 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin mx-auto" />
        <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest">
          Chargement du graphe réseau...
        </span>
      </div>
    </div>
  ),
});

interface GraphNode {
  id: string;
  name: string;
  type: string;
  role: string;
  color: string;
  company?: string;
  score?: number;
  signals_count?: number;
  signals?: string[];
  is_holding?: boolean;
}

type FilterType = "all" | "internal" | "target" | "advisor" | "subsidiary";
type LayoutType = "force" | "dagre" | "radial" | "circular";

const FILTER_OPTIONS: { key: FilterType; label: string; color: string }[] = [
  { key: "all", label: "Tout", color: "#ffffff" },
  { key: "internal", label: "Équipe EDR", color: "#6366f1" },
  { key: "target", label: "Cibles", color: "#10b981" },
  { key: "advisor", label: "Conseillers", color: "#f59e0b" },
  { key: "subsidiary", label: "Filiales", color: "#8b5cf6" },
];

export default function RelationshipGraph() {
  const { data: graphResponse, isLoading } = useGraph();
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState<FilterType>("all");
  const [layout, setLayout] = useState<LayoutType>("force");

  const graphData = graphResponse?.data || { nodes: [], links: [] };

  const filteredData = useMemo(() => {
    let nodes = graphData.nodes;

    if (activeFilter !== "all") {
      if (activeFilter === "subsidiary") {
        const subNodes = nodes.filter((n) => n.type === "subsidiary");
        const parentIds = new Set(
          subNodes.map((n) => n.company).filter(Boolean)
        );
        nodes = nodes.filter(
          (n) =>
            n.type === "subsidiary" ||
            (n.type === "target" && parentIds.has(n.company))
        );
      } else {
        nodes = nodes.filter((n) => n.type === activeFilter);
      }
    }

    const nodeIds = new Set(nodes.map((n) => n.id));
    const links = graphData.links.filter(
      (l) =>
        nodeIds.has(l.source as string) && nodeIds.has(l.target as string)
    );
    return { nodes, links };
  }, [activeFilter, graphData]);

  const handleNodeClick = useCallback((node: GraphNode) => {
    setSelectedNode(node);
  }, []);

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] lg:h-[calc(100vh-4rem)] w-full max-w-7xl mx-auto pb-20 lg:pb-4 px-2 sm:px-4 overflow-hidden">
      {/* Header */}
      <header className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 lg:gap-6 mb-4 lg:mb-6 pt-4">
        <div>
          <h1 className="text-2xl md:text-4xl font-black tracking-tight text-white mb-2 flex items-center gap-3 lg:gap-4">
            <div className="p-2 rounded-xl lg:rounded-2xl bg-indigo-500/10 border border-indigo-500/20">
              <Network size={20} className="text-indigo-400 lg:w-6 lg:h-6" />
            </div>
            Intelligence Réseau
          </h1>
          <p className="text-gray-400 text-xs sm:text-sm font-medium hidden sm:block">
            Cartographie relationnelle propriétaire identifiant les chemins d&apos;approche.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative group w-full sm:w-72 lg:w-80">
            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-indigo-400 transition-colors">
              <Search size={16} />
            </span>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Rechercher un noeud..."
              className="w-full bg-white/[0.03] border border-white/10 rounded-xl lg:rounded-2xl py-2.5 lg:py-3 pl-11 lg:pl-12 pr-4 text-sm text-gray-200 placeholder-gray-600 outline-none focus:border-indigo-500/50 focus:bg-white/[0.05] transition-all"
            />
          </div>
          {/* Filter buttons */}
          <div className="flex items-center gap-1.5 lg:gap-2 overflow-x-auto scrollbar-hide pb-1">
            {FILTER_OPTIONS.map((opt) => (
              <button
                key={opt.key}
                onClick={() => setActiveFilter(opt.key)}
                className={`shrink-0 px-3 lg:px-4 py-2 rounded-xl lg:rounded-2xl text-[10px] lg:text-xs font-black uppercase tracking-widest transition-all border ${
                  activeFilter === opt.key
                    ? "bg-white/10 border-white/30 text-white"
                    : "bg-white/[0.03] border-white/10 text-gray-500 hover:text-gray-300 hover:bg-white/5"
                }`}
                style={
                  activeFilter === opt.key
                    ? { borderColor: opt.color + "60", color: opt.color }
                    : {}
                }
              >
                <span
                  className="inline-block w-1.5 h-1.5 lg:w-2 lg:h-2 rounded-full mr-1.5 lg:mr-2"
                  style={{
                    backgroundColor: opt.color,
                    opacity: activeFilter === opt.key ? 1 : 0.4,
                  }}
                />
                <span className="hidden sm:inline">{opt.label}</span>
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Layout switcher */}
      <div className="flex items-center justify-between mb-3 lg:mb-4">
        <LayoutSwitcher current={layout} onChange={setLayout} />
        <div className="text-[9px] font-black text-gray-600 uppercase tracking-widest hidden sm:block">
          {filteredData.nodes.length} nodes · {filteredData.links.length} liens
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-4 lg:gap-8 min-h-0">
        {/* Graph canvas */}
        <div className="lg:col-span-3 rounded-[1.5rem] lg:rounded-[2.5rem] bg-[#050505] border border-white/10 relative overflow-hidden flex flex-col shadow-[0_4px_50px_rgba(0,0,0,0.8)]">
          {/* Legend — desktop only */}
          <div className="absolute top-4 sm:top-6 left-4 sm:left-6 z-10 hidden sm:flex flex-col gap-2">
            {[
              { color: "#6366f1", label: "Équipe EDR" },
              { color: "#10b981", label: "Cible" },
              { color: "#f59e0b", label: "Conseil" },
              { color: "#8b5cf6", label: "Filiale" },
              { color: "#ef4444", label: "Signal actif" },
            ].map(({ color, label }) => (
              <div
                key={label}
                className="px-3 py-1.5 rounded-xl bg-black/60 border border-white/10 text-[9px] uppercase font-black tracking-widest text-gray-400 flex items-center gap-2"
              >
                <div
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: color }}
                />
                {label}
              </div>
            ))}
          </div>

          {/* Graph */}
          <div className="flex-1 w-full h-full min-h-[250px]">
            {isLoading ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center space-y-4">
                  <div className="w-12 h-12 border-4 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin mx-auto" />
                  <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest">
                    Chargement du graphe réseau...
                  </span>
                </div>
              </div>
            ) : (
              <GraphCanvas
                nodes={filteredData.nodes}
                links={filteredData.links}
                onNodeClick={handleNodeClick}
                layout={layout}
                highlightNodeId={selectedNode?.id}
                searchTerm={search}
              />
            )}
          </div>

          {/* Bottom info badge */}
          <div className="absolute bottom-4 lg:bottom-6 left-4 lg:left-6 z-10">
            <div className="px-3 lg:px-4 py-1.5 lg:py-2 rounded-xl lg:rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-[9px] lg:text-[10px] tracking-widest uppercase font-black text-indigo-400 flex items-center gap-2">
              <Info size={12} /> Données réseau EdRCF 6.0
            </div>
          </div>
        </div>

        {/* Detail panel */}
        <NodeDetailSheet
          node={selectedNode}
          onClose={() => setSelectedNode(null)}
        />
      </div>
    </div>
  );
}
