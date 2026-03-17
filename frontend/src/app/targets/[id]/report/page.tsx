"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { FileText, Download, ArrowLeft, ShieldCheck, Zap, TrendingUp, Target, Users, MapPin, Briefcase, Clock, Activity } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

export default function ReportPage() {
  const params = useParams();
  const id = params?.id as string;
  const router = useRouter();
  const [target, setTarget] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    fetch(`${API_URL}/api/targets/${id}`)
      .then(res => res.json())
      .then(json => {
        setTarget(json.data);
        setLoading(false);
      });
  }, [id]);

  if (loading || !target) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[#050505]">
        <div className="w-12 h-12 border-4 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin" />
      </div>
    );
  }

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="min-h-screen bg-[#050505] text-white p-4 md:p-8 pb-32 flex flex-col items-center">
      {/* Controls - Hidden in Print */}
      <div className="w-full max-w-4xl flex justify-between items-center mb-12 print:hidden">
        <button 
          onClick={() => router.back()}
          className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors font-black uppercase tracking-widest text-[10px]"
        >
          <ArrowLeft size={16} /> Back to Vault
        </button>
        <button 
          onClick={handlePrint}
          className="px-6 py-3 bg-white text-black rounded-2xl font-black uppercase tracking-widest text-[10px] flex items-center gap-3 hover:bg-gray-200 transition-all active:scale-95 shadow-2xl"
        >
          <Download size={16} /> Export Dossier (PDF)
        </button>
      </div>

      {/* The Report Document */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-4xl bg-white text-black p-6 sm:p-12 md:p-20 rounded-[2rem] sm:rounded-[3rem] shadow-[0_0_100px_rgba(255,255,255,0.05)] print:shadow-none print:rounded-none flex flex-col gap-8 sm:gap-12"
      >
        {/* Document Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start border-b-4 border-black pb-8 sm:pb-12 gap-6">
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-black flex items-center justify-center rounded-xl">
                 <Zap size={20} className="text-white" />
              </div>
              <span className="font-black text-xl sm:text-2xl tracking-tighter uppercase">Aethelgard</span>
            </div>
            <h1 className="text-3xl sm:text-5xl font-black tracking-tighter mb-2">TARGET DOSSIER</h1>
            <p className="text-gray-500 font-bold uppercase tracking-[0.2em] text-[10px] sm:text-xs">Internal Strategic Intelligence • {new Date().toLocaleDateString()}</p>
          </div>
          <div className="text-left sm:text-right">
             <div className="text-[10px] font-black uppercase tracking-widest text-gray-400 mb-1">Status</div>
             <div className="px-4 py-1.5 bg-black text-white rounded-lg font-black text-[10px] uppercase tracking-widest">Highly Confidential</div>
          </div>
        </div>

        {/* Target Profile */}
        <section className="grid grid-cols-1 md:grid-cols-2 gap-16">
          <div>
             <h2 className="text-[10px] font-black uppercase tracking-[0.3em] text-gray-400 mb-6 underline decoration-black/10 underline-offset-8">01. Entity Identity</h2>
             <div className="space-y-6">
                <div>
                   <div className="text-[9px] font-black text-gray-400 uppercase tracking-widest mb-1">Legal Name</div>
                   <div className="text-2xl font-black">{target.name}</div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                   <div>
                      <div className="text-[9px] font-black text-gray-400 uppercase tracking-widest mb-1">Sector</div>
                      <div className="text-sm font-bold">{target.sector} Hub</div>
                   </div>
                   <div>
                      <div className="text-[9px] font-black text-gray-400 uppercase tracking-widest mb-1">Core Focus</div>
                      <div className="text-sm font-bold">{target.dealType}</div>
                   </div>
                </div>
                <div className="p-6 bg-gray-50 rounded-3xl border border-gray-100 flex items-center justify-between">
                   <div>
                      <div className="text-[9px] font-black text-gray-400 uppercase tracking-widest mb-1">Confidence Score</div>
                      <div className="text-3xl font-black text-black tracking-tighter">{target.priorityScore}%</div>
                   </div>
                   <ShieldCheck size={32} className="text-black opacity-20" />
                </div>
             </div>
          </div>

          <div className="flex flex-col justify-center gap-8">
             <div className="p-8 rounded-[2.5rem] bg-black text-white flex items-center justify-between">
                <div>
                   <div className="text-[9px] font-black text-gray-500 uppercase tracking-widest mb-1">Detection Window</div>
                   <div className="text-2xl font-black italic">{target.timeframe}</div>
                </div>
                <Clock size={32} className="opacity-20 translate-x-4" />
             </div>
             <p className="text-sm text-gray-600 leading-relaxed font-medium">
                Analysis suggests a deep structural alignment with our primary acquisition mandate. Entity demonstrates low resistance to warm network outreach.
             </p>
          </div>
        </section>

        {/* Intelligence Synthesis */}
        <section className="bg-gray-50 p-6 sm:p-12 rounded-[2.5rem] sm:rounded-[3.5rem] border border-gray-100">
           <h2 className="text-[10px] font-black uppercase tracking-[0.3em] text-gray-400 mb-8 flex items-center gap-3">
              <Activity size={16} className="text-black" /> 02. Neural Synthesis
           </h2>
           <div className="space-y-8">
              <div className="p-6 sm:p-8 bg-white rounded-[1.5rem] sm:rounded-[2rem] border border-gray-200 relative overflow-hidden">
                 <div className="absolute top-0 right-0 p-8 opacity-[0.03]">
                    <Target size={120} />
                 </div>
                 <h3 className="text-lg font-black mb-4 relative z-10 text-left">Strategic Thesis</h3>
                 <p className="text-gray-600 leading-relaxed font-medium relative z-10 text-sm sm:text-base text-left">
                    The entity's current capital structure and recent executive activity indicate a pre-transactional phase. Our proprietary "Aethelgard-7" protocol identifies a high convergence of liquidity pressure and succession needs.
                 </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                 <div className="space-y-4">
                    <h4 className="text-[9px] font-black uppercase tracking-widest text-gray-400">Signal Evidence</h4>
                    {target.signals.map((s: string, i: number) => (
                      <div key={i} className="flex gap-4 items-start">
                         <div className="w-1.5 h-1.5 rounded-full bg-black mt-2 shrink-0" />
                         <span className="text-sm font-bold text-gray-800">{s}</span>
                      </div>
                    ))}
                 </div>
                 <div className="space-y-4">
                    <h4 className="text-[9px] font-black uppercase tracking-widest text-gray-400">Metric Breakdown</h4>
                    <div className="space-y-3">
                       {Object.entries(target.scores).map(([k, v]: any) => (
                         <div key={k} className="flex justify-between items-end border-b border-gray-100 pb-2">
                            <span className="text-[10px] font-black uppercase tracking-widest text-gray-500">{k}</span>
                            <span className="font-black text-sm">{v}%</span>
                         </div>
                       ))}
                    </div>
                 </div>
              </div>
           </div>
        </section>

        {/* Network & Access */}
        <section>
           <h2 className="text-[10px] font-black uppercase tracking-[0.3em] text-gray-400 mb-8 text-left">03. Network Intelligence</h2>
           <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="p-6 border border-gray-200 rounded-3xl text-left">
                 <Users size={20} className="mb-4 opacity-50" />
                 <div className="text-[9px] font-black text-gray-400 uppercase tracking-widest mb-1">Entry Path</div>
                 <div className="text-xs font-bold leading-relaxed">{target.accessibility}</div>
              </div>
              <div className="p-6 border border-gray-200 rounded-3xl text-left">
                 <Briefcase size={20} className="mb-4 opacity-50" />
                 <div className="text-[9px] font-black text-gray-400 uppercase tracking-widest mb-1">Entity Cluster</div>
                 <div className="text-xs font-bold">{target.sector} Deep-Tech</div>
              </div>
              <div className="p-6 border border-gray-200 rounded-3xl text-left">
                 <MapPin size={20} className="mb-4 opacity-50" />
                 <div className="text-[9px] font-black text-gray-400 uppercase tracking-widest mb-1">Dominant Region</div>
                 <div className="text-xs font-bold uppercase tracking-widest">European Union</div>
              </div>
           </div>
        </section>

        {/* Footer */}
        <div className="mt-8 sm:mt-12 pt-8 sm:pt-12 border-t border-gray-200 flex flex-col sm:flex-row justify-between items-center text-[7px] sm:text-[8px] font-black text-gray-400 uppercase tracking-[0.2em] sm:tracking-[0.4em] gap-4 text-center sm:text-left">
           <span>AETHELGARD-DOSSIER-V1</span>
           <span className="hidden sm:inline">SECURE TRANSMISSION PROTOCOL: ENABLED</span>
           <span>ID: {target.id.toUpperCase()}-{Math.random().toString(36).substring(7).toUpperCase()}</span>
        </div>
      </motion.div>

      <style jsx global>{`
        @media print {
          body { background: white !important; }
          .min-h-screen { background: white !important; }
          header, footer, nav, aside { display: none !important; }
        }
      `}</style>
    </div>
  );
}
