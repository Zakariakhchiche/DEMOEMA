"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, Target, Award, Users, Clock, Zap, Building, Crosshair, TrendingUp, AlertCircle, FileText, Share2, MoreVertical, ShieldCheck, ArrowRight, Radio, Fingerprint } from "lucide-react";
import { useParams } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

export default function TargetDetail() {
  const params = useParams();
  const id = params?.id as string;

  const [targetData, setTargetData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!id) return;
    
    setLoading(true);
    fetch(`${API_URL}/api/targets/${id}`)
      .then(res => {
        if (!res.ok) throw new Error();
        return res.json();
      })
      .then(json => {
        setTargetData(json.data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setError(true);
        setLoading(false);
      });
  }, [id]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-white">
        <div className="relative w-20 h-20 mb-8">
          <div className="absolute inset-0 border-4 border-indigo-500/10 rounded-full" />
          <div className="absolute inset-0 border-t-4 border-indigo-500 rounded-full animate-spin shadow-[0_0_30px_rgba(79,70,229,0.5)]" />
        </div>
        <span className="font-black uppercase tracking-[0.4em] text-[10px] text-indigo-400">Decrypting Node {id}...</span>
      </div>
    );
  }

  if (error || !targetData) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] text-white">
          <div className="w-20 h-20 rounded-[2rem] bg-rose-500/10 border border-rose-500/20 flex items-center justify-center mb-6 shadow-2xl">
            <AlertCircle size={40} className="text-rose-500" />
          </div>
          <h1 className="text-3xl font-black mb-3 tracking-tighter">Target Intercept Failed</h1>
          <p className="text-gray-400 mb-8 max-w-sm text-center font-medium leading-relaxed">Intelligence node {id} is currently unreachable or does not exist in the primary vault.</p>
          <Link href="/" className="px-8 py-4 bg-indigo-600 text-white rounded-[2rem] hover:bg-indigo-500 transition-all font-black text-xs uppercase tracking-widest shadow-2xl shadow-indigo-600/30">
            Return to Command Center
          </Link>
        </div>
      );
  }

  return (
    <div className="flex flex-col gap-12 w-full max-w-7xl mx-auto pb-32 pt-6 px-4">
      {/* Top Navigation & Status */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-8 sm:gap-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6">
          <Link href="/targets" className="w-12 h-12 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-all backdrop-blur-xl group shrink-0">
            <ArrowLeft size={20} className="group-hover:-translate-x-1 transition-transform" />
          </Link>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-4 mb-3">
              <h1 className="text-3xl md:text-5xl font-black tracking-tighter text-white truncate max-w-full">{targetData.name}</h1>
              <div className="px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-[10px] text-indigo-400 font-black uppercase tracking-[0.2em] whitespace-nowrap">
                {targetData.sector} Hub
              </div>
            </div>
            <div className="flex flex-col sm:flex-row sm:items-center gap-4">
               <div className="flex items-center gap-2.5 px-3 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-black uppercase tracking-widest w-fit">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> Live Analysis
               </div>
               <p className="text-gray-500 text-[10px] sm:text-xs font-black uppercase tracking-[0.2em] break-all">
                  Vault: <span className="text-gray-300">Classified</span> • Protocol: <span className="text-gray-300">Aethelgard-7</span>
               </p>
            </div>
          </div>
        </div>
        
        <div className="flex gap-4 w-full lg:w-auto">
          <button className="flex-1 lg:flex-none w-12 h-12 rounded-2xl bg-white/[0.03] border border-white/10 text-gray-400 hover:text-white hover:bg-white/10 transition-all flex items-center justify-center">
            <Share2 size={20} />
          </button>
          <button className="flex-[4] lg:flex-none flex items-center justify-center gap-3 px-8 py-3 rounded-2xl bg-indigo-600 text-white font-black text-xs uppercase tracking-widest shadow-2xl shadow-indigo-600/40 hover:bg-indigo-500 transition-all active:scale-95">
            <TrendingUp size={18} /> Signal Fetch
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
        
        {/* Left Column - Core Metrics */}
        <div className="lg:col-span-4 flex flex-col gap-8 order-2 lg:order-1">
          
          {/* Main Priority Card */}
          <div className="p-6 md:p-10 rounded-[2.5rem] md:rounded-[3rem] bg-black/40 border border-indigo-500/20 relative overflow-hidden group shadow-2xl backdrop-blur-3xl">
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-600/10 via-transparent to-transparent opacity-50" />
            
            <div className="relative z-10">
              <div className="flex justify-between items-center mb-12">
                <div className="p-4 rounded-[1.5rem] bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shadow-xl">
                  <Target size={28} />
                </div>
                <div className="text-right">
                  <div className="text-[10px] font-black uppercase tracking-[0.3em] text-indigo-400/80 mb-1">Confidence Layer</div>
                  <div className="text-xs font-black text-white flex items-center gap-2 justify-end">
                    <ShieldCheck size={14} className="text-emerald-500" /> 94.2% AI INTEGRITY
                  </div>
                </div>
              </div>

              <div className="flex flex-col items-center mb-12">
                <div className="relative">
                  <svg className="w-56 h-56 transform -rotate-90 filter drop-shadow-[0_0_15px_rgba(79,70,229,0.3)]">
                    <circle cx="112" cy="112" r="102" stroke="rgba(255,255,255,0.03)" strokeWidth="14" fill="transparent" />
                    <motion.circle 
                      initial={{ strokeDashoffset: 2 * Math.PI * 102 }}
                      animate={{ strokeDashoffset: 2 * Math.PI * 102 * (1 - targetData.priorityScore / 100) }}
                      transition={{ duration: 1.5, ease: "easeOut" }}
                      cx="112" cy="112" r="102" 
                      stroke="url(#gradient-ring-deep)" 
                      strokeWidth="14" 
                      strokeDasharray={2 * Math.PI * 102} 
                      strokeLinecap="round" 
                      fill="transparent" 
                    />
                    <defs>
                      <linearGradient id="gradient-ring-deep" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#6366f1" />
                        <stop offset="100%" stopColor="#a855f7" />
                      </linearGradient>
                    </defs>
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-7xl font-black text-white leading-none tracking-tighter bg-clip-text text-transparent bg-gradient-to-b from-white to-gray-500">{targetData.priorityScore}</span>
                    <span className="text-indigo-400/60 text-[10px] font-black uppercase tracking-[0.4em] mt-3">Confidence</span>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-5">
                {Object.entries(targetData.scores).map(([key, val]: any) => (
                  <div key={key} className="group/metric">
                    <div className="flex justify-between text-[10px] font-black uppercase tracking-[0.2em] mb-3 text-gray-500 group-hover/metric:text-gray-300 transition-colors">
                      <span className="capitalize">{key}</span>
                      <span className="text-indigo-400/80">{val}%</span>
                    </div>
                    <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden p-[1px]">
                      <motion.div 
                        initial={{ width: 0 }}
                        animate={{ width: `${val}%` }}
                        transition={{ duration: 1, delay: 0.5 }}
                        className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full shadow-[0_0_10px_rgba(79,70,229,0.4)]" 
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Quick Metrics Grid */}
          <div className="grid grid-cols-2 gap-6">
            <div className="p-8 rounded-[2.5rem] bg-black/40 border border-white/10 backdrop-blur-3xl shadow-2xl relative overflow-hidden group">
               <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:scale-110 transition-transform">
                  <Zap size={60} />
               </div>
               <Zap className="text-amber-500 mb-6" size={24} />
               <div className="text-[10px] text-gray-600 font-black uppercase tracking-widest mb-1.5">Intercept Speed</div>
               <div className="text-xl font-black text-white tracking-tighter italic uppercase">Accelerating</div>
            </div>
            <div className="p-8 rounded-[2.5rem] bg-black/40 border border-white/10 backdrop-blur-3xl shadow-2xl relative overflow-hidden group">
               <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:scale-110 transition-transform">
                  <Users size={60} />
               </div>
               <Users className="text-indigo-500 mb-6" size={24} />
               <div className="text-[10px] text-gray-600 font-black uppercase tracking-widest mb-1.5">Network Node</div>
               <div className="text-xl font-black text-white tracking-tighter italic uppercase">4 Warm Connections</div>
            </div>
          </div>

        </div>

        {/* Center/Right Column - Intelligence & Narrative */}
        <div className="lg:col-span-8 flex flex-col gap-10 order-1 lg:order-2">
          
          {/* Intelligence Deep Dive */}
          <div className="p-6 md:p-12 rounded-[2.5rem] md:rounded-[3.5rem] bg-black/40 border border-white/10 backdrop-blur-3xl shadow-2xl relative overflow-hidden">
            <div className="absolute top-0 right-0 p-12 opacity-[0.02]">
               <Fingerprint size={200} />
            </div>
            
            <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-8 md:mb-12 relative z-10 gap-4">
              <h3 className="text-xl md:text-2xl font-black text-white flex items-center gap-4 tracking-tighter text-left">
                <div className="w-1.5 h-8 bg-indigo-600 rounded-full shadow-[0_0_15px_rgba(79,70,229,0.5)] shrink-0" />
                Strategic Thesis
              </h3>
              <div className="flex items-center gap-3 px-4 py-2 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-[11px] font-black uppercase tracking-widest w-fit">
                <Radio size={14} className="animate-pulse" /> Live Synthesis
              </div>
            </div>
            
            <div className="relative z-10">
              <p className="text-gray-300 leading-relaxed text-lg md:text-xl mb-12 font-medium tracking-tight text-left">
                {targetData.name} presents a <span className="text-white font-black underline decoration-indigo-500 decoration-2 underline-offset-8">high-probability intercept opportunity</span>. Neural engine identified convergence of <span className="text-indigo-400 font-black">executive churn</span> and <span className="text-indigo-400 font-black">pre-transactional structuring</span>. 
              </p>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-8 my-8 md:my-12">
                <div className="p-6 md:p-8 rounded-[2rem] md:rounded-[2.5rem] bg-indigo-500/5 border border-indigo-500/20 group hover:bg-indigo-500/10 transition-all">
                  <h4 className="text-white font-black text-[10px] uppercase tracking-[0.2em] mb-4 md:mb-6 flex items-center gap-3 text-left">
                    <Zap size={16} className="text-amber-500" /> Catalytic Anomalies
                  </h4>
                  <ul className="text-xs md:text-sm text-gray-400 space-y-4 md:space-y-5 text-left">
                    <li className="flex gap-4 group/li">
                      <div className="w-1.5 h-1.5 rounded-full bg-indigo-600 mt-2 shrink-0 group-hover/li:scale-150 transition-transform" />
                      <span className="leading-relaxed">CFO transition detected; historical profile aligns with private equity exit strategies.</span>
                    </li>
                    <li className="flex gap-4 group/li">
                      <div className="w-1.5 h-1.5 rounded-full bg-indigo-600 mt-2 shrink-0 group-hover/li:scale-150 transition-transform" />
                      <span className="leading-relaxed">Unusual dormant entity activation suggests tax-efficient structuring for M&A.</span>
                    </li>
                  </ul>
                </div>
                <div className="p-6 md:p-8 rounded-[2rem] md:rounded-[2.5rem] bg-rose-500/5 border border-rose-500/20 group hover:bg-rose-500/10 transition-all">
                  <h4 className="text-white font-black text-[10px] uppercase tracking-[0.2em] mb-4 md:mb-6 flex items-center gap-3 text-left">
                    <Crosshair size={16} className="text-rose-500" /> Investment Precision
                  </h4>
                  <ul className="text-xs md:text-sm text-gray-400 space-y-4 md:space-y-5 text-left">
                    <li className="flex gap-4 group/li">
                      <div className="w-1.5 h-1.5 rounded-full bg-rose-600 mt-2 shrink-0 group-hover/li:scale-150 transition-transform" />
                      <span className="leading-relaxed">Core component fit for "Project Nexus" rollup strategy within the EU healthcare cluster.</span>
                    </li>
                    <li className="flex gap-4 group/li">
                      <div className="w-1.5 h-1.5 rounded-full bg-rose-600 mt-2 shrink-0 group-hover/li:scale-150 transition-transform" />
                      <span className="leading-relaxed">Relationship pathing reveals direct board-level access through established alumni networks.</span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          {/* Sub-surface Signal Feed */}
          <div className="p-6 md:p-12 rounded-[2.5rem] md:rounded-[3.5rem] bg-black/40 border border-white/10 backdrop-blur-3xl shadow-2xl">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 md:mb-12 gap-4">
              <h3 className="text-xl md:text-2xl font-black text-white flex items-center gap-4 tracking-tighter text-left">
                <Clock className="text-gray-500" size={24} /> Signal Chronology
              </h3>
              <button className="w-full sm:w-auto text-[10px] font-black text-indigo-400 uppercase tracking-widest hover:text-indigo-300 bg-indigo-500/5 px-4 py-2 rounded-xl border border-indigo-500/10">
                Full Export
              </button>
            </div>
            
            <div className="relative pl-12 space-y-12">
              {/* Vertical Stream Line */}
              <div className="absolute left-[23px] top-2 bottom-2 w-px bg-gradient-to-b from-indigo-500 via-white/10 to-transparent" />
              
              {targetData.signals.map((signal: string, idx: number) => (
                <motion.div 
                  initial={{ opacity: 0, x: -10 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: idx * 0.1 }}
                  key={idx} 
                  className="relative group/signal"
                >
                  <div className="absolute -left-[35px] top-1 w-8 h-8 rounded-xl bg-black border border-white/10 flex items-center justify-center z-10 shadow-2xl group-hover/signal:border-indigo-500 transition-all">
                    <div className="w-2 h-2 rounded-full bg-indigo-500 shadow-[0_0_10px_rgba(79,70,229,0.5)] group-hover/signal:scale-150 transition-transform" />
                  </div>
                  <div>
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-lg font-black text-white tracking-tight">{signal}</span>
                      <span className="text-[10px] text-gray-700 font-bold uppercase tracking-[0.2em]">{idx === 0 ? "LIVE • 120m ago" : "D-1 RECORD"}</span>
                    </div>
                    <p className="text-gray-400 text-sm leading-relaxed max-w-2xl font-medium">
                      Automated intercept confirmed high-relevance match via <span className="text-indigo-400 font-black">{idx === 0 ? "proprietary data-lakes" : "regulatory filings"}</span>. Sentiment vector indicates a <span className="text-white font-bold italic">{idx === 0 ? "shift in capital allocation" : "structural hardening"}</span>.
                    </p>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>

          {/* Critical Actions */}
          <div className="flex flex-col lg:flex-row justify-between items-center p-8 md:p-12 rounded-[2.5rem] md:rounded-[3.5rem] bg-indigo-600 shadow-[0_40px_80px_rgba(79,70,229,0.3)] border border-indigo-400 relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-500 to-transparent pointer-events-none" />
            
            <div className="relative z-10 mb-8 lg:mb-0 text-center lg:text-left">
               <h4 className="text-xl md:text-2xl font-black text-white tracking-tighter mb-2">Protocol Initiation</h4>
               <p className="text-indigo-100 font-medium opacity-80 max-w-sm text-sm md:text-base">Secure ownership or generate a PDF dossier for the investment committee.</p>
            </div>
            
            <div className="flex flex-col sm:flex-row justify-center gap-4 sm:gap-6 relative z-10 w-full lg:w-auto">
               <button className="flex-1 sm:flex-none px-10 py-4 rounded-[2rem] bg-white/10 border border-white/20 text-white font-black text-xs uppercase tracking-widest hover:bg-white/20 transition-all backdrop-blur-xl active:scale-95">
                  Sector Lead
               </button>
                <Link href={`/targets/${id}/report`} className="flex-1 sm:flex-none px-12 py-4 rounded-[2rem] bg-white text-black font-black text-xs uppercase tracking-widest hover:bg-indigo-50 transition-all flex items-center justify-center gap-3 shadow-2xl active:scale-95 group/btn">
                  PDF Dossier <ArrowRight size={18} className="group-hover/btn:translate-x-1 transition-transform" />
                </Link>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
