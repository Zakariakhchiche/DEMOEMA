"use client";

import { useState, useEffect, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Target, Search, Filter, ArrowUpDown, ChevronRight, Building, Download, SlidersHorizontal, X, Check, Globe, Shield } from "lucide-react";
import { useRouter } from "next/navigation";

import { Target as TargetData } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

type SortKey = "name" | "sector" | "dealType" | "priorityScore";

export default function TargetsPage() {
  const [targets, setTargets] = useState<TargetData[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("priorityScore");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [showFilters, setShowFilters] = useState(false);
  const [selectedSectors, setSelectedSectors] = useState<string[]>([]);
  const [minScore, setMinScore] = useState(40);
  
  const router = useRouter();

  useEffect(() => {
    fetch(`${API_URL}/api/targets`)
      .then(res => res.json())
      .then(data => {
        setTargets(data.data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const sectors = useMemo(() => Array.from(new Set(targets.map(t => t.sector))), [targets]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortOrder("desc");
    }
  };

  const filteredAndSortedTargets = useMemo(() => {
    return targets
      .filter(t => 
        (t.name.toLowerCase().includes(search.toLowerCase()) ||
         t.sector.toLowerCase().includes(search.toLowerCase()) ||
         t.dealType.toLowerCase().includes(search.toLowerCase())) &&
        (selectedSectors.length === 0 || selectedSectors.includes(t.sector)) &&
        t.priorityScore >= minScore
      )
      .sort((a, b) => {
        const valA = a[sortKey];
        const valB = b[sortKey];
        if (typeof valA === "string" && typeof valB === "string") {
          return sortOrder === "asc" 
            ? valA.localeCompare(valB) 
            : valB.localeCompare(valA);
        }
        return sortOrder === "asc" 
          ? (valA as number) - (valB as number) 
          : (valB as number) - (valA as number);
      });
  }, [targets, search, sortKey, sortOrder, selectedSectors, minScore]);

  return (
    <div className="flex flex-col gap-10 w-full max-w-7xl mx-auto py-4 h-[calc(100vh-8rem)]">
      
      {/* Filter Sidebar Overlay */}
      <AnimatePresence>
        {showFilters && (
          <>
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowFilters(false)}
              className="fixed inset-0 bg-black/80 backdrop-blur-xl z-[100]"
            />
            <motion.div 
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              className="fixed top-0 right-0 bottom-0 w-full sm:w-96 bg-[#0a0a0a] border-l border-white/10 z-[101] p-6 sm:p-10 shadow-[0_0_100px_rgba(0,0,0,0.8)] flex flex-col"
            >
              <div className="flex items-center justify-between mb-10">
                <h2 className="text-2xl font-black text-white uppercase tracking-tighter">Engine Filters</h2>
                <button onClick={() => setShowFilters(false)} className="p-3 rounded-2xl bg-white/5 text-gray-400 hover:text-white transition-all active:scale-95">
                  <X size={20} />
                </button>
              </div>

              <div className="space-y-10 flex-1 overflow-y-auto custom-scrollbar pr-2">
                 <div>
                    <h3 className="text-[11px] font-black text-white uppercase tracking-[0.2em] mb-6 flex items-center gap-2">
                        <Globe size={14} className="text-indigo-500" /> Sectors
                    </h3>
                    <div className="flex flex-wrap gap-2.5">
                       {sectors.map(s => (
                         <button 
                           key={s}
                           onClick={() => setSelectedSectors(curr => curr.includes(s) ? curr.filter(x => x !== s) : [...curr, s])}
                           className={`px-4 py-2 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all border
                             ${selectedSectors.includes(s) 
                               ? "bg-indigo-500 border-indigo-400 text-white shadow-[0_0_20px_rgba(79,70,229,0.3)]" 
                               : "bg-white/5 border-white/10 text-gray-500 hover:bg-white/10 hover:text-gray-300"
                             }
                           `}
                         >
                           {s}
                         </button>
                       ))}
                    </div>
                 </div>

                 <div>
                    <div className="flex justify-between items-center mb-6">
                       <h3 className="text-[11px] font-black text-white uppercase tracking-[0.2em] flex items-center gap-2">
                           <Shield size={14} className="text-indigo-500" /> Confidence Threshold
                       </h3>
                       <span className="text-2xl font-black text-indigo-400">{minScore}</span>
                    </div>
                    <input 
                      type="range" 
                      min="0" max="100" 
                      value={minScore}
                      onChange={(e) => setMinScore(parseInt(e.target.value))}
                      className="w-full accent-indigo-500 h-1.5 bg-white/10 rounded-full appearance-none cursor-pointer"
                    />
                    <div className="flex justify-between mt-3 text-[9px] font-black text-gray-700 uppercase tracking-widest">
                        <span>Min Confidence</span>
                        <span>High Priority Only</span>
                    </div>
                 </div>
              </div>

              <div className="pt-10 border-t border-white/10 mt-auto">
                 <button 
                   onClick={() => {
                     setSelectedSectors([]);
                     setMinScore(40);
                   }}
                   className="w-full py-4 rounded-3xl bg-white/5 border border-white/10 text-[11px] font-black uppercase text-gray-500 hover:bg-rose-500/10 hover:text-rose-400 hover:border-rose-500/20 transition-all tracking-widest active:scale-95"
                 >
                   Reset Scoping
                 </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Header */}
      <header className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 shrink-0">
        <div>
          <h1 className="text-3xl md:text-5xl font-black tracking-tighter text-white mb-3 flex flex-wrap items-center gap-4 sm:gap-5">
            Intelligence Vault
            <div className="px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-[10px] text-indigo-400 font-black uppercase tracking-[0.2em]">
               {filteredAndSortedTargets.length} Entities Proxied
            </div>
          </h1>
          <p className="text-gray-400 text-base md:text-lg font-medium max-w-2xl leading-relaxed">
            Universal directory of analyzed entities. Calibrated by <span className="text-white">Aethelgard High-Fidelity Scoring</span>.
          </p>
        </div>
        
        <div className="flex flex-col sm:flex-row gap-4 w-full lg:w-auto">
          <div className="relative group w-full lg:w-80">
            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-indigo-400 transition-colors">
               <Search size={20} />
            </span>
            <input 
               type="text" 
               value={search}
               onChange={(e) => setSearch(e.target.value)}
               placeholder="Intercept company..." 
               className="w-full bg-white/[0.03] border border-white/10 rounded-[2rem] py-4 pl-14 pr-6 text-sm text-gray-200 placeholder-gray-600 outline-none focus:border-indigo-500/50 focus:bg-white/[0.05] transition-all backdrop-blur-md"
            />
          </div>
          <div className="flex gap-4 w-full sm:w-auto">
            <button 
              onClick={() => setShowFilters(true)}
              className={`flex-1 sm:flex-none px-6 py-4 rounded-[2rem] transition-all flex items-center justify-center gap-3 font-black text-[11px] uppercase tracking-widest
                ${selectedSectors.length > 0 || minScore > 40 ? "bg-indigo-600 border border-indigo-500 text-white shadow-2xl shadow-indigo-600/30" : "bg-white/[0.03] border border-white/10 text-white hover:bg-white/10"}
              `}
            >
              <SlidersHorizontal size={18} /> Scoping {(selectedSectors.length > 0) && `(${selectedSectors.length})`}
            </button>
            <button className="flex-1 sm:flex-none px-6 py-4 rounded-[2rem] bg-indigo-600/10 text-indigo-400 border border-indigo-500/20 hover:bg-indigo-600 hover:text-white transition-all flex items-center justify-center gap-3 font-black text-[11px] uppercase tracking-widest active:scale-95 shadow-2xl">
              <Download size={18} /> <span className="sm:hidden lg:inline">Export</span>
            </button>
          </div>
        </div>
      </header>

      {/* Table Area */}
      <div className="flex-1 bg-black/40 border border-white/10 rounded-[3rem] overflow-hidden flex flex-col shadow-2xl backdrop-blur-3xl relative">
        
        {/* Table Header - Desktop Only */}
        <div className="hidden lg:grid grid-cols-12 gap-6 px-10 py-6 border-b border-white/10 bg-white/[0.02] text-[11px] font-black text-gray-500 uppercase tracking-[0.2em]">
          <div 
            className="col-span-4 flex items-center gap-3 cursor-pointer hover:text-white transition-colors"
            onClick={() => handleSort("name")}
          >
            Entity Identity {sortKey === "name" && <ArrowUpDown size={14} className="text-indigo-400" />}
          </div>
          <div 
            className="col-span-2 flex items-center gap-3 cursor-pointer hover:text-white transition-colors"
            onClick={() => handleSort("sector")}
          >
            Sub-Cluster {sortKey === "sector" && <ArrowUpDown size={14} className="text-indigo-400" />}
          </div>
          <div 
            className="col-span-3 flex items-center gap-3 cursor-pointer hover:text-white transition-colors"
            onClick={() => handleSort("dealType")}
          >
            Primary Thesis {sortKey === "dealType" && <ArrowUpDown size={14} className="text-indigo-400" />}
          </div>
          <div 
            className="col-span-2 flex items-center gap-3 cursor-pointer hover:text-white transition-colors justify-end text-right"
            onClick={() => handleSort("priorityScore")}
          >
            Confidence Metric {sortKey === "priorityScore" && <ArrowUpDown size={14} className="text-indigo-400" />}
          </div>
          <div className="col-span-1 text-right">Data</div>
        </div>

        {/* Table Body */}
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          {loading ? (
            <div className="p-20 text-center text-gray-500 flex flex-col items-center justify-center h-full gap-8">
              <div className="relative w-16 h-16">
                <div className="absolute inset-0 border-4 border-indigo-500/10 rounded-full" />
                <div className="absolute inset-0 border-t-4 border-indigo-500 rounded-full animate-spin shadow-[0_0_20px_rgba(79,70,229,0.5)]" />
              </div>
              <span className="font-black uppercase tracking-[0.3em] text-[10px] text-white/50">Accessing Aethelgard Datastream...</span>
            </div>
          ) : (
            <div className="flex flex-col divide-y divide-white/[0.03]">
              <AnimatePresence mode="popLayout">
                {filteredAndSortedTargets.map((target, idx) => (
                  <motion.div 
                    layout
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.3, delay: idx * 0.05 }}
                    key={target.id}
                    onClick={() => router.push(`/targets/${target.id}`)}
                    className="flex flex-col lg:grid lg:grid-cols-12 gap-4 lg:gap-6 px-6 lg:px-10 py-6 lg:py-7 items-start lg:items-center hover:bg-white/[0.04] transition-all cursor-pointer group active:scale-[0.998] relative overflow-hidden"
                  >
                    <div className="w-full lg:col-span-4 flex items-center gap-4 lg:gap-5">
                      <div className="w-12 h-12 lg:w-14 lg:h-14 rounded-xl lg:rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center text-gray-500 group-hover:text-indigo-400 group-hover:bg-indigo-500/10 group-hover:border-indigo-500/30 transition-all shadow-xl shrink-0">
                         <Building size={24} />
                      </div>
                      <div className="min-w-0">
                        <div className="font-black text-white text-base lg:text-lg group-hover:text-indigo-400 transition-colors tracking-tighter leading-tight mb-1 truncate">{target.name}</div>
                        <div className="text-[9px] font-black text-gray-700 uppercase tracking-[0.2em]">{target.id}</div>
                      </div>
                    </div>

                    <div className="w-full lg:col-span-2 flex items-center justify-between lg:block">
                      <span className="lg:hidden text-[9px] font-black text-gray-600 uppercase tracking-widest">Sector</span>
                      <span className="px-3 py-1 lg:py-1.5 rounded-xl text-[10px] font-black tracking-widest uppercase bg-indigo-500/5 text-indigo-400/80 border border-indigo-500/10 group-hover:border-indigo-500/30 transition-all">
                        {target.sector}
                      </span>
                    </div>

                    <div className="w-full lg:col-span-3 flex items-center justify-between lg:block">
                      <div className="lg:hidden text-[9px] font-black text-gray-600 uppercase tracking-widest">Thesis</div>
                      <div className="text-right lg:text-left">
                        <div className="text-sm lg:text-base text-gray-200 font-bold tracking-tight mb-0.5">{target.dealType}</div>
                        <div className="text-[9px] lg:text-[10px] font-black text-gray-600 uppercase tracking-[0.2em]">{target.timeframe} Range</div>
                      </div>
                    </div>

                    <div className="w-full lg:col-span-2 flex items-center justify-between lg:justify-end lg:text-right">
                      <span className="lg:hidden text-[9px] font-black text-gray-600 uppercase tracking-widest">Confidence</span>
                      <div className="flex items-center gap-4 lg:flex-col lg:items-end lg:gap-0">
                        <span className="text-2xl lg:text-4xl font-black bg-clip-text text-transparent bg-gradient-to-b from-white to-gray-800 leading-none tracking-tighter">
                          {target.priorityScore}
                        </span>
                        <div className="hidden lg:block w-20 h-1.5 bg-white/5 rounded-full mt-3 overflow-hidden p-[1px]">
                           <motion.div 
                             initial={{ width: 0 }}
                             animate={{ width: `${target.priorityScore}%` }}
                             className="h-full bg-indigo-500 shadow-[0_0_10px_rgba(79,70,229,0.5)] rounded-full" 
                           />
                        </div>
                      </div>
                    </div>

                    <div className="absolute right-6 top-1/2 -translate-y-1/2 lg:relative lg:right-0 lg:top-0 lg:translate-y-0 lg:col-span-1 flex justify-end">
                      <div className="w-8 h-8 lg:w-10 lg:h-10 rounded-xl lg:rounded-2xl bg-white/5 flex items-center justify-center text-gray-600 group-hover:text-white group-hover:bg-indigo-600 transition-all border border-white/5 group-hover:border-indigo-400 shadow-2xl active:scale-90">
                        <ChevronRight size={20} />
                      </div>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
              
              {filteredAndSortedTargets.length === 0 && (
                <div className="p-32 text-center flex flex-col items-center gap-8">
                   <div className="w-24 h-24 rounded-[2rem] bg-white/5 border border-white/10 flex items-center justify-center">
                       <Target size={48} className="text-gray-800" />
                   </div>
                   <div>
                       <p className="font-black text-2xl text-white mb-3 tracking-tighter">Negative Intelligence Match</p>
                       <p className="text-gray-500 font-medium max-w-sm mx-auto">No strategic entities match the current scoping parameters. Expand your Confidence threshold or Sector clusters.</p>
                   </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}



