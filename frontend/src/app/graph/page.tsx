"use client";

import { useState, useMemo, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Network, Search, Filter, Download, Info, Zap, ArrowUpRight, X, AlertTriangle, Building2 } from "lucide-react";
import dynamic from 'next/dynamic';
import Link from "next/link";

const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false });

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

interface GraphLink {
  source: string;
  target: string;
  label: string;
  value: number;
}

interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

type FilterType = 'all' | 'internal' | 'target' | 'advisor' | 'subsidiary';

const FILTER_OPTIONS: { key: FilterType; label: string; color: string }[] = [
  { key: 'all', label: 'Tout', color: '#ffffff' },
  { key: 'internal', label: 'Équipe EDR', color: '#6366f1' },
  { key: 'target', label: 'Cibles', color: '#10b981' },
  { key: 'advisor', label: 'Conseillers', color: '#f59e0b' },
  { key: 'subsidiary', label: 'Filiales', color: '#8b5cf6' },
];

const SEVERITY_COLOR: Record<string, string> = {
  high: '#ef4444',
  medium: '#f59e0b',
  low: '#6366f1',
};

export default function RelationshipGraph() {
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState<FilterType>('all');
  const [loading, setLoading] = useState(true);
  const fgRef = useRef<any>(null);

  useEffect(() => {
    fetch("/api/graph")
      .then(res => res.json())
      .then(data => {
        setGraphData(data.data);
        if (data.data.nodes.length > 2) {
          setSelectedNode(data.data.nodes[2]);
        }
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to fetch graph:", err);
        setLoading(false);
      });
  }, []);

  const filteredData = useMemo(() => {
    let nodes = graphData.nodes;

    // Apply type filter
    if (activeFilter !== 'all') {
      if (activeFilter === 'subsidiary') {
        const subNodes = nodes.filter(n => n.type === 'subsidiary');
        const parentIds = new Set(subNodes.map(n => n.company).filter(Boolean));
        nodes = nodes.filter(n => n.type === 'subsidiary' || (n.type === 'target' && parentIds.has(n.company)));
      } else {
        nodes = nodes.filter(n => n.type === activeFilter);
      }
    }

    // Apply search
    if (search) {
      nodes = nodes.filter(n =>
        n.name.toLowerCase().includes(search.toLowerCase()) ||
        (n.company || '').toLowerCase().includes(search.toLowerCase())
      );
    }

    const nodeIds = new Set(nodes.map(n => n.id));
    const links = graphData.links.filter(l =>
      nodeIds.has(l.source as string) && nodeIds.has(l.target as string)
    );
    return { nodes, links };
  }, [search, activeFilter, graphData]);

  const typeLabel = (type: string) => {
    if (type === 'internal') return 'Équipe EDR';
    if (type === 'target') return 'Cible';
    if (type === 'advisor') return 'Conseil';
    if (type === 'subsidiary') return 'Filiale';
    return type;
  };

  return (
    <div className="flex flex-col h-[calc(100dvh-4rem)] pb-4 overflow-hidden">
      {/* Header compact */}
      <header className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 mb-3 sm:mb-4 pt-3 px-1 shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-1.5 sm:p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20">
            <Network size={20} className="text-indigo-400" />
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl lg:text-3xl font-black tracking-tight text-white leading-none">
              Intelligence Réseau
            </h1>
            <p className="text-gray-500 text-xs font-medium mt-0.5 hidden sm:block">
              Cartographie relationnelle propriétaire
            </p>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-2 sm:gap-3 items-stretch sm:items-center">
          <div className="relative group w-full sm:w-56 lg:w-64">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-indigo-400 transition-colors">
               <Search size={16} />
            </span>
            <input
               type="text"
               value={search}
               onChange={(e) => setSearch(e.target.value)}
               placeholder="Rechercher..."
               className="w-full bg-white/[0.03] border border-white/10 rounded-xl py-2 pl-9 pr-3 text-sm text-gray-200 placeholder-gray-600 outline-none focus:border-indigo-500/50 focus:bg-white/[0.05] transition-all"
            />
          </div>
          {/* Filter buttons -- compact pills */}
          <div className="flex items-center gap-1.5 flex-wrap">
            {FILTER_OPTIONS.map(opt => (
              <button
                key={opt.key}
                onClick={() => setActiveFilter(opt.key)}
                className={`px-2.5 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-wider transition-all border ${
                  activeFilter === opt.key
                    ? 'bg-white/10 border-white/30 text-white'
                    : 'bg-white/[0.03] border-white/10 text-gray-500 hover:text-gray-300 hover:bg-white/5'
                }`}
                style={activeFilter === opt.key ? { borderColor: opt.color + '60', color: opt.color } : {}}
              >
                <span
                  className="inline-block w-1.5 h-1.5 rounded-full mr-1.5"
                  style={{ backgroundColor: opt.color, opacity: activeFilter === opt.key ? 1 : 0.4 }}
                />
                <span className="hidden sm:inline">{opt.label}</span>
                <Filter size={10} className="sm:hidden inline" />
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Main content -- graph + panel */}
      <div className="flex-1 flex gap-3 sm:gap-4 min-h-0">

        {/* Graph canvas */}
        <div className="flex-1 rounded-2xl bg-[#050505] border border-white/10 relative overflow-hidden flex flex-col shadow-[0_4px_50px_rgba(0,0,0,0.8)]">
          {/* Legend -- horizontal compact on desktop */}
          <div className="absolute top-3 left-3 z-10 flex flex-wrap gap-1.5">
            {[
              { color: '#6366f1', label: 'EDR' },
              { color: '#10b981', label: 'Cible' },
              { color: '#f59e0b', label: 'Conseil' },
              { color: '#8b5cf6', label: 'Filiale' },
              { color: '#ef4444', label: 'Signal' },
            ].map(({ color, label }) => (
              <div key={label} className="px-2 py-1 rounded-lg bg-black/70 border border-white/10 backdrop-blur-md text-[8px] uppercase font-black tracking-wider text-gray-400 flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: color }} />
                {label}
              </div>
            ))}
          </div>

          {/* Zoom button */}
          <button onClick={() => fgRef.current?.zoomToFit(400)} className="absolute top-3 right-3 z-10 w-8 h-8 rounded-lg bg-black/70 border border-white/10 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-all">
            <Download size={16} />
          </button>

          <div className="flex-1 w-full h-full">
            {loading ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center space-y-3">
                  <div className="w-10 h-10 border-3 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin mx-auto" />
                  <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Chargement...</span>
                </div>
              </div>
            ) : (
              <ForceGraph2D
                ref={fgRef}
                graphData={filteredData}
                backgroundColor="#050505"
                nodeLabel="name"
                nodeColor={(node: any) => node.color}
                nodeRelSize={7}
                linkColor={(link: any) => link.label === 'Filiale' ? 'rgba(139,92,246,0.3)' : 'rgba(255,255,255,0.08)'}
                linkWidth={(link: any) => link.value}
                linkLineDash={(link: any) => link.label === 'Filiale' ? [2, 3] : null}
                onNodeClick={(node: any) => setSelectedNode(node)}
                nodeCanvasObject={(node: any, ctx: any, globalScale: number) => {
                  const { x, y } = node;
                  const isSubsidiary = node.type === 'subsidiary';
                  const r = isSubsidiary ? 4 : 6;
                  const fontSize = 12 / globalScale;

                  ctx.beginPath();
                  ctx.arc(x, y, r, 0, 2 * Math.PI, false);
                  ctx.fillStyle = node.color;
                  ctx.fill();

                  if (node.is_holding) {
                    ctx.beginPath();
                    ctx.arc(x, y, r + 3 / globalScale, 0, 2 * Math.PI, false);
                    ctx.strokeStyle = node.color + '60';
                    ctx.lineWidth = 1.5 / globalScale;
                    ctx.stroke();
                  }

                  if (selectedNode?.id === node.id) {
                    ctx.beginPath();
                    ctx.arc(x, y, r + 3, 0, 2 * Math.PI, false);
                    ctx.strokeStyle = node.color;
                    ctx.lineWidth = 2 / globalScale;
                    ctx.stroke();
                  }

                  if (node.signals_count > 0) {
                    const badgeR = 3.5 / globalScale;
                    const bx = x + r * 0.8;
                    const by = y - r * 0.8;
                    ctx.beginPath();
                    ctx.arc(bx, by, badgeR, 0, 2 * Math.PI, false);
                    ctx.fillStyle = '#ef4444';
                    ctx.fill();
                    if (globalScale > 1.2 && node.signals_count > 1) {
                      ctx.fillStyle = '#fff';
                      ctx.font = `bold ${Math.max(6, 9 / globalScale)}px sans-serif`;
                      ctx.textAlign = 'center';
                      ctx.textBaseline = 'middle';
                      ctx.fillText(String(node.signals_count), bx, by);
                    }
                  }

                  ctx.textAlign = 'center';
                  ctx.textBaseline = 'middle';
                  ctx.fillStyle = isSubsidiary ? 'rgba(255,255,255,0.5)' : 'rgba(255,255,255,0.8)';
                  ctx.font = `${isSubsidiary ? '' : 'bold '}${fontSize}px sans-serif`;
                  ctx.fillText(node.name, x, y + r + 8 / globalScale);
                }}
              />
            )}
          </div>

          <div className="absolute bottom-3 left-3 z-10">
             <div className="px-3 py-1.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 backdrop-blur-md text-[9px] tracking-widest uppercase font-black text-indigo-400 flex items-center gap-1.5">
                <Info size={12} /> EdRCF 6.0
             </div>
          </div>
        </div>

        {/* Detail panel -- compact, no internal scroll on desktop */}
        <AnimatePresence mode="wait">
          {selectedNode && (
            <motion.div
              key={selectedNode?.id}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="
                fixed lg:relative bottom-3 left-3 right-3 lg:bottom-0 lg:left-0 lg:right-0
                w-auto lg:w-72 xl:w-80 shrink-0
                rounded-2xl bg-black/90 lg:bg-black/40 border border-white/10 backdrop-blur-3xl
                p-4 lg:p-5
                flex flex-col
                max-h-[55dvh] lg:max-h-full
                overflow-y-auto lg:overflow-y-auto
                shadow-2xl z-[60]
                custom-scrollbar
              "
            >
              {/* Mobile close */}
              <div className="flex items-center justify-between lg:hidden mb-3">
                <span className="text-[9px] font-black text-gray-600 uppercase tracking-widest">Fiche Contact</span>
                <button onClick={() => setSelectedNode(null)} className="p-1.5 rounded-lg bg-white/5 text-gray-500"><X size={14} /></button>
              </div>

              {/* Identity */}
              <div className="flex items-center gap-3 mb-4">
                <div
                  className="w-11 h-11 rounded-xl flex items-center justify-center text-white font-black text-lg shrink-0"
                  style={{ backgroundColor: selectedNode.color + '20', border: `1px solid ${selectedNode.color}40` }}
                >
                  {selectedNode.name.split(' ').map((n: string) => n[0]).join('').substring(0, 2)}
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <h2 className="text-base lg:text-lg font-black text-white leading-tight tracking-tighter truncate">{selectedNode.name}</h2>
                    {selectedNode.is_holding && (
                      <span className="px-1.5 py-0.5 rounded bg-purple-500/10 border border-purple-500/20 text-[8px] font-black text-purple-400 uppercase flex items-center gap-0.5">
                        <Building2 size={8} /> Grp
                      </span>
                    )}
                  </div>
                  <p className="text-indigo-400 text-[9px] font-black uppercase tracking-widest mt-0.5 truncate">{selectedNode.role}</p>
                </div>
              </div>

              {/* Type + Score -- inline */}
              <div className="grid grid-cols-2 gap-2 mb-3">
                 <div className="p-2.5 rounded-xl bg-white/[0.03] border border-white/5">
                    <div className="text-[8px] font-black text-gray-600 uppercase tracking-widest">Type</div>
                    <div className="text-xs font-black text-white capitalize mt-0.5">{typeLabel(selectedNode.type)}</div>
                 </div>
                 <div className="p-2.5 rounded-xl bg-white/[0.03] border border-white/5">
                    <div className="text-[8px] font-black text-gray-600 uppercase tracking-widest">Score</div>
                    <div className="text-xs font-black text-white mt-0.5">{selectedNode.score ? `${selectedNode.score}/100` : 'N/A'}</div>
                 </div>
              </div>

              {selectedNode.company && (
                <div className="p-2.5 rounded-xl bg-white/[0.02] border border-white/5 mb-3">
                  <div className="text-[8px] font-black text-gray-600 uppercase tracking-widest">Entreprise</div>
                  <div className="text-xs font-bold text-gray-300 mt-0.5 truncate">{selectedNode.company}</div>
                </div>
              )}

              {/* Signals */}
              {(selectedNode.signals_count ?? 0) > 0 && selectedNode.signals && (
                <div className="mb-3">
                  <h3 className="text-[9px] font-black text-gray-600 uppercase tracking-widest flex items-center gap-1.5 mb-2">
                    <AlertTriangle size={10} className="text-red-400" />
                    Signaux ({selectedNode.signals_count})
                  </h3>
                  <div className="space-y-1.5">
                    {selectedNode.signals.map((sig, i) => (
                      <div key={i} className="flex items-start gap-1.5 p-2 rounded-lg bg-red-500/5 border border-red-500/10">
                        <div className="w-1 h-1 rounded-full bg-red-400 mt-1.5 shrink-0" />
                        <span className="text-[11px] text-gray-300 font-medium leading-snug">{sig}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Intelligence */}
              <div className="p-3 rounded-xl bg-indigo-500/5 border border-indigo-500/10 flex gap-2 mb-3">
                <Zap size={14} className="text-indigo-400 shrink-0 mt-0.5" />
                <p className="text-[11px] text-gray-400 leading-relaxed font-medium">
                  Connexion via le <span className="text-white font-bold">réseau EdRCF 6.0</span>.
                </p>
              </div>

              {/* CTA */}
              {selectedNode.type === 'target' && (
                <Link href={`/targets/${selectedNode.id}`} className="w-full py-3 rounded-xl bg-white text-black font-black text-[10px] uppercase tracking-widest hover:bg-indigo-50 transition-all shadow-lg flex items-center justify-center gap-2 mt-auto">
                   Ouvrir la Fiche <ArrowUpRight size={14} />
                </Link>
              )}
            </motion.div>
          )}
        </AnimatePresence>

      </div>
    </div>
  );
}
