"use client";

import { useState, useMemo, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Activity, Bell, Filter, Search, ShieldAlert, ArrowUpRight, Clock, MapPin, Zap, TrendingUp, Globe, AlertCircle, Radio } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

// --- Types ---
interface Signal {
  id: string;
  type: string;
  title: string;
  time: string;
  source: string;
  severity: "high" | "medium" | "low";
  location: string;
  tags: string[];
}

export default function SignalsPage() {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("All");
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`${API_URL}/api/signals`)
      .then(res => res.json())
      .then(json => {
        setSignals(json.data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to fetch signals:", err);
        setLoading(false);
      });
  }, []);

  const filteredSignals = useMemo(() => {
    return signals.filter(s => {
      const matchSearch = s.title.toLowerCase().includes(search.toLowerCase()) || 
                          s.type.toLowerCase().includes(search.toLowerCase());
      const matchFilter = filter === "All" || s.severity === filter.toLowerCase();
      return matchSearch && matchFilter;
    });
  }, [search, filter, signals]);

  return (
    <div className="flex flex-col gap-8 w-full max-w-7xl mx-auto py-4 h-[calc(100vh-8rem)]">
      {/* Header */}
      <header className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 shrink-0">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-4">
            <h1 className="text-3xl md:text-4xl font-black tracking-tight text-white flex items-center gap-4">
              Intelligence Feed
            </h1>
            <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-[10px] text-indigo-400 font-black uppercase tracking-[0.2em]">
               <Radio size={12} className="animate-pulse" /> Live Stream
            </div>
          </div>
          <p className="text-gray-400 text-sm font-medium">
            Real-time anomaly detection and strategic market triggers calibrated by Aethelgard.
          </p>
        </div>
        
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative group w-full sm:w-80">
            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-indigo-400 transition-colors">
               <Search size={18} />
            </span>
            <input 
               type="text" 
               value={search}
               onChange={(e) => setSearch(e.target.value)}
               placeholder="Search intercept data..." 
               className="w-full bg-white/[0.03] border border-white/10 rounded-2xl py-3 pl-12 pr-4 text-sm text-gray-200 placeholder-gray-600 outline-none focus:border-indigo-500/50 focus:bg-white/[0.05] transition-all"
            />
          </div>
          <button className="px-5 py-3 rounded-2xl bg-white/[0.03] border border-white/10 text-[10px] font-black uppercase tracking-widest text-white hover:bg-white/10 transition-all flex items-center justify-center gap-2">
            <AlertCircle size={16} /> <span className="sm:hidden lg:inline">Notification Matrix</span>
          </button>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 flex-1 min-h-0">
        
        {/* Main Feed */}
        <div className="lg:col-span-8 bg-black/40 border border-white/10 rounded-[2.5rem] overflow-hidden flex flex-col shadow-2xl backdrop-blur-xl">
          <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between bg-white/[0.02]">
             <div className="flex gap-2">
                {["All", "High", "Medium", "Low"].map((lvl) => (
                  <button 
                    key={lvl}
                    onClick={() => setFilter(lvl)}
                    className={`px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all border
                      ${filter === lvl 
                        ? "bg-indigo-500/10 border-indigo-500/30 text-indigo-400" 
                        : "bg-white/5 border-transparent text-gray-500 hover:bg-white/10 hover:text-gray-300"
                      }
                    `}
                  >
                    {lvl} {lvl === "All" ? "Alerts" : "Severity"}
                  </button>
                ))}
             </div>
             <div className="text-[10px] font-black text-gray-600 uppercase tracking-widest">
                Scanning 14.2M datapoints / sec
             </div>
          </div>
          
          <div className="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar">
            <AnimatePresence mode="popLayout">
              {filteredSignals.map((signal) => (
                <motion.div 
                  layout
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.98 }}
                  key={signal.id} 
                  className="p-6 rounded-[2rem] bg-white/[0.02] border border-white/10 hover:border-indigo-500/30 transition-all group flex gap-6 items-start relative overflow-hidden active:scale-[0.99]"
                >
                  <div className={`absolute top-0 left-0 w-1 h-full
                    ${signal.severity === 'high' ? 'bg-indigo-500 shadow-[0_0_15px_rgba(99,102,241,0.5)]' : ''}
                    ${signal.severity === 'medium' ? 'bg-purple-500' : ''}
                    ${signal.severity === 'low' ? 'bg-gray-700' : ''}
                  `} />

                  <div className="flex-shrink-0">
                    <div className={`w-14 h-14 rounded-2xl flex items-center justify-center border transition-all
                      ${signal.severity === 'high' ? 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400 group-hover:bg-indigo-600 group-hover:text-white' : 'bg-white/5 border-white/5 text-gray-500'}
                    `}>
                      <Bell size={22} />
                    </div>
                  </div>
                  
                  <div className="flex-1">
                    <div className="flex items-center gap-4 mb-3">
                      <span className={`text-[9px] font-black uppercase tracking-[0.2em] px-2.5 py-1 rounded-lg
                        ${signal.severity === 'high' ? 'bg-indigo-500 text-white' : 'bg-white/10 text-gray-400'}
                      `}>
                        {signal.type}
                      </span>
                      <span className="text-[10px] font-black text-gray-600 flex items-center gap-2 uppercase tracking-[0.2em]">
                        <Clock size={12} /> {signal.time}
                      </span>
                    </div>
                    
                    <h3 className="text-lg md:text-xl font-black text-white mb-4 group-hover:text-indigo-400 transition-colors tracking-tight">
                      {signal.title}
                    </h3>
                    
                    <div className="flex flex-wrap items-center gap-6">
                      <div className="flex items-center gap-2 text-[10px] font-black text-gray-500 uppercase tracking-widest bg-white/5 px-3 py-1.5 rounded-xl border border-white/5">
                        <Globe size={14} className="opacity-50" /> {signal.location}
                      </div>
                      <div className="flex items-center gap-2 text-[10px] font-black text-gray-500 uppercase tracking-widest">
                        <ShieldAlert size={14} className="opacity-50 text-indigo-500" /> {signal.source}
                      </div>
                      <div className="flex gap-2 ml-auto">
                        {signal.tags.map(tag => (
                          <span key={tag} className="text-[9px] font-black text-gray-500 bg-indigo-500/5 px-2 py-1 rounded-md border border-indigo-500/10 uppercase tracking-widest">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center self-center">
                    <button className="w-12 h-12 rounded-2xl bg-white/5 group-hover:bg-indigo-600 text-gray-600 group-hover:text-white flex items-center justify-center transition-all border border-white/10 group-hover:border-indigo-400 shadow-xl active:scale-90">
                       <ArrowUpRight size={24} />
                    </button>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {filteredSignals.length === 0 && (
              <div className="p-20 text-center flex flex-col items-center gap-6">
                 <div className="w-20 h-20 bg-white/5 rounded-[2rem] flex items-center justify-center border border-white/10">
                    <ShieldAlert size={40} className="text-gray-700" />
                 </div>
                 <div>
                   <h2 className="text-white font-black text-2xl mb-2 tracking-tighter">Silence in the Wire</h2>
                   <p className="text-gray-500 max-w-sm mx-auto font-medium">No signals matching your current filters have reached the threshold. Engine reliability: 99.8%.</p>
                 </div>
              </div>
            )}
          </div>
        </div>

        {/* Sidebar Analytics */}
        <div className="lg:col-span-4 flex flex-col gap-8 overflow-y-auto custom-scrollbar">
          <div className="p-8 rounded-[2.5rem] bg-black/40 border border-white/10 shadow-2xl backdrop-blur-xl">
             <div className="flex items-center justify-between mb-8">
                <h3 className="text-[10px] font-black text-gray-500 uppercase tracking-[0.2em] flex items-center gap-2">
                  <TrendingUp size={16} className="text-indigo-400" /> Market Volatility
                </h3>
                <Zap size={16} className="text-indigo-500 animate-pulse" />
             </div>
             
             <div className="space-y-6">
                <div className="flex items-end gap-3">
                  <span className="text-6xl font-black text-white leading-none tracking-tighter">
                    84.2
                  </span>
                  <div className="flex flex-col">
                    <span className="text-[10px] text-emerald-500 font-black uppercase mb-1">↑ 14%</span>
                    <span className="text-[10px] text-gray-600 font-black uppercase tracking-widest">Signal Index</span>
                  </div>
                </div>
                
                <div className="p-4 rounded-3xl bg-indigo-500/5 border border-indigo-500/10">
                   <p className="text-[11px] text-indigo-200/60 leading-relaxed font-bold italic">
                     "Significant uptick in holding vehicle creation across DACH industrials. Probability of carve-out wave: 74%."
                   </p>
                </div>
             </div>
          </div>

          <div className="p-8 rounded-[2.5rem] bg-black/40 border border-white/10 shadow-2xl backdrop-blur-xl flex-1 flex flex-col">
            <h3 className="text-[10px] font-black text-gray-500 mb-8 uppercase tracking-[0.2em] flex items-center gap-2">
               <Globe size={16} className="text-indigo-400" /> Sector Heat
            </h3>
            <div className="space-y-6 flex-1">
               {[
                 { name: "Industrial Tech", trend: "Severe", color: "bg-indigo-500", val: "95%" },
                 { name: "MedTech Carveouts", trend: "High", color: "bg-purple-500", val: "72%" },
                 { name: "SaaS Clusters", trend: "Medium", color: "bg-gray-600", val: "45%" },
                 { name: "EU Logistics", trend: "Low", color: "bg-gray-800", val: "20%" },
               ].map((zone) => (
                 <div key={zone.name} className="group cursor-default">
                    <div className="flex justify-between text-[11px] font-black text-gray-400 mb-3 group-hover:text-white transition-colors uppercase tracking-widest">
                      <span>{zone.name}</span>
                      <span className="text-indigo-400">{zone.trend}</span>
                    </div>
                    <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
                      <motion.div 
                        initial={{ width: 0 }}
                        animate={{ width: zone.val }}
                        className={`h-full ${zone.color} shadow-[0_0_10px_rgba(0,0,0,0.5)]`} 
                      />
                    </div>
                 </div>
               ))}
            </div>
            
            <button className="mt-10 w-full py-4 rounded-3xl bg-indigo-600 text-white font-black text-[10px] uppercase tracking-widest hover:bg-indigo-500 transition-all shadow-xl shadow-indigo-600/20 active:scale-95">
               Download Intelligence Report
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}

