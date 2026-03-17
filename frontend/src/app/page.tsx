"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { TrendingUp, Users, Building, AlertTriangle, ArrowRight, Zap, ChevronRight, MessageSquare, Target as TargetIcon, Activity, ShieldCheck, Cpu, Radio, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { SkeletonCard, SkeletonKPI } from "@/components/LoadingSkeleton";

import { Target } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

export default function Home() {
  const [targets, setTargets] = useState<Target[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(false);
  const router = useRouter();

  // Fetch targets from FastAPI backend
  useEffect(() => {
    fetch(`${API_URL}/api/targets`)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP error: ${res.status}`);
        return res.json();
      })
      .then(data => {
        setTargets(data.data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to fetch targets:", err);
        setFetchError(true);
        setLoading(false);
      });
  }, []);

  return (
    <div className="flex flex-col gap-10 w-full max-w-7xl mx-auto py-4">
      {/* Header */}
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-6 shrink-0">
        <div>
          <h1 className="text-5xl font-black tracking-tighter text-white mb-3 flex items-center gap-5">
            Aethelgard Engine
            <div className="flex items-center gap-2.5 px-4 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-[10px] text-indigo-400 font-black uppercase tracking-[0.2em]">
               <Radio size={14} className="animate-pulse" /> Intelligence Live
            </div>
          </h1>
          <p className="text-gray-400 text-lg font-medium max-w-2xl leading-relaxed">
            Proprietary origination control center. Calibrating <span className="text-white">short-term transaction windows</span> and relationship proximity in real-time.
          </p>
        </div>
        
        <div className="flex flex-col sm:flex-row gap-4 w-full md:w-auto">
          <button className="px-6 py-3 rounded-2xl bg-white/[0.03] border border-white/10 text-[11px] font-black uppercase tracking-widest text-white hover:bg-white/10 transition-all flex items-center justify-center gap-3 backdrop-blur-md">
            <Activity size={16} className="text-indigo-500" /> <span className="hidden sm:inline">System Diagnostics</span>
          </button>
          <button className="px-6 py-3 rounded-2xl bg-indigo-600 text-white shadow-[0_20px_40px_rgba(79,70,229,0.3)] hover:bg-indigo-500 transition-all flex items-center justify-center gap-3 font-black text-[11px] uppercase tracking-widest active:scale-95">
            <Sparkles size={16} /> Force Recalibration
          </button>
        </div>
      </header>

      {/* KPI Section */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {loading
          ? Array.from({ length: 4 }).map((_, i) => <SkeletonKPI key={i} />)
          : [
              { icon: Building, label: "Active Monitored", value: "2,408", trend: "+12%", color: "text-indigo-400" },
              { icon: AlertTriangle, label: "System Triggers", value: "45", trend: "+5", color: "text-amber-500" },
              { icon: Users, label: "Rel. Proximity", value: "891", trend: "+24", color: "text-purple-400" },
              { icon: TrendingUp, label: "Predicted M&A", value: "18", trend: "-2", color: "text-indigo-400" },
            ].map((card, idx) => (
              <motion.div
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.1, duration: 0.5 }}
                key={card.label}
                className="p-8 rounded-[2.5rem] bg-black/40 border border-white/10 backdrop-blur-2xl group hover:border-indigo-500/40 transition-all shadow-2xl relative overflow-hidden"
              >
                <div className="absolute top-0 right-0 p-6 opacity-[0.02] group-hover:opacity-[0.05] transition-opacity">
                   <card.icon size={80} />
                </div>
                <div className="flex justify-between items-start mb-8 relative z-10">
                  <div className={`p-3.5 rounded-2xl bg-white/5 border border-white/10 ${card.color}`}>
                    <card.icon size={24} />
                  </div>
                  <span className={`text-[10px] font-black px-2.5 py-1 rounded-xl border ${
                    card.trend.startsWith('+') ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                  }`}>
                    {card.trend}
                  </span>
                </div>
                <div className="text-4xl font-black text-white mb-2 tracking-tighter relative z-10">{card.value}</div>
                <div className="text-[10px] font-black text-gray-500 uppercase tracking-widest relative z-10">{card.label}</div>
              </motion.div>
            ))
        }
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-start">
        
        {/* Targets Feed */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
            <h2 className="text-xs font-black text-white uppercase tracking-[0.3em] flex items-center gap-4">
              <div className="hidden sm:block w-1.5 h-6 bg-indigo-600 rounded-full shadow-[0_0_15px_rgba(79,70,229,0.5)]" /> 
              High Confidence Origination Trajectories
            </h2>
            <button onClick={() => router.push("/targets")} className="w-full sm:w-auto text-[10px] font-black text-indigo-400 hover:text-indigo-300 uppercase tracking-widest transition-colors flex items-center justify-center gap-2 bg-indigo-500/5 px-5 py-2.5 rounded-2xl border border-indigo-500/10 hover:border-indigo-500/30">
              Intelligence Vault <ChevronRight size={16} />
            </button>
          </div>

          {fetchError && (
             <motion.div 
               initial={{ opacity: 0, scale: 0.95 }}
               animate={{ opacity: 1, scale: 1 }}
               className="p-8 rounded-[2.5rem] bg-rose-500/5 border border-rose-500/20 text-rose-300 flex items-center gap-6"
             >
                <div className="w-14 h-14 rounded-2xl bg-rose-500/10 flex items-center justify-center border border-rose-500/20 shadow-2xl">
                   <AlertTriangle size={28} className="text-rose-500" />
                </div>
                <div>
                   <div className="font-black uppercase tracking-widest text-xs mb-1 text-rose-500">Connectivity Error</div>
                   <div className="text-sm font-medium text-gray-400">Unable to establish secure tunnel to Aethelgard Internal Services. Verify host status.</div>
                </div>
             </motion.div>
          )}

          <div className="flex flex-col gap-5">
            {loading
              ? Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} />)
              : targets.slice(0, 3).map((target, idx) => (
              <motion.div 
                onClick={() => router.push(`/targets/${target.id}`)}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 + idx * 0.1 }}
                key={target.id}
                className="group p-10 rounded-[3rem] bg-black/40 border border-white/10 hover:border-indigo-500/40 transition-all cursor-pointer relative overflow-hidden backdrop-blur-3xl shadow-2xl active:scale-[0.99]"
              >
                <div className="flex justify-between items-start relative z-10">
                  <div className="flex-1">
                    <div className="flex items-center gap-5 mb-5">
                      <div className="w-16 h-16 rounded-[1.5rem] bg-white/5 border border-white/10 flex items-center justify-center text-gray-400 group-hover:text-indigo-400 group-hover:bg-indigo-500/10 group-hover:border-indigo-500/30 transition-all shadow-xl">
                         <Building size={28} />
                      </div>
                      <div>
                        <h3 className="text-3xl font-black text-white tracking-tighter group-hover:text-indigo-400 transition-colors">{target.name}</h3>
                        <div className="flex gap-3 items-center mt-2">
                          <span className="px-3 py-1 rounded-xl text-[10px] font-black tracking-widest uppercase bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                            {target.sector}
                          </span>
                          <span className="text-[10px] font-black text-gray-600 uppercase tracking-[0.2em]">{target.id}</span>
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex flex-wrap gap-3 mt-8">
                      {target.signals.map((signal) => (
                        <div key={signal} className="px-4 py-2 rounded-2xl bg-white/[0.03] text-gray-400 text-xs font-black uppercase tracking-widest flex items-center gap-2.5 border border-white/5 group-hover:bg-white/[0.05] transition-all">
                          <div className="w-2 h-2 rounded-full bg-indigo-500/50 shadow-[0_0_8px_rgba(79,70,229,0.5)]" />
                          {signal}
                        </div>
                      ))}
                    </div>
                  </div>
                  
                  <div className="flex flex-col items-end">
                    <span className="text-7xl font-black text-white leading-none tracking-tighter bg-clip-text text-transparent bg-gradient-to-b from-white to-gray-800">
                      {target.priorityScore}
                    </span>
                    <span className="text-[10px] uppercase tracking-[0.4em] text-indigo-400/80 font-black mt-3">
                      Confidence
                    </span>
                  </div>
                </div>

                <div className="mt-10 pt-8 border-t border-white/[0.05] flex flex-col md:flex-row justify-between items-start md:items-center gap-6 relative z-10">
                  <div className="flex gap-8 sm:gap-12">
                    <div className="space-y-1.5">
                      <span className="text-[10px] font-black text-gray-600 uppercase tracking-widest block">Core Thesis</span>
                      <span className="text-base text-gray-200 font-bold tracking-tight">{target.dealType}</span>
                    </div>
                    <div className="space-y-1.5">
                      <span className="text-[10px] font-black text-gray-600 uppercase tracking-widest block">Detection Window</span>
                      <span className="text-base text-gray-200 font-bold tracking-tight">{target.timeframe}</span>
                    </div>
                  </div>
                  
                  <button className="w-full md:w-auto flex items-center justify-center gap-3 px-8 py-3.5 rounded-2xl bg-white text-black font-black text-[11px] uppercase tracking-widest hover:bg-indigo-600 hover:text-white transition-all shadow-2xl shadow-black/50 active:scale-95 group/btn">
                    Open Intercept Data <ChevronRight size={18} className="group-hover/btn:translate-x-1 transition-transform" />
                  </button>
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Intelligence Sidebar */}
        <div className="lg:col-span-4 flex flex-col gap-10 sticky top-4">
           {/* Section Intensity */}
           <div className="p-10 rounded-[3rem] bg-black/40 border border-white/10 backdrop-blur-3xl shadow-2xl">
              <div className="flex items-center justify-between mb-10">
                 <h2 className="text-[11px] font-black text-white uppercase tracking-[0.3em] flex items-center gap-3">
                  <Activity size={18} className="text-indigo-400" /> Sector Volatility
                 </h2>
                 <ShieldCheck size={18} className="text-emerald-500/50" />
              </div>
              
              <div className="space-y-6">
                {[
                  { name: "Industrial Tech", val: 89, trend: "↑ 24%", color: "bg-indigo-500" },
                  { name: "Digital Health", val: 64, trend: "↑ 12%", color: "bg-purple-500" },
                  { name: "SaaS Clusters", val: 94, trend: "↑ 38%", color: "bg-indigo-600" },
                  { name: "FinTech Rollup", val: 42, trend: "↓ 4%", color: "bg-gray-600" },
                ].map((s) => (
                  <div key={s.name} className="group cursor-default">
                     <div className="flex justify-between items-center mb-4">
                        <span className="text-[11px] font-black text-gray-400 group-hover:text-white transition-colors uppercase tracking-widest">{s.name}</span>
                        <span className={`text-[10px] font-black px-2 py-0.5 rounded-lg ${s.trend.includes('↑') ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>{s.trend}</span>
                     </div>
                     <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden shadow-inner">
                        <motion.div 
                          initial={{ width: 0 }}
                          animate={{ width: `${s.val}%` }}
                          className={`h-full ${s.color} shadow-[0_0_12px_rgba(79,70,229,0.4)]`}
                        />
                     </div>
                  </div>
                ))}
              </div>

              <div className="mt-10 p-5 rounded-3xl bg-indigo-500/5 border border-indigo-500/10 flex items-center justify-between">
                 <div className="flex items-center gap-4">
                    <div className="p-2 rounded-xl bg-indigo-500/10">
                       <Cpu size={16} className="text-indigo-400" />
                    </div>
                    <div>
                       <div className="text-[10px] font-black text-white uppercase tracking-widest">Neural Load</div>
                       <div className="text-[9px] font-bold text-gray-600 uppercase mt-0.5">Processing 14M intercepts</div>
                    </div>
                 </div>
                 <span className="text-[10px] font-black text-emerald-500 border border-emerald-500/20 px-2.5 py-1 rounded-lg">OPTIMAL</span>
              </div>
            </div>

           {/* Copilot Action Card */}
           <motion.button 
             whileHover={{ y: -5 }}
             onClick={() => window.dispatchEvent(new CustomEvent("toggle-copilot"))}
             className="relative p-10 rounded-[3rem] bg-indigo-600 text-left shadow-[0_30px_60px_rgba(79,70,229,0.4)] border border-indigo-400 hover:bg-indigo-500 transition-all group overflow-hidden"
           >
              <div className="absolute top-0 right-0 p-10 opacity-10 group-hover:scale-125 group-hover:rotate-6 transition-all duration-700">
                 <MessageSquare size={160} />
              </div>
              
              <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/50 to-transparent pointer-events-none" />

              <div className="w-16 h-16 rounded-[1.5rem] bg-white/10 flex items-center justify-center text-white relative z-10 backdrop-blur-md mb-8 shadow-2xl">
                 <Zap size={32} />
              </div>
              <div className="relative z-10">
                 <h3 className="text-2xl font-black text-white leading-tight mb-4 tracking-tighter">Query Aethelgard</h3>
                 <p className="text-indigo-100 text-base font-medium leading-relaxed opacity-80 group-hover:opacity-100 transition-opacity">
                    "Identify French industrials with founders nearing age 65 and no clear succession plan."
                 </p>
              </div>
              <div className="flex items-center gap-3 text-white text-[11px] font-black uppercase tracking-[0.2em] mt-8 relative z-10 group-hover:translate-x-2 transition-transform">
                 Initialize Assistant <ChevronRight size={18} />
              </div>
           </motion.button>
        </div>

      </div>
    </div>
  );
}


