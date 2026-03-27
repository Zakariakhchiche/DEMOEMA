"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { 
  ArrowLeft, Target, ShieldCheck, Zap, TrendingUp, AlertCircle, 
  Share2, ArrowRight, Radio, Fingerprint, Activity, Clock, 
  Users, Briefcase, Crosshair, MapPin, Gauge, FileText, AlertTriangle
} from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { Target as TargetType } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

export default function TargetDetail() {
  const params = useParams();
  const router = useRouter();
  const [id, setId] = useState<string>("");

  useEffect(() => {
    if (params && typeof params.id === 'string') {
      setId(params.id);
    }
  }, [params]);

  const [targetData, setTargetData] = useState<TargetType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [processingAction, setProcessingAction] = useState<string | null>(null);
  const [notification, setNotification] = useState<{message: string, type: 'success' | 'info'} | null>(null);

  useEffect(() => {
    if (notification) {
      const timer = setTimeout(() => setNotification(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [notification]);

  const handleAction = (name: string, message: string) => {
    setProcessingAction(name);
    setTimeout(() => {
      setProcessingAction(null);
      setNotification({ message, type: 'success' });
    }, 1500);
  };

  useEffect(() => {
    if (!id) return;
    
    setLoading(true);
    fetch(`/api/targets/${id}`)
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
        <span className="font-black uppercase tracking-[0.4em] text-[10px] text-indigo-400">Initializing EDRCF Intercept Node {id}...</span>
      </div>
    );
  }

  if (error || !targetData) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] text-white">
          <div className="w-20 h-20 rounded-[2rem] bg-rose-500/10 border border-rose-500/20 flex items-center justify-center mb-6 shadow-2xl">
            <AlertCircle size={40} className="text-rose-500" />
          </div>
          <h1 className="text-3xl font-black mb-3 tracking-tighter">Intercept Failed</h1>
          <p className="text-gray-400 mb-8 max-w-sm text-center font-medium leading-relaxed">Intelligence node {id} is currently unreachable or does not exist in the primary vault.</p>
          <Link href="/" className="px-8 py-4 bg-indigo-600 text-white rounded-[2rem] hover:bg-indigo-500 transition-all font-black text-xs uppercase tracking-widest shadow-2xl shadow-indigo-600/30">
            Return to Command Center
          </Link>
        </div>
      );
  }

  const getPriorityColor = (level: string) => {
    if (level === "Strong Opportunity") return "text-emerald-400 bg-emerald-500/10 border-emerald-500/20";
    if (level === "Priority Target") return "text-indigo-400 bg-indigo-500/10 border-indigo-500/20";
    if (level === "Preparation Needed") return "text-amber-400 bg-amber-500/10 border-amber-500/20";
    return "text-gray-400 bg-white/5 border-white/10";
  };

  return (
    <div className="flex flex-col gap-12 w-full max-w-7xl mx-auto pb-32 pt-6 px-4 relative">
      {/* Toast Notification */}
      <AnimatePresence>
        {notification && (
          <motion.div 
            initial={{ opacity: 0, y: 50, x: '-50%' }}
            animate={{ opacity: 1, y: 0, x: '-50%' }}
            exit={{ opacity: 0, y: 20, x: '-50%' }}
            className="fixed bottom-10 left-1/2 z-[200] px-6 py-3 rounded-2xl bg-indigo-600 text-white font-black text-[10px] uppercase tracking-widest shadow-2xl flex items-center gap-3 border border-indigo-400 backdrop-blur-xl"
          >
            <ShieldCheck size={16} /> {notification.message}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-8 sm:gap-6 border-b border-white/5 pb-12">
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6">
          <button onClick={() => router.push('/targets')} className="w-12 h-12 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-all backdrop-blur-xl group shrink-0">
            <ArrowLeft size={20} className="group-hover:-translate-x-1 transition-transform" />
          </button>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-4 mb-3">
              <h1 className="text-3xl md:text-5xl font-black tracking-tighter text-white truncate max-w-full uppercase italic">{targetData.name}</h1>
              <div className={`px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-[0.2em] border ${getPriorityColor(targetData.priorityLevel)}`}>
                {targetData.priorityLevel}
              </div>
            </div>
            <div className="flex flex-col sm:flex-row sm:items-center gap-4">
               <div className="flex items-center gap-2.5 px-3 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-[10px] font-black uppercase tracking-widest w-fit">
                  {targetData.sector} • EDRCF Radar V5.0
               </div>
               <p className="text-gray-500 text-[10px] sm:text-xs font-black uppercase tracking-[0.2em]">
                  ID: <span className="text-gray-300">{targetData.id.toUpperCase()}</span> • Window: <span className="text-white">{targetData.analysis.window}</span>
               </p>
            </div>
          </div>
        </div>
        
        <div className="flex gap-4 w-full lg:w-auto">
          <button 
            onClick={() => handleAction('share', 'Dossier link copied')}
            className="flex-1 lg:flex-none w-14 h-14 rounded-2xl bg-white/[0.03] border border-white/10 text-gray-400 hover:text-white hover:bg-white/10 transition-all flex items-center justify-center shadow-xl"
          >
            <Share2 size={24} />
          </button>
          <button 
            disabled={processingAction === 'fetch'}
            onClick={() => handleAction('fetch', 'Radar synchronized')}
            className="flex-[4] lg:flex-none flex items-center justify-center gap-3 px-10 py-4 rounded-2xl bg-indigo-600 text-white font-black text-xs uppercase tracking-widest shadow-2xl shadow-indigo-600/40 hover:bg-indigo-500 transition-all active:scale-95 disabled:opacity-50"
          >
            {processingAction === 'fetch' ? (
              <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
            ) : (
              <Activity size={20} />
            )}
            {processingAction === 'fetch' ? 'Scanning...' : 'Radar Refresh'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
        
        {/* Left Column - Origination Card */}
        <div className="lg:col-span-4 flex flex-col gap-8">
          <div className="p-10 rounded-[3rem] bg-black/40 border border-indigo-500/20 relative overflow-hidden group shadow-2xl backdrop-blur-3xl">
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-600/10 via-transparent to-transparent opacity-50" />
            
            <div className="relative z-10">
              <div className="flex justify-between items-center mb-12">
                <div className="p-4 rounded-2xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  <Fingerprint size={32} />
                </div>
                <div className="text-right">
                  <div className="text-[10px] font-black uppercase tracking-[0.3em] text-indigo-400/80 mb-1">Intelligence Integrity</div>
                  <div className="text-xs font-black text-white flex items-center gap-2 justify-end">
                    <ShieldCheck size={14} className="text-emerald-500" /> 100% SECURE
                  </div>
                </div>
              </div>

              <div className="flex flex-col items-center mb-12">
                <div className="relative">
                  <div className="flex flex-col items-center">
                    <span className="text-7xl font-black text-white leading-none tracking-tighter mb-2">{targetData.globalScore}</span>
                    <span className="text-[10px] font-black text-indigo-400/60 uppercase tracking-[0.4em]">Global Score</span>
                  </div>
                </div>
                <div className="mt-12 flex flex-col items-center">
                   <span className="text-[10px] font-black text-gray-600 uppercase tracking-widest mb-4">Priority Status</span>
                   <div className="text-lg font-black text-white px-6 py-2 rounded-2xl bg-white/5 border border-white/10 italic">
                      {targetData.priorityLevel}
                   </div>
                </div>
              </div>

              <div className="space-y-6 mt-16 border-t border-white/[0.05] pt-12">
                   <div className="flex justify-between items-center px-4">
                     <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Active Cluster</span>
                     <div className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                        <span className="text-[10px] font-black text-white uppercase tracking-widest">{targetData.sector}</span>
                     </div>
                   </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column - Deep Dive */}
        <div className="lg:col-span-8 flex flex-col gap-10">
           {/* Strategic Thesis */}
           <section className="p-12 rounded-[4rem] bg-white/[0.02] border border-white/10 relative overflow-hidden group hover:border-indigo-500/30 transition-all">
              <div className="absolute top-0 right-10 bottom-0 w-1/3 bg-gradient-to-l from-indigo-600/5 to-transparent skew-x-12" />
              <h2 className="text-xs font-black uppercase tracking-[0.4em] text-gray-500 mb-10 flex items-center gap-4">
                 <span className="w-10 h-px bg-white/10" /> 01. Strategic Thesis
              </h2>
              <div className="space-y-12 relative z-10">
                 <div>
                    <div className="text-[10px] font-black text-indigo-400 uppercase tracking-[0.3em] mb-4">Probable Technical Angle</div>
                    <div className="text-4xl font-black text-white tracking-tighter uppercase italic leading-tight">{targetData.analysis.type}</div>
                 </div>
                 <p className="text-xl font-medium leading-relaxed text-gray-300 border-l border-indigo-500/30 pl-8">
                   "{targetData.analysis.narrative}"
                 </p>
              </div>
           </section>

           <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
              {/* Conviction Indicators */}
              <section className="p-12 rounded-[4rem] bg-white/[0.02] border border-white/10">
                 <h2 className="text-xs font-black uppercase tracking-[0.4em] text-gray-500 mb-10 flex items-center gap-4">
                    <Radio size={16} /> 02. Conviction Indicators
                 </h2>
                 <div className="space-y-4">
                    {targetData.topSignals.map((signal, i) => (
                      <div key={i} className="p-6 rounded-3xl bg-white/[0.03] border border-white/5 hover:border-indigo-500/20 transition-all group/signal">
                         <div className="text-[9px] font-black text-gray-500 uppercase tracking-widest mb-2 group-hover/signal:text-indigo-400 transition-colors uppercase">{signal.family}</div>
                         <div className="text-sm font-bold text-gray-200 uppercase tracking-tight">{signal.label}</div>
                      </div>
                    ))}
                 </div>
              </section>

              {/* Strategic Activation */}
              <section className="p-12 rounded-[4rem] bg-indigo-600 text-white shadow-2xl relative overflow-hidden group">
                 <div className="absolute -top-10 -right-10 opacity-10 group-hover:scale-110 transition-transform duration-700">
                    <Crosshair size={120} />
                 </div>
                 <h4 className="text-xs font-black uppercase tracking-widest mb-10 flex items-center gap-3">
                   <Crosshair size={18} /> 03. Strategic Activation
                 </h4>
                 <div className="space-y-8 relative z-10">
                    <div>
                       <div className="text-[9px] font-black text-indigo-200 uppercase tracking-widest mb-2 opacity-60">Approach Angle</div>
                       <div className="text-sm font-bold leading-relaxed">{targetData.activation.approach}</div>
                    </div>
                    <div>
                       <div className="text-[9px] font-black text-indigo-200 uppercase tracking-widest mb-2 opacity-60">Decision Pipeline</div>
                       <div className="flex flex-wrap gap-2">
                          {targetData.activation.deciders.map((d, i) => (
                            <span key={i} className="px-3 py-1 bg-black/20 rounded-xl text-[10px] font-black uppercase">{d}</span>
                          ))}
                       </div>
                    </div>
                    <div>
                        <div className="text-[9px] font-black text-indigo-200 uppercase tracking-widest mb-2 opacity-60">Objective reason</div>
                        <div className="text-sm font-bold leading-relaxed">{targetData.activation.reason}</div>
                    </div>
                 </div>
              </section>
           </div>

           {/* Bottom Bar */}
           <div className="mt-10 pt-10 border-t border-white/5 flex flex-col sm:flex-row justify-between items-center gap-8">
              <div className="flex items-center gap-10">
                 <div>
                    <div className="text-[10px] font-black text-gray-600 uppercase tracking-widest mb-2 uppercase">Vigilance Protocol</div>
                    <div className="flex items-center gap-3 px-4 py-2 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-500 text-[10px] font-black uppercase">
                       <AlertTriangle size={14} /> {targetData.risks.falsePositive} FPR
                    </div>
                 </div>
              </div>
              <button 
                onClick={() => router.push(`/targets/${id}/report`)}
                className="w-full sm:w-auto px-10 py-5 bg-white text-black rounded-[2rem] font-black uppercase tracking-widest text-[11px] hover:bg-indigo-500 hover:text-white transition-all shadow-2xl active:scale-95 group flex items-center justify-center gap-3"
              >
                <FileText size={18} /> Generate Origination Dossier
              </button>
           </div>
        </div>
      </div>
    </div>
  );
}
