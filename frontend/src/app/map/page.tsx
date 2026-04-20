"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Map, Filter, TrendingUp, Building2 } from "lucide-react";
import FranceMap from "@/components/FranceMap";
import Link from "next/link";

interface DeptStat {
  dept: string;
  count: number;
  label?: string;
}

const DEPT_NAMES: Record<string, string> = {
  "01":"Ain","02":"Aisne","03":"Allier","04":"Alpes-de-Haute-Provence","05":"Hautes-Alpes",
  "06":"Alpes-Maritimes","07":"Ardèche","08":"Ardennes","09":"Ariège","10":"Aube",
  "11":"Aude","12":"Aveyron","13":"Bouches-du-Rhône","14":"Calvados","15":"Cantal",
  "16":"Charente","17":"Charente-Maritime","18":"Cher","19":"Corrèze","21":"Côte-d'Or",
  "22":"Côtes-d'Armor","23":"Creuse","24":"Dordogne","25":"Doubs","26":"Drôme",
  "27":"Eure","28":"Eure-et-Loir","29":"Finistère","2A":"Corse-du-Sud","2B":"Haute-Corse",
  "30":"Gard","31":"Haute-Garonne","32":"Gers","33":"Gironde","34":"Hérault",
  "35":"Ille-et-Vilaine","36":"Indre","37":"Indre-et-Loire","38":"Isère","39":"Jura",
  "40":"Landes","41":"Loir-et-Cher","42":"Loire","43":"Haute-Loire","44":"Loire-Atlantique",
  "45":"Loiret","46":"Lot","47":"Lot-et-Garonne","48":"Lozère","49":"Maine-et-Loire",
  "50":"Manche","51":"Marne","52":"Haute-Marne","53":"Mayenne","54":"Meurthe-et-Moselle",
  "55":"Meuse","56":"Morbihan","57":"Moselle","58":"Nièvre","59":"Nord",
  "60":"Oise","61":"Orne","62":"Pas-de-Calais","63":"Puy-de-Dôme","64":"Pyrénées-Atlantiques",
  "65":"Hautes-Pyrénées","66":"Pyrénées-Orientales","67":"Bas-Rhin","68":"Haut-Rhin","69":"Rhône",
  "70":"Haute-Saône","71":"Saône-et-Loire","72":"Sarthe","73":"Savoie","74":"Haute-Savoie",
  "75":"Paris","76":"Seine-Maritime","77":"Seine-et-Marne","78":"Yvelines","79":"Deux-Sèvres",
  "80":"Somme","81":"Tarn","82":"Tarn-et-Garonne","83":"Var","84":"Vaucluse",
  "85":"Vendée","86":"Vienne","87":"Haute-Vienne","88":"Vosges","89":"Yonne",
  "90":"Territoire de Belfort","91":"Essonne","92":"Hauts-de-Seine","93":"Seine-Saint-Denis",
  "94":"Val-de-Marne","95":"Val-d'Oise",
};

export default function MapPage() {
  const [data, setData] = useState<DeptStat[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDept, setSelectedDept] = useState<string | undefined>();
  const [selectedTargets, setSelectedTargets] = useState<{name:string;id:string;score:number}[]>([]);

  useEffect(() => {
    fetch("/api/targets?limit=5000")
      .then(r => r.json())
      .then(json => {
        const targets: {dept?: string; region?: string; id: string; name: string; globalScore?: number}[] = json.data || json.targets || [];
        const counts: Record<string, number> = {};
        targets.forEach(t => {
          const d = t.dept || (t.region?.slice(0,2));
          if (d) counts[d] = (counts[d] || 0) + 1;
        });
        setData(Object.entries(counts).map(([dept, count]) => ({
          dept,
          count,
          label: DEPT_NAMES[dept] || dept,
        })));
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const total = data.reduce((s, d) => s + d.count, 0);
  const topDept = data.sort((a,b) => b.count - a.count)[0];

  return (
    <div className="flex flex-col gap-6 pb-20 pt-4 px-0 sm:px-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/5 pb-6">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
            <Map size={22} className="text-indigo-400" />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-black tracking-tighter text-white uppercase italic">Carte des Opportunités</h1>
            <p className="text-[10px] font-black text-gray-500 uppercase tracking-widest mt-1">Distribution géographique des cibles M&A</p>
          </div>
        </div>
        <Link href="/targets" className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-300 text-[10px] font-black uppercase tracking-widest hover:bg-indigo-600/30 transition-all">
          <Filter size={12} /> Voir les cibles
        </Link>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {[
          { label: "Total cibles", value: total, icon: <Building2 size={14} />, color: "indigo" },
          { label: "Départements actifs", value: data.length, icon: <Map size={14} />, color: "purple" },
          { label: "Top département", value: topDept?.label || "—", icon: <TrendingUp size={14} />, color: "emerald" },
        ].map(k => (
          <motion.div
            key={k.label}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-4 rounded-2xl bg-black/40 border border-white/10 backdrop-blur-xl"
          >
            <div className={`text-${k.color}-400 mb-2`}>{k.icon}</div>
            <div className="text-xl font-black text-white">{loading ? "—" : k.value}</div>
            <div className="text-[9px] font-black text-gray-500 uppercase tracking-widest mt-1">{k.label}</div>
          </motion.div>
        ))}
      </div>

      {/* Map */}
      {loading ? (
        <div className="h-[500px] rounded-3xl bg-black/40 border border-white/10 flex items-center justify-center">
          <div className="flex flex-col items-center gap-4">
            <div className="w-10 h-10 border-2 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin" />
            <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Chargement de la carte…</span>
          </div>
        </div>
      ) : (
        <FranceMap
          data={data}
          selectedDept={selectedDept}
          onSelect={(dept) => {
            setSelectedDept(dept === selectedDept ? undefined : dept);
          }}
        />
      )}
    </div>
  );
}
