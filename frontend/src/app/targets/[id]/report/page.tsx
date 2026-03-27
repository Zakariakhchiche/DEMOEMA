"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { FileText, Download, ArrowLeft, ShieldCheck, Zap, TrendingUp, Target as TargetIcon, Users, MapPin, Briefcase, Clock, Activity, Fingerprint, Crosshair, AlertTriangle } from "lucide-react";
import { Target as TargetType } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

export default function ReportPage() {
  const params = useParams();
  const id = params?.id as string;
  const router = useRouter();
  const [target, setTarget] = useState<TargetType | null>(null);
  const [loading, setLoading] = useState(true);
  const [isExporting, setIsExporting] = useState(false);

  useEffect(() => {
    if (!id) return;
    fetch(`/api/targets/${id}`)
      .then(res => res.json())
      .then(json => {
        setTarget(json.data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [id]);

  if (loading || !target) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[#050505]">
        <div className="w-12 h-12 border-4 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin" />
      </div>
    );
  }

  const handlePrint = () => {
    setIsExporting(true);
    setTimeout(() => {
      window.print();
      setIsExporting(false);
    }, 500);
  };

  return (
    <div className="min-h-screen bg-[#050505] text-white p-4 md:p-8 pb-32 flex flex-col items-center">
      {/* Controls */}
      <div className="w-full max-w-4xl flex flex-col sm:flex-row justify-between items-center mb-12 print:hidden gap-6">
        <button 
          onClick={() => router.back()}
          className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors font-black uppercase tracking-widest text-[10px]"
        >
          <ArrowLeft size={16} /> Back to Vault
        </button>
        <button 
          onClick={handlePrint}
          disabled={isExporting}
          className={`px-8 py-4 bg-white text-black rounded-2xl font-black uppercase tracking-widest text-[10px] flex items-center gap-3 hover:bg-gray-200 transition-all shadow-2xl ${isExporting ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          {isExporting ? (
            <div className="w-4 h-4 border-2 border-black/20 border-t-black rounded-full animate-spin" />
          ) : (
            <Download size={16} />
          )}
          {isExporting ? "Generating PDF..." : "Export Dossier (PDF)"}
        </button>
      </div>

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-4xl bg-white text-black p-10 md:p-20 shadow-none flex flex-col gap-12 print:rounded-none overflow-hidden"
      >
        {/* Document Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start border-b-8 border-black pb-12 gap-8">
          <div>
            <div className="flex items-center gap-3 mb-6">
               <div className="w-12 h-12 bg-black flex items-center justify-center rounded-xl">
                  <Fingerprint size={28} className="text-white" />
               </div>
               <span className="font-black text-3xl tracking-tighter uppercase">EDRCF 5.0</span>
            </div>
            <h1 className="text-5xl font-black tracking-tighter mb-2 italic">EXTRACTION : ORIGINATION</h1>
            <p className="text-gray-500 font-bold uppercase tracking-[0.3em] text-xs">Weak Signals Radar • {new Date().toLocaleDateString('en-US')}</p>
          </div>
          <div className="text-left sm:text-right">
             <div className="text-[10px] font-black uppercase tracking-widest text-gray-400 mb-2">Protocol Confidence</div>
             <div className="text-4xl font-black">{target.globalScore}</div>
             <div className="text-[10px] font-black uppercase tracking-widest text-indigo-600 mt-1">{target.priorityLevel}</div>
          </div>
        </div>

        {/* 01. Identification */}
        <section>
           <h2 className="text-xs font-black uppercase tracking-[0.4em] text-gray-400 mb-8 flex items-center gap-4">
              <span className="w-1.5 h-6 bg-black rounded-full" /> 01. TARGET IDENTITY
           </h2>
           <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
              <div className="space-y-8">
                 <div>
                    <div className="text-[9px] font-black text-gray-400 uppercase tracking-widest mb-1.5">Company</div>
                    <div className="text-3xl font-black uppercase tracking-tight">{target.name}</div>
                 </div>
                 <div className="flex gap-12">
                    <div>
                       <div className="text-[9px] font-black text-gray-400 uppercase tracking-widest mb-1.5">Sectorcluster</div>
                       <div className="text-sm font-black uppercase">{target.sector}</div>
                    </div>
                    <div>
                       <div className="text-[9px] font-black text-gray-400 uppercase tracking-widest mb-1.5">Estimated Window</div>
                       <div className="text-sm font-black uppercase italic">{target.analysis.window}</div>
                    </div>
                 </div>
              </div>
              <div className="p-8 bg-gray-50 rounded-[2rem] border border-gray-100">
                  <div className="text-[9px] font-black text-gray-400 uppercase tracking-widest mb-4">Top 5 Signaux de Convergence</div>
                  <div className="space-y-3">
                     {target.topSignals.map((s, i) => (
                       <div key={i} className="flex items-center gap-3">
                          <div className="w-1.5 h-1.5 rounded-full bg-black shrink-0" />
                          <span className="text-[11px] font-black uppercase">{s.label}</span>
                       </div>
                     ))}
                  </div>
              </div>
           </div>
        </section>

        {/* 02. Analyse */}
        <section className="bg-black text-white p-12 rounded-[3.5rem] relative overflow-hidden">
           <div className="absolute top-0 right-0 p-12 opacity-10">
              <Activity size={120} />
           </div>
           <h2 className="text-xs font-black uppercase tracking-[0.4em] text-gray-500 mb-8 relative z-10">02. NARRATIVE ANALYSIS</h2>
           <div className="space-y-8 relative z-10">
              <div>
                 <div className="text-[9px] font-black text-indigo-400 uppercase tracking-widest mb-2">Probable Technical Type</div>
                 <div className="text-2xl font-black italic">{target.analysis.type}</div>
              </div>
              <p className="text-lg font-bold leading-relaxed text-gray-200 border-l border-white/20 pl-8">
                {target.analysis.narrative}
              </p>
           </div>
        </section>

        {/* 03. Activat         <section className="grid grid-cols-1 md:grid-cols-2 gap-12">
           <div>
              <h2 className="text-xs font-black uppercase tracking-[0.4em] text-gray-400 mb-8">03. STRATEGIC ACTIVATION</h2>
              <div className="space-y-6">
                 <div>
                    <div className="text-[9px] font-black text-gray-400 uppercase tracking-widest mb-2">Probable Deciders</div>
                    <div className="flex flex-wrap gap-2">
                       {target.activation.deciders.map((d, i) => (
                         <span key={i} className="px-3 py-1 bg-gray-100 rounded-lg text-[10px] font-black uppercase">{d}</span>
                       ))}
                    </div>
                 </div>
                 <div>
                    <div className="text-[9px] font-black text-gray-400 uppercase tracking-widest mb-2">Recommended Approach</div>
                    <div className="text-sm font-bold leading-relaxed">{target.activation.approach}</div>
                 </div>
                 <div>
                    <div className="text-[9px] font-black text-gray-400 uppercase tracking-widest mb-2">Objective contact reason</div>
                    <div className="text-sm font-bold leading-relaxed">{target.activation.reason}</div>
                 </div>
              </div>
           </div>
           <div className="p-10 border-4 border-rose-500/10 rounded-[3rem] bg-rose-50/20">
              <h2 className="text-xs font-black uppercase tracking-[0.4em] text-rose-500 mb-8 flex items-center gap-3">
                 <AlertTriangle size={18} /> VIGILANCE & RISKS
              </h2>
              <div className="space-y-8">
                 <div>
                    <div className="text-[9px] font-black text-rose-500/60 uppercase tracking-widest mb-2">False Positive Risk</div>
                    <div className="text-2xl font-black text-rose-600">{target.risks.falsePositive}</div>
                 </div>
                 <div>
                    <div className="text-[9px] font-black text-rose-500/60 uppercase tracking-widest mb-2">Incertainty Points</div>
                    <p className="text-xs font-bold leading-relaxed text-gray-500">
                       {target.risks.uncertainties}
                    </p>
                 </div>
              </div>
           </div>
        </section>  </section>

        {/* Footer */}
        <div className="mt-12 pt-12 border-t border-black flex justify-between items-center text-[8px] font-black text-gray-400 uppercase tracking-widest">
           <div className="flex gap-8">
              <span>EDRCF-ARCHIVE-V5</span>
              <span>GEN-LATENCY-42ms</span>
           </div>
           <div>TOTAL CONFIDENTIALITY • INTERNAL USE ONLY</div>
        </div>
      </motion.div>

      <style jsx global>{`
        @media print {
          html, body { background: white !important; margin: 0; padding: 0; }
          .min-h-screen { background: white !important; padding: 0 !important; }
          .print\:hidden { display: none !important; }
          .bg-white { shadow: none !important; box-shadow: none !important; border-radius: 0 !important; }
          .bg-black { color: black !important; background: white !important; border: 4px solid black !important; }
          .bg-black p { color: black !important; }
          .bg-black div { color: black !important; }
          section { page-break-inside: avoid; }
        }
      `}</style>
    </div>
  );
}
