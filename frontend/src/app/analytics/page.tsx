"use client";

import { useState, useEffect, useMemo } from "react";
import { motion } from "framer-motion";
import {
  BarChart2, TrendingUp, Building2, Users, Zap, PieChart,
  Target, Activity, ArrowUpRight, Filter, Download,
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart as RePieChart, Pie, Cell, RadarChart, Radar, PolarGrid,
  PolarAngleAxis, AreaChart, Area,
} from "recharts";
import Link from "next/link";
import type { Target as TargetType } from "@/types";

const COLORS = ["#6366f1", "#a855f7", "#ec4899", "#f59e0b", "#10b981", "#06b6d4", "#f43f5e", "#8b5cf6"];

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-[#0d0d18] border border-white/10 rounded-xl px-3 py-2 shadow-xl text-[11px]">
      <p className="font-black text-white mb-1">{label}</p>
      {payload.map((p: any, i: number) => (
        <p key={i} style={{ color: p.color || p.fill }} className="font-bold">{p.name}: {p.value}</p>
      ))}
    </div>
  );
};

export default function AnalyticsPage() {
  const [targets, setTargets] = useState<TargetType[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/targets?limit=5000")
      .then(r => r.json())
      .then(d => { setTargets(d.data || []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  // ── Computed analytics ───────────────────────────────────────────────────────
  const sectorData = useMemo(() => {
    const counts: Record<string, { count: number; totalScore: number }> = {};
    targets.forEach(t => {
      const s = t.sector || "Autre";
      if (!counts[s]) counts[s] = { count: 0, totalScore: 0 };
      counts[s].count++;
      counts[s].totalScore += t.globalScore;
    });
    return Object.entries(counts)
      .map(([sector, d]) => ({ sector: sector.slice(0, 20), count: d.count, avgScore: Math.round(d.totalScore / d.count) }))
      .sort((a, b) => b.count - a.count).slice(0, 10);
  }, [targets]);

  const priorityData = useMemo(() => {
    const counts: Record<string, number> = {};
    targets.forEach(t => { counts[t.priorityLevel] = (counts[t.priorityLevel] || 0) + 1; });
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  }, [targets]);

  const structureData = useMemo(() => {
    const counts: Record<string, number> = {};
    targets.forEach(t => { counts[t.structure] = (counts[t.structure] || 0) + 1; });
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  }, [targets]);

  const scoreDistribution = useMemo(() => {
    const buckets = [
      { range: "0-20", min: 0, max: 20, count: 0 },
      { range: "20-40", min: 20, max: 40, count: 0 },
      { range: "40-50", min: 40, max: 50, count: 0 },
      { range: "50-60", min: 50, max: 60, count: 0 },
      { range: "60-70", min: 60, max: 70, count: 0 },
      { range: "70-80", min: 70, max: 80, count: 0 },
      { range: "80+", min: 80, max: 100, count: 0 },
    ];
    targets.forEach(t => {
      const b = buckets.find(b => t.globalScore >= b.min && t.globalScore < b.max) || buckets[buckets.length - 1];
      b.count++;
    });
    return buckets;
  }, [targets]);

  const ebitdaData = useMemo(() => {
    const counts: Record<string, number> = {};
    targets.forEach(t => { const r = t.financials?.ebitda_range || "N/A"; counts[r] = (counts[r] || 0) + 1; });
    return Object.entries(counts).map(([name, value]) => ({ name, value })).filter(d => d.name !== "N/A");
  }, [targets]);

  const regionData = useMemo(() => {
    const counts: Record<string, number> = {};
    targets.forEach(t => { if (t.region) counts[t.region] = (counts[t.region] || 0) + 1; });
    return Object.entries(counts).map(([region, count]) => ({ region: region.slice(0, 15), count }))
      .sort((a, b) => b.count - a.count).slice(0, 8);
  }, [targets]);

  const radarData = useMemo(() => {
    if (!targets.length) return [];
    const dims = ["financier", "gouvernance", "signal_bodacc", "secteur", "effectif", "anciennete"];
    return dims.map(d => ({
      dimension: d.replace("_", " "),
      avg: Math.round(targets.reduce((acc, t) => acc + ((t.scoring_details?.[d]?.score || 0)), 0) / targets.length),
    }));
  }, [targets]);

  const kpis = useMemo(() => {
    if (!targets.length) return [];
    const actionPrio = targets.filter(t => t.priorityLevel === "Action Prioritaire").length;
    const avgScore = Math.round(targets.reduce((a, t) => a + t.globalScore, 0) / targets.length);
    const withSignals = targets.filter(t => t.topSignals?.length > 0).length;
    const bodaccFlag = targets.filter(t => t.bodacc_recent).length;
    const pe = targets.filter(t => t.structure === "PE-backed").length;
    const familiales = targets.filter(t => t.structure === "Familiale").length;
    return [
      { label: "Total cibles", value: targets.length, icon: <Target size={16} />, color: "indigo", sub: "dans la base" },
      { label: "Action Prioritaire", value: actionPrio, icon: <Zap size={16} />, color: "rose", sub: `${Math.round(actionPrio / targets.length * 100)}% du total` },
      { label: "Score moyen", value: avgScore, icon: <BarChart2 size={16} />, color: "amber", sub: "/100" },
      { label: "Avec signaux", value: withSignals, icon: <Activity size={16} />, color: "purple", sub: "M&A actifs" },
      { label: "BODACC récent", value: bodaccFlag, icon: <TrendingUp size={16} />, color: "emerald", sub: "alertes" },
      { label: "PE-backed", value: pe, icon: <Building2 size={16} />, color: "cyan", sub: `${familiales} familiales` },
    ];
  }, [targets]);

  const colorMap: Record<string, string> = {
    indigo: "text-indigo-400 bg-indigo-500/10 border-indigo-500/20",
    rose: "text-rose-400 bg-rose-500/10 border-rose-500/20",
    amber: "text-amber-400 bg-amber-500/10 border-amber-500/20",
    purple: "text-purple-400 bg-purple-500/10 border-purple-500/20",
    emerald: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
    cyan: "text-cyan-400 bg-cyan-500/10 border-cyan-500/20",
  };

  if (loading) return (
    <div className="flex items-center justify-center h-96">
      <div className="flex flex-col items-center gap-4">
        <div className="w-10 h-10 border-2 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin" />
        <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Chargement analytics…</span>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col gap-6 pb-24">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/5 pb-6">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center">
            <BarChart2 size={22} className="text-purple-400" />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-black tracking-tighter text-white uppercase italic">Analytics M&A</h1>
            <p className="text-[10px] font-black text-gray-500 uppercase tracking-widest mt-1">Intelligence data sur {targets.length.toLocaleString()} cibles</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/targets" className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-gray-400 text-[10px] font-black uppercase tracking-widest hover:bg-white/8 transition-all">
            <Filter size={11} /> Filtrer
          </Link>
          <Link href="/targets" className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-300 text-[10px] font-black uppercase tracking-widest hover:bg-indigo-600/30 transition-all">
            <ArrowUpRight size={11} /> Voir les cibles
          </Link>
        </div>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {kpis.map((k, i) => (
          <motion.div key={k.label} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
            className="p-4 rounded-2xl bg-black/40 border border-white/8 backdrop-blur-xl hover:border-white/15 transition-all">
            <div className={`w-8 h-8 rounded-xl flex items-center justify-center mb-3 border ${colorMap[k.color]}`}>{k.icon}</div>
            <div className="text-2xl font-black text-white">{k.value.toLocaleString()}</div>
            <div className="text-[8px] font-black text-gray-500 uppercase tracking-widest mt-0.5">{k.label}</div>
            <div className="text-[8px] text-gray-700 mt-0.5">{k.sub}</div>
          </motion.div>
        ))}
      </div>

      {/* Charts Row 1: Score distribution + Sectors */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Score distribution */}
        <div className="p-5 rounded-3xl bg-black/40 border border-white/8 backdrop-blur-xl">
          <div className="flex items-center gap-2 mb-5">
            <div className="w-7 h-7 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
              <BarChart2 size={13} className="text-amber-400" />
            </div>
            <div>
              <p className="text-[11px] font-black text-white uppercase tracking-widest">Distribution des scores</p>
              <p className="text-[8px] text-gray-600 font-bold uppercase tracking-widest">Score M&A / 100</p>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={scoreDistribution} barSize={28}>
              <XAxis dataKey="range" tick={{ fill: "#4b5563", fontSize: 10, fontWeight: "bold" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "#4b5563", fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="count" name="Cibles" radius={[6, 6, 0, 0]}>
                {scoreDistribution.map((_, i) => (
                  <Cell key={i} fill={i >= 4 ? "#10b981" : i >= 2 ? "#f59e0b" : "#6366f1"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Sectors */}
        <div className="p-5 rounded-3xl bg-black/40 border border-white/8 backdrop-blur-xl">
          <div className="flex items-center gap-2 mb-5">
            <div className="w-7 h-7 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
              <PieChart size={13} className="text-indigo-400" />
            </div>
            <div>
              <p className="text-[11px] font-black text-white uppercase tracking-widest">Répartition sectorielle</p>
              <p className="text-[8px] text-gray-600 font-bold uppercase tracking-widest">Top 10 secteurs</p>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={sectorData} layout="vertical" barSize={14}>
              <XAxis type="number" tick={{ fill: "#4b5563", fontSize: 9 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="sector" tick={{ fill: "#9ca3af", fontSize: 9, fontWeight: "bold" }} axisLine={false} tickLine={false} width={110} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="count" name="Cibles" radius={[0, 6, 6, 0]}>
                {sectorData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Charts Row 2: Priority + Structure + EBITDA */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Priority pie */}
        <div className="p-5 rounded-3xl bg-black/40 border border-white/8 backdrop-blur-xl">
          <p className="text-[11px] font-black text-white uppercase tracking-widest mb-1">Niveaux de priorité</p>
          <p className="text-[8px] text-gray-600 font-bold uppercase tracking-widest mb-4">Répartition pipeline</p>
          <div className="flex items-center gap-3">
            <ResponsiveContainer width={100} height={100}>
              <RePieChart>
                <Pie data={priorityData} cx="50%" cy="50%" innerRadius={28} outerRadius={46} paddingAngle={3} dataKey="value">
                  {priorityData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
              </RePieChart>
            </ResponsiveContainer>
            <div className="flex-1 space-y-1.5">
              {priorityData.map((d, i) => (
                <div key={d.name} className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                  <span className="text-[9px] text-gray-400 truncate">{d.name.replace("Action ", "")}</span>
                  <span className="text-[9px] font-black text-white ml-auto">{d.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Structure pie */}
        <div className="p-5 rounded-3xl bg-black/40 border border-white/8 backdrop-blur-xl">
          <p className="text-[11px] font-black text-white uppercase tracking-widest mb-1">Structure capitalistique</p>
          <p className="text-[8px] text-gray-600 font-bold uppercase tracking-widest mb-4">Famille / PE / Côté</p>
          <div className="flex items-center gap-3">
            <ResponsiveContainer width={100} height={100}>
              <RePieChart>
                <Pie data={structureData} cx="50%" cy="50%" innerRadius={28} outerRadius={46} paddingAngle={3} dataKey="value">
                  {structureData.map((_, i) => <Cell key={i} fill={["#6366f1", "#f59e0b", "#10b981"][i % 3]} />)}
                </Pie>
              </RePieChart>
            </ResponsiveContainer>
            <div className="flex-1 space-y-1.5">
              {structureData.map((d, i) => (
                <div key={d.name} className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: ["#6366f1", "#f59e0b", "#10b981"][i % 3] }} />
                  <span className="text-[9px] text-gray-400 truncate">{d.name}</span>
                  <span className="text-[9px] font-black text-white ml-auto">{d.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* EBITDA ranges */}
        <div className="p-5 rounded-3xl bg-black/40 border border-white/8 backdrop-blur-xl">
          <p className="text-[11px] font-black text-white uppercase tracking-widest mb-1">Tranches d&apos;EBITDA</p>
          <p className="text-[8px] text-gray-600 font-bold uppercase tracking-widest mb-4">Profil financier</p>
          <div className="space-y-2.5">
            {ebitdaData.sort((a, b) => b.value - a.value).map((d, i) => {
              const max = Math.max(...ebitdaData.map(x => x.value));
              return (
                <div key={d.name}>
                  <div className="flex justify-between mb-1">
                    <span className="text-[9px] font-black text-gray-400">{d.name}</span>
                    <span className="text-[9px] font-black text-white">{d.value}</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
                    <motion.div className="h-full rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }}
                      initial={{ width: 0 }} animate={{ width: `${(d.value / max) * 100}%` }} transition={{ duration: 0.5, delay: i * 0.1 }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Charts Row 3: Regions + Score radar */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Regions */}
        <div className="p-5 rounded-3xl bg-black/40 border border-white/8 backdrop-blur-xl">
          <div className="flex items-center gap-2 mb-5">
            <div className="w-7 h-7 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
              <Activity size={13} className="text-emerald-400" />
            </div>
            <div>
              <p className="text-[11px] font-black text-white uppercase tracking-widest">Répartition régionale</p>
              <p className="text-[8px] text-gray-600 font-bold uppercase tracking-widest">Top 8 régions</p>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={regionData}>
              <XAxis dataKey="region" tick={{ fill: "#4b5563", fontSize: 9 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "#4b5563", fontSize: 9 }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="count" name="Cibles" stroke="#10b981" fill="url(#emeraldGrad)" strokeWidth={2} />
              <defs>
                <linearGradient id="emeraldGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Score radar by dimension */}
        {radarData.length > 0 ? (
          <div className="p-5 rounded-3xl bg-black/40 border border-white/8 backdrop-blur-xl">
            <div className="flex items-center gap-2 mb-5">
              <div className="w-7 h-7 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center">
                <Target size={13} className="text-purple-400" />
              </div>
              <div>
                <p className="text-[11px] font-black text-white uppercase tracking-widest">Scores moyens par dimension</p>
                <p className="text-[8px] text-gray-600 font-bold uppercase tracking-widest">Radar scoring EdRCF</p>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="rgba(255,255,255,0.06)" />
                <PolarAngleAxis dataKey="dimension" tick={{ fill: "#6b7280", fontSize: 9, fontWeight: "bold" }} />
                <Radar name="Score moyen" dataKey="avg" stroke="#6366f1" fill="#6366f1" fillOpacity={0.2} strokeWidth={2} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="p-5 rounded-3xl bg-black/40 border border-white/8 backdrop-blur-xl flex items-center justify-center">
            <p className="text-[10px] text-gray-600">Données de scoring insuffisantes</p>
          </div>
        )}
      </div>

      {/* Top 10 table */}
      <div className="p-5 rounded-3xl bg-black/40 border border-white/8 backdrop-blur-xl">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center">
              <Zap size={13} className="text-rose-400" />
            </div>
            <div>
              <p className="text-[11px] font-black text-white uppercase tracking-widest">Top 10 cibles — Score M&A</p>
              <p className="text-[8px] text-gray-600 font-bold uppercase tracking-widest">Meilleures opportunités</p>
            </div>
          </div>
          <Link href="/targets" className="flex items-center gap-1.5 text-[9px] font-black text-indigo-400 uppercase tracking-widest hover:text-indigo-300 transition-colors">
            Voir tout <ArrowUpRight size={10} />
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/5">
                {["#", "Nom", "Secteur", "Région", "Score", "Priorité", "EBITDA", ""].map(h => (
                  <th key={h} className="text-left text-[8px] font-black text-gray-600 uppercase tracking-widest pb-3 pr-4 whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...targets].sort((a, b) => b.globalScore - a.globalScore).slice(0, 10).map((t, i) => (
                <tr key={t.id} className="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors group">
                  <td className="py-3 pr-4 text-[9px] font-black text-gray-700">{i + 1}</td>
                  <td className="py-3 pr-4">
                    <p className="text-[11px] font-black text-white truncate max-w-40">{t.name}</p>
                    <p className="text-[8px] text-gray-600 font-mono">{t.siren}</p>
                  </td>
                  <td className="py-3 pr-4 text-[10px] text-gray-400 truncate max-w-28 hidden sm:table-cell">{t.sector}</td>
                  <td className="py-3 pr-4 text-[10px] text-gray-500 truncate max-w-24 hidden lg:table-cell">{t.region}</td>
                  <td className="py-3 pr-4">
                    <span className={`text-lg font-black ${t.globalScore >= 65 ? "text-emerald-400" : t.globalScore >= 45 ? "text-amber-400" : "text-indigo-400"}`}>{t.globalScore}</span>
                  </td>
                  <td className="py-3 pr-4 hidden md:table-cell">
                    <span className={`text-[8px] font-black uppercase tracking-wider px-2 py-1 rounded-lg border ${
                      t.priorityLevel === "Action Prioritaire" ? "bg-rose-500/10 text-rose-400 border-rose-500/20" :
                      t.priorityLevel === "Qualification" ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
                      "bg-white/5 text-gray-500 border-white/10"
                    }`}>{t.priorityLevel}</span>
                  </td>
                  <td className="py-3 pr-4 text-[10px] font-bold text-emerald-400 hidden lg:table-cell">{t.financials?.ebitda || "—"}</td>
                  <td className="py-3">
                    <Link href={`/targets/${t.siren}`} className="opacity-0 group-hover:opacity-100 transition-opacity">
                      <ArrowUpRight size={13} className="text-indigo-400" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
