"use client";

import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTargets } from "@/lib/queries/useTargets";
import { usePullToRefresh } from "@/hooks/usePullToRefresh";
import PullToRefreshIndicator from "@/components/ui/PullToRefreshIndicator";
import { motion, AnimatePresence } from "framer-motion";
import {
  Target,
  Search,
  Filter,
  ArrowUpDown,
  ChevronRight,
  Building,
  Download,
  SlidersHorizontal,
  X,
  Check,
  Globe,
  Shield,
  MapPin,
  BarChart3,
  Users,
  Layers,
  RotateCcw,
  Network,
  Plus,
  Loader2,
} from "lucide-react";
import { useRouter } from "next/navigation";

import {
  Target as TargetData,
  FilterOptions,
  ScoringConfigEntry,
} from "@/types";

type SortKey = "name" | "sector" | "region" | "globalScore";

const PRIORITY_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  "Action Prioritaire": { bg: "bg-emerald-500/10", text: "text-emerald-400", border: "border-emerald-500/20" },
  "Qualification":      { bg: "bg-indigo-500/10",  text: "text-indigo-400",  border: "border-indigo-500/20" },
  "Monitoring":         { bg: "bg-amber-500/10",   text: "text-amber-400",   border: "border-amber-500/20" },
  "Veille Passive":     { bg: "bg-gray-500/10",    text: "text-gray-400",    border: "border-gray-500/20" },
};

const STRUCTURE_COLORS: Record<string, string> = {
  "Familiale":    "bg-purple-500/10 text-purple-400 border-purple-500/20",
  "PE-backed":    "bg-sky-500/10 text-sky-400 border-sky-500/20",
  "Groupe côté":  "bg-amber-500/10 text-amber-400 border-amber-500/20",
};

function getScoreThresholdLabel(score: number) {
  if (score >= 65) return "Action";
  if (score >= 45) return "Qualification";
  if (score >= 25) return "Monitoring";
  return "Veille";
}

export default function TargetsPage() {
  const queryClient = useQueryClient();
  const scrollRef = useRef<HTMLDivElement>(null);
  const { data, isLoading: loading } = useTargets();
  const targets = data?.data || [];
  const handleRefresh = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: ["targets"] });
  }, [queryClient]);
  const { isRefreshing, pullDistance } = usePullToRefresh(scrollRef, handleRefresh);
  const totalCount = data?.total || targets.length;
  const apiFilters = data?.filters || null;
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("globalScore");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  // Filters
  const [showFilters, setShowFilters] = useState(false);
  const [selectedSectors, setSelectedSectors] = useState<string[]>([]);
  const [selectedRegions, setSelectedRegions] = useState<string[]>([]);
  const [selectedStructures, setSelectedStructures] = useState<string[]>([]);
  const [selectedEbitdaRanges, setSelectedEbitdaRanges] = useState<string[]>([]);
  const [selectedPubStatus, setSelectedPubStatus] = useState<string[]>([]);
  const [minScore, setMinScore] = useState(0);

  // Scoring weights panel
  const [showWeights, setShowWeights] = useState(false);
  const [scoringConfig, setScoringConfig] = useState<Record<string, ScoringConfigEntry>>({});
  const [localWeights, setLocalWeights] = useState<Record<string, number>>({});
  const [savingWeights, setSavingWeights] = useState(false);

  const router = useRouter();

  // Re-fetch targets when copilot injects new ones from Pappers
  useEffect(() => {
    const handleTargetsUpdated = () => {
      queryClient.invalidateQueries({ queryKey: ["targets"] });
    };
    window.addEventListener("targets-updated", handleTargetsUpdated);
    return () => window.removeEventListener("targets-updated", handleTargetsUpdated);
  }, [queryClient]);

  // Fetch scoring config
  useEffect(() => {
    fetch(`/api/scoring/config`)
      .then((res) => res.json())
      .then((data) => {
        const config = data.data || data;
        setScoringConfig(config);
        const w: Record<string, number> = {};
        Object.entries(config).forEach(([key, val]) => {
          w[key] = (val as ScoringConfigEntry).weight;
        });
        setLocalWeights(w);
      })
      .catch(() => {});
  }, []);

  // Active filter count
  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (selectedSectors.length > 0) count++;
    if (selectedRegions.length > 0) count++;
    if (selectedStructures.length > 0) count++;
    if (selectedEbitdaRanges.length > 0) count++;
    if (selectedPubStatus.length > 0) count++;
    if (minScore > 0) count++;
    return count;
  }, [selectedSectors, selectedRegions, selectedStructures, selectedEbitdaRanges, selectedPubStatus, minScore]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortOrder("desc");
    }
  };

  const resetFilters = () => {
    setSelectedSectors([]);
    setSelectedRegions([]);
    setSelectedStructures([]);
    setSelectedEbitdaRanges([]);
    setSelectedPubStatus([]);
    setMinScore(0);
  };

  const handleApplyWeights = async () => {
    setSavingWeights(true);
    const payload: Record<string, ScoringConfigEntry> = {};
    Object.entries(scoringConfig).forEach(([key, val]) => {
      payload[key] = { ...val, weight: localWeights[key] ?? val.weight };
    });
    try {
      await fetch(`/api/scoring/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setScoringConfig(payload);
      setShowWeights(false);
      queryClient.invalidateQueries({ queryKey: ["targets"] });
    } catch (err) {
      console.error(err);
    } finally {
      setSavingWeights(false);
    }
  };

  const resetWeights = () => {
    const w: Record<string, number> = {};
    Object.entries(scoringConfig).forEach(([key, val]) => {
      w[key] = val.weight;
    });
    setLocalWeights(w);
  };

  const filteredAndSortedTargets = useMemo(() => {
    return targets
      .filter((t) => {
        const q = search.toLowerCase();
        const matchSearch =
          !q ||
          t.name.toLowerCase().includes(q) ||
          t.sector.toLowerCase().includes(q) ||
          (t.sub_sector || "").toLowerCase().includes(q) ||
          (t.city || "").toLowerCase().includes(q) ||
          (t.siren || "").toLowerCase().includes(q);
        const matchSector = selectedSectors.length === 0 || selectedSectors.includes(t.sector);
        const matchRegion = selectedRegions.length === 0 || selectedRegions.includes(t.region);
        const matchStructure = selectedStructures.length === 0 || selectedStructures.includes(t.structure);
        const matchEbitda = selectedEbitdaRanges.length === 0 || selectedEbitdaRanges.includes(t.financials?.ebitda_range);
        const matchPub = selectedPubStatus.length === 0 || selectedPubStatus.includes(t.publication_status);
        const matchScore = t.globalScore >= minScore;
        return matchSearch && matchSector && matchRegion && matchStructure && matchEbitda && matchPub && matchScore;
      })
      .sort((a, b) => {
        let valA: string | number = a[sortKey] as string | number;
        let valB: string | number = b[sortKey] as string | number;
        if (typeof valA === "string" && typeof valB === "string") {
          return sortOrder === "asc" ? valA.localeCompare(valB) : valB.localeCompare(valA);
        }
        return sortOrder === "asc" ? (valA as number) - (valB as number) : (valB as number) - (valA as number);
      });
  }, [targets, search, sortKey, sortOrder, selectedSectors, selectedRegions, selectedStructures, selectedEbitdaRanges, selectedPubStatus, minScore]);

  const sectors = apiFilters?.sectors || Array.from(new Set(targets.map((t) => t.sector)));
  const regions = apiFilters?.regions || Array.from(new Set(targets.map((t) => t.region).filter(Boolean)));
  const structures = apiFilters?.structures || ["Familiale", "PE-backed", "Groupe côté"];
  const ebitdaRanges = apiFilters?.ebitda_ranges || ["< 3M", "3-10M", "10-30M", "> 30M"];

  // ── NAF Sector importer ───────────────────────────────────────────
  const [showImport, setShowImport] = useState(false);
  const [importNaf, setImportNaf] = useState("");
  const [importCount, setImportCount] = useState(10);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<{ added: number; total: number } | null>(null);

  const handleImportSector = async () => {
    if (!importNaf.trim()) return;
    setImporting(true);
    setImportResult(null);
    try {
      const res = await fetch(`/api/admin/load-sector?naf=${encodeURIComponent(importNaf.trim())}&count=${importCount}`);
      const data = await res.json();
      setImportResult({ added: data.added ?? 0, total: data.total ?? 0 });
      if (data.added > 0) {
        fetchTargets();
        window.dispatchEvent(new CustomEvent("targets-updated"));
      }
    } catch {
      setImportResult({ added: -1, total: 0 });
    } finally {
      setImporting(false);
    }
  };

  const handleExportCSV = () => {
    if (filteredAndSortedTargets.length === 0) return;
    const escape = (v: string | number | undefined | null) => {
      const s = String(v ?? "");
      return s.includes(",") || s.includes('"') || s.includes("\n") ? `"${s.replace(/"/g, '""')}"` : s;
    };
    const headers = [
      "Entité", "SIREN", "Secteur", "Sous-secteur", "Région", "Ville",
      "Structure", "Publication", "Score", "Priorité",
      "Type M&A", "Fenêtre", "CA", "EBITDA", "Marge EBITDA", "Effectif",
      "Signaux actifs", "Dirigeant principal", "Relation EDR (%)",
    ];
    const rows = filteredAndSortedTargets.map(t => [
      t.name,
      t.siren,
      t.sector,
      t.sub_sector || "",
      t.region || "",
      t.city || "",
      t.structure || "",
      t.publication_status || "",
      t.globalScore,
      t.priorityLevel,
      t.analysis?.type || "",
      t.analysis?.window || "",
      t.financials?.revenue || "",
      t.financials?.ebitda || "",
      t.financials?.ebitda_margin || "",
      t.financials?.effectif ?? "",
      t.topSignals?.length ?? 0,
      t.dirigeants?.[0]?.name || "",
      t.relationship?.strength ?? "",
    ]);
    const csv = [headers, ...rows].map(r => r.map(escape).join(",")).join("\n");
    const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Origin_Intelligence_Vault_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col gap-5 sm:gap-6 lg:gap-8 w-full py-4 h-[calc(100dvh-5rem)] sm:h-[calc(100dvh-6rem)]">

      {/* ── Filter Sidebar Overlay ───────────────────────────────── */}
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
              transition={{ type: "spring", damping: 30, stiffness: 300 }}
              className="fixed top-0 right-0 bottom-0 w-full sm:w-[28rem] bg-[#0a0a0a] border-l border-white/10 z-[101] p-6 sm:p-10 shadow-[0_0_100px_rgba(0,0,0,0.8)] flex flex-col"
            >
              <div className="flex items-center justify-between mb-10">
                <h2 className="text-2xl font-black text-white uppercase tracking-tighter">Filtres Avancés</h2>
                <button
                  onClick={() => setShowFilters(false)}
                  className="p-3 rounded-2xl bg-white/5 text-gray-400 hover:text-white transition-all active:scale-95"
                >
                  <X size={20} />
                </button>
              </div>

              <div className="space-y-10 flex-1 overflow-y-auto custom-scrollbar pr-2">
                {/* Sectors */}
                <div>
                  <h3 className="text-[11px] font-black text-white uppercase tracking-[0.2em] mb-6 flex items-center gap-2">
                    <Globe size={14} className="text-indigo-500" /> Secteurs
                  </h3>
                  <div className="flex flex-wrap gap-2.5">
                    {sectors.map((s) => (
                      <button
                        key={s}
                        onClick={() => setSelectedSectors((curr) => (curr.includes(s) ? curr.filter((x) => x !== s) : [...curr, s]))}
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

                {/* Regions */}
                <div>
                  <h3 className="text-[11px] font-black text-white uppercase tracking-[0.2em] mb-6 flex items-center gap-2">
                    <MapPin size={14} className="text-indigo-500" /> Régions
                  </h3>
                  <div className="flex flex-wrap gap-2.5">
                    {regions.map((r) => (
                      <button
                        key={r}
                        onClick={() => setSelectedRegions((curr) => (curr.includes(r) ? curr.filter((x) => x !== r) : [...curr, r]))}
                        className={`px-4 py-2 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all border
                          ${selectedRegions.includes(r)
                            ? "bg-indigo-500 border-indigo-400 text-white shadow-[0_0_20px_rgba(79,70,229,0.3)]"
                            : "bg-white/5 border-white/10 text-gray-500 hover:bg-white/10 hover:text-gray-300"
                          }
                        `}
                      >
                        {r}
                      </button>
                    ))}
                  </div>
                </div>

                {/* EBITDA Range */}
                <div>
                  <h3 className="text-[11px] font-black text-white uppercase tracking-[0.2em] mb-6 flex items-center gap-2">
                    <BarChart3 size={14} className="text-indigo-500" /> Tranche EBITDA
                  </h3>
                  <div className="flex flex-wrap gap-2.5">
                    {ebitdaRanges.map((r) => (
                      <button
                        key={r}
                        onClick={() => setSelectedEbitdaRanges((curr) => (curr.includes(r) ? curr.filter((x) => x !== r) : [...curr, r]))}
                        className={`px-5 py-2.5 rounded-2xl text-[11px] font-black tracking-widest transition-all border
                          ${selectedEbitdaRanges.includes(r)
                            ? "bg-indigo-500 border-indigo-400 text-white shadow-[0_0_20px_rgba(79,70,229,0.3)]"
                            : "bg-white/5 border-white/10 text-gray-500 hover:bg-white/10 hover:text-gray-300"
                          }
                        `}
                      >
                        {r}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Structure */}
                <div>
                  <h3 className="text-[11px] font-black text-white uppercase tracking-[0.2em] mb-6 flex items-center gap-2">
                    <Layers size={14} className="text-indigo-500" /> Structure
                  </h3>
                  <div className="flex flex-wrap gap-2.5">
                    {structures.map((s) => (
                      <button
                        key={s}
                        onClick={() => setSelectedStructures((curr) => (curr.includes(s) ? curr.filter((x) => x !== s) : [...curr, s]))}
                        className={`px-4 py-2 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all border
                          ${selectedStructures.includes(s)
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

                {/* Publication Status */}
                <div>
                  <h3 className="text-[11px] font-black text-white uppercase tracking-[0.2em] mb-6 flex items-center gap-2">
                    <Shield size={14} className="text-indigo-500" /> Statut Publication
                  </h3>
                  <div className="flex flex-wrap gap-2.5">
                    {["Publie", "Ne publie pas"].map((s) => (
                      <button
                        key={s}
                        onClick={() => setSelectedPubStatus((curr) => (curr.includes(s) ? curr.filter((x) => x !== s) : [...curr, s]))}
                        className={`px-4 py-2 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all border
                          ${selectedPubStatus.includes(s)
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

                {/* Score Minimum Slider */}
                <div>
                  <div className="flex justify-between items-center mb-6">
                    <h3 className="text-[11px] font-black text-white uppercase tracking-[0.2em] flex items-center gap-2">
                      <Shield size={14} className="text-indigo-500" /> Score Minimum
                    </h3>
                    <div className="flex items-center gap-2">
                      <span className="text-2xl font-black text-indigo-400">{minScore}</span>
                      <span className="text-[9px] font-black text-gray-600 uppercase">{getScoreThresholdLabel(minScore)}</span>
                    </div>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={minScore}
                    onChange={(e) => setMinScore(parseInt(e.target.value))}
                    className="w-full accent-indigo-500 h-1.5 bg-white/10 rounded-full appearance-none cursor-pointer"
                  />
                  <div className="flex justify-between mt-3 text-[8px] font-black text-gray-700 uppercase tracking-widest">
                    <span>Veille &lt;25</span>
                    <span>Monitoring 25-44</span>
                    <span>Qualif. 45-64</span>
                    <span>Action 65+</span>
                  </div>
                </div>
              </div>

              <div className="pt-10 border-t border-white/10 mt-auto">
                <button
                  onClick={resetFilters}
                  className="w-full py-4 rounded-3xl bg-white/5 border border-white/10 text-[11px] font-black uppercase text-gray-500 hover:bg-rose-500/10 hover:text-rose-400 hover:border-rose-500/20 transition-all tracking-widest active:scale-95"
                >
                  Réinitialiser
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* ── Scoring Weights Panel ────────────────────────────────── */}
      <AnimatePresence>
        {showWeights && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowWeights(false)}
              className="fixed inset-0 bg-black/80 backdrop-blur-xl z-[100]"
            />
            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", damping: 30, stiffness: 300 }}
              className="fixed top-0 right-0 bottom-0 w-full sm:w-[28rem] bg-[#0a0a0a] border-l border-white/10 z-[101] p-6 sm:p-10 shadow-[0_0_100px_rgba(0,0,0,0.8)] flex flex-col"
            >
              <div className="flex items-center justify-between mb-10">
                <h2 className="text-2xl font-black text-white uppercase tracking-tighter">Pondérations</h2>
                <button
                  onClick={() => setShowWeights(false)}
                  className="p-3 rounded-2xl bg-white/5 text-gray-400 hover:text-white transition-all active:scale-95"
                >
                  <X size={20} />
                </button>
              </div>

              <div className="space-y-8 flex-1 overflow-y-auto custom-scrollbar pr-2">
                {Object.entries(scoringConfig).map(([key, dim]) => (
                  <div key={key}>
                    <div className="flex justify-between items-center mb-4">
                      <h3 className="text-[11px] font-black text-white uppercase tracking-[0.15em]">{dim.label}</h3>
                      <span className="text-xl font-black text-indigo-400">{localWeights[key] ?? dim.weight}</span>
                    </div>
                    <input
                      type="range"
                      min="5"
                      max="40"
                      value={localWeights[key] ?? dim.weight}
                      onChange={(e) => setLocalWeights((prev) => ({ ...prev, [key]: parseInt(e.target.value) }))}
                      className="w-full accent-indigo-500 h-1.5 bg-white/10 rounded-full appearance-none cursor-pointer"
                    />
                    <div className="flex justify-between mt-2 text-[9px] font-black text-gray-700 uppercase tracking-widest">
                      <span>5</span>
                      <span>Max: {dim.max}</span>
                      <span>40</span>
                    </div>
                  </div>
                ))}
              </div>

              <div className="pt-10 border-t border-white/10 mt-auto space-y-4">
                <button
                  onClick={handleApplyWeights}
                  disabled={savingWeights}
                  className="w-full py-4 rounded-3xl bg-indigo-600 border border-indigo-500 text-[11px] font-black uppercase text-white hover:bg-indigo-500 transition-all tracking-widest active:scale-95 shadow-2xl shadow-indigo-600/30 flex items-center justify-center gap-3 disabled:opacity-50"
                >
                  {savingWeights ? (
                    <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                  ) : (
                    <Check size={16} />
                  )}
                  Appliquer
                </button>
                <button
                  onClick={resetWeights}
                  className="w-full py-4 rounded-3xl bg-white/5 border border-white/10 text-[11px] font-black uppercase text-gray-500 hover:bg-rose-500/10 hover:text-rose-400 hover:border-rose-500/20 transition-all tracking-widest active:scale-95"
                >
                  Réinitialiser les défauts
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* ── Header ───────────────────────────────────────────────── */}
      <header className="shrink-0 space-y-5">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-black tracking-tighter text-white mb-1.5">
              Intelligence Vault
            </h1>
            <p className="text-gray-500 text-sm font-medium">
              {filteredAndSortedTargets.length} entités sur {totalCount} analysées
              {activeFilterCount > 0 && <span className="text-indigo-400 ml-2">({activeFilterCount} filtres actifs)</span>}
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-3">
            <div className="relative group flex-1 sm:flex-none sm:w-56 lg:w-64">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-indigo-400 transition-colors">
                <Search size={16} />
              </span>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Rechercher une entité..."
                className="w-full bg-white/[0.03] border border-white/10 rounded-xl py-2.5 pl-9 pr-4 text-sm text-gray-200 placeholder-gray-600 outline-none focus:border-indigo-500/50 focus:bg-white/[0.05] transition-all"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setShowWeights(true)}
                className="flex-1 sm:flex-none px-3 py-2.5 rounded-xl bg-white/[0.03] border border-white/10 text-gray-400 hover:text-white hover:bg-white/10 transition-all flex items-center justify-center gap-2 text-[10px] font-black uppercase tracking-wider"
              >
                <BarChart3 size={15} /> <span className="hidden sm:inline">Poids</span>
              </button>
              <button
                onClick={() => setShowFilters(true)}
                className={`flex-1 sm:flex-none px-3 py-2.5 rounded-xl transition-all relative flex items-center justify-center gap-2 text-[10px] font-black uppercase tracking-wider
                  ${activeFilterCount > 0
                    ? "bg-indigo-600 border border-indigo-500 text-white"
                    : "bg-white/[0.03] border border-white/10 text-gray-400 hover:text-white hover:bg-white/10"
                  }
                `}
              >
                <SlidersHorizontal size={15} /> <span className="hidden sm:inline">Filtres</span>
                {activeFilterCount > 0 && (
                  <span className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-indigo-400 text-white text-[8px] font-black flex items-center justify-center border border-[#0a0a0a]">
                    {activeFilterCount}
                  </span>
                )}
              </button>
              <button
                onClick={handleExportCSV}
                disabled={filteredAndSortedTargets.length === 0}
                className="flex-1 sm:flex-none px-3 py-2.5 rounded-xl bg-white/[0.03] border border-white/10 text-gray-400 hover:text-indigo-400 hover:bg-indigo-500/10 hover:border-indigo-500/20 transition-all flex items-center justify-center gap-2 text-[10px] font-black uppercase tracking-wider disabled:opacity-30 disabled:cursor-not-allowed"
                title={`Exporter ${filteredAndSortedTargets.length} cibles en CSV`}
              >
                <Download size={15} /> <span className="hidden sm:inline">Export CSV</span>
              </button>
              <button
                onClick={() => { setShowImport(v => !v); setImportResult(null); }}
                className={`flex-1 sm:flex-none px-3 py-2.5 rounded-xl border transition-all flex items-center justify-center gap-2 text-[10px] font-black uppercase tracking-wider
                  ${showImport ? "bg-indigo-600 border-indigo-500 text-white" : "bg-white/3 border-white/10 text-gray-400 hover:text-indigo-400 hover:bg-indigo-500/10 hover:border-indigo-500/20"}`}
                title="Importer un secteur via code NAF"
              >
                <Plus size={15} /> <span className="hidden sm:inline">Importer</span>
              </button>
            </div>
          </div>
        </div>

        {/* ── NAF Sector Importer Panel ─────────────────────────── */}
        <AnimatePresence>
          {showImport && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden"
            >
              <div className="p-4 rounded-2xl bg-indigo-500/5 border border-indigo-500/20 flex flex-col sm:flex-row gap-3 items-start sm:items-end">
                <div className="flex-1 min-w-0">
                  <label className="text-[9px] font-black text-indigo-400 uppercase tracking-widest block mb-1.5">Code NAF</label>
                  <input
                    value={importNaf}
                    onChange={e => setImportNaf(e.target.value)}
                    placeholder="ex: 62.01Z, 66.22Z, 49.41A…"
                    className="w-full bg-black/40 border border-white/10 rounded-xl py-2.5 px-4 text-sm text-gray-200 placeholder-gray-600 outline-none focus:border-indigo-500/50 transition-all font-mono"
                    onKeyDown={e => e.key === "Enter" && handleImportSector()}
                  />
                </div>
                <div className="flex-none">
                  <label className="text-[9px] font-black text-indigo-400 uppercase tracking-widest block mb-1.5">Quantité</label>
                  <select
                    value={importCount}
                    onChange={e => setImportCount(Number(e.target.value))}
                    className="bg-black/40 border border-white/10 rounded-xl py-2.5 px-3 text-sm text-gray-200 outline-none focus:border-indigo-500/50"
                  >
                    {[5, 10, 20, 30, 50].map(n => <option key={n} value={n}>{n} entités</option>)}
                  </select>
                </div>
                <button
                  onClick={handleImportSector}
                  disabled={importing || !importNaf.trim()}
                  className="flex-none px-5 py-2.5 rounded-xl bg-indigo-600 text-white font-black text-[10px] uppercase tracking-widest hover:bg-indigo-500 transition-all active:scale-95 disabled:opacity-40 flex items-center gap-2"
                >
                  {importing ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                  {importing ? "Chargement…" : "Importer"}
                </button>
                {importResult && (
                  <div className={`text-[10px] font-black uppercase tracking-wider px-3 py-2 rounded-xl border flex-none
                    ${importResult.added > 0 ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" : importResult.added === 0 ? "text-amber-400 bg-amber-500/10 border-amber-500/20" : "text-rose-400 bg-rose-500/10 border-rose-500/20"}`}
                  >
                    {importResult.added > 0 ? `+${importResult.added} ajoutées · ${importResult.total} total` : importResult.added === 0 ? "Déjà en base" : "Erreur"}
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── KPI Summary Strip ─────────────────────────────────── */}
        {!loading && targets.length > 0 && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {[
              { label: "Score moyen", value: Math.round(targets.reduce((a, t) => a + t.globalScore, 0) / targets.length), suffix: "/100", color: "text-indigo-400" },
              { label: "Action prioritaire", value: targets.filter(t => t.priorityLevel === "Action Prioritaire").length, suffix: "", color: "text-emerald-400" },
              { label: "Secteurs couverts", value: new Set(targets.map(t => t.sector)).size, suffix: "", color: "text-purple-400" },
              { label: "Régions", value: new Set(targets.map(t => t.region).filter(Boolean)).size, suffix: "", color: "text-amber-400" },
            ].map(kpi => (
              <div key={kpi.label} className="flex items-center gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/5">
                <span className={`text-xl font-black ${kpi.color}`}>{kpi.value}{kpi.suffix}</span>
                <span className="text-[9px] font-bold text-gray-500 uppercase tracking-wider leading-tight">{kpi.label}</span>
              </div>
            ))}
          </div>
        )}
      </header>

      {/* ── Table Area ───────────────────────────────────────────── */}
      <div className="flex-1 bg-black/40 border border-white/10 rounded-[2rem] sm:rounded-[3rem] overflow-hidden flex flex-col shadow-2xl lg:backdrop-blur-3xl relative">
        {/* Table Header - Desktop Only */}
        <div className="hidden lg:grid grid-cols-12 gap-3 px-6 py-3.5 border-b border-white/[0.06] bg-white/[0.015] text-[10px] font-black text-gray-500 uppercase tracking-[0.15em]">
          <div
            className="col-span-3 flex items-center gap-2 cursor-pointer hover:text-white transition-colors"
            onClick={() => handleSort("name")}
          >
            Entité {sortKey === "name" && <ArrowUpDown size={12} className="text-indigo-400" />}
          </div>
          <div
            className="col-span-2 flex items-center gap-2 cursor-pointer hover:text-white transition-colors"
            onClick={() => handleSort("sector")}
          >
            Secteur {sortKey === "sector" && <ArrowUpDown size={12} className="text-indigo-400" />}
          </div>
          <div
            className="col-span-2 flex items-center gap-2 cursor-pointer hover:text-white transition-colors"
            onClick={() => handleSort("region")}
          >
            Région {sortKey === "region" && <ArrowUpDown size={12} className="text-indigo-400" />}
          </div>
          <div className="col-span-1 flex items-center gap-2 text-gray-600">
            EBITDA
          </div>
          <div
            className="col-span-2 flex items-center gap-2 cursor-pointer hover:text-white transition-colors justify-end"
            onClick={() => handleSort("globalScore")}
          >
            Score {sortKey === "globalScore" && <ArrowUpDown size={12} className="text-indigo-400" />}
          </div>
          <div className="col-span-1 text-center">Statut</div>
          <div className="col-span-1 text-right"></div>
        </div>

        {/* Table Body */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto custom-scrollbar">
          <PullToRefreshIndicator pullDistance={pullDistance} isRefreshing={isRefreshing} />
          {loading ? (
            <div className="p-16 text-center text-gray-500 flex flex-col items-center justify-center h-full gap-6">
              <div className="relative w-12 h-12">
                <div className="absolute inset-0 border-3 border-indigo-500/10 rounded-full" />
                <div className="absolute inset-0 border-t-3 border-indigo-500 rounded-full animate-spin" />
              </div>
              <span className="font-black uppercase tracking-[0.2em] text-[10px] text-white/40">Chargement...</span>
            </div>
          ) : (
            <div className="flex flex-col">
              <AnimatePresence mode="popLayout">
                {filteredAndSortedTargets.map((target, idx) => {
                  const priority = PRIORITY_COLORS[target.priorityLevel] || PRIORITY_COLORS["Veille Passive"];
                  const structureClass = STRUCTURE_COLORS[target.structure] || "bg-white/5 text-gray-400 border-white/10";

                  return (
                    <motion.div
                      layout
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.2, delay: idx * 0.02 }}
                      key={target.id}
                      onClick={() => router.push(`/targets/${target.id}`)}
                      className="flex flex-col lg:grid lg:grid-cols-12 gap-3 lg:gap-3 px-4 sm:px-6 py-3.5 lg:py-4 items-start lg:items-center hover:bg-white/[0.03] transition-all cursor-pointer group border-b border-white/[0.03] last:border-b-0"
                    >
                      {/* Entity */}
                      <div className="w-full lg:col-span-3 flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/[0.06] flex items-center justify-center text-gray-500 group-hover:text-indigo-400 group-hover:bg-indigo-500/10 group-hover:border-indigo-500/30 transition-all shrink-0 relative">
                          <Building size={18} />
                          {target.group?.is_group && (
                            <div className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-purple-500/20 border border-purple-500/30 flex items-center justify-center" title="Groupe">
                              <Network size={7} className="text-purple-400" />
                            </div>
                          )}
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="font-bold text-white text-sm group-hover:text-indigo-400 transition-colors tracking-tight leading-tight truncate">
                            {target.name}
                          </div>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className={`px-1.5 py-px rounded text-[7px] font-black uppercase tracking-wider border ${structureClass}`}>
                              {target.structure}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Sector */}
                      <div className="w-full lg:col-span-2 flex items-center justify-between lg:block">
                        <span className="lg:hidden text-[9px] font-black text-gray-600 uppercase tracking-widest">Secteur</span>
                        <span className="px-2.5 py-1 rounded-lg text-[10px] font-bold tracking-tight bg-indigo-500/5 text-indigo-400/80 border border-indigo-500/10">
                          {target.sector}
                        </span>
                      </div>

                      {/* Region */}
                      <div className="w-full lg:col-span-2 flex items-center justify-between lg:block">
                        <span className="lg:hidden text-[9px] font-black text-gray-600 uppercase tracking-widest">Région</span>
                        <span className="text-xs text-gray-400 font-medium">{target.region || "—"}</span>
                      </div>

                      {/* EBITDA */}
                      <div className="w-full lg:col-span-1 flex items-center justify-between lg:block">
                        <span className="lg:hidden text-[9px] font-black text-gray-600 uppercase tracking-widest">EBITDA</span>
                        <span className="text-xs text-gray-300 font-bold tracking-tight">{target.financials?.ebitda || "—"}</span>
                      </div>

                      {/* Score */}
                      <div className="w-full lg:col-span-2 flex items-center justify-between lg:justify-end">
                        <span className="lg:hidden text-[9px] font-black text-gray-600 uppercase tracking-widest">Score</span>
                        <div className="flex items-center gap-2">
                          <div className="hidden lg:block w-12 h-1 bg-white/5 rounded-full overflow-hidden">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${target.globalScore}%` }}
                              className={`h-full rounded-full ${target.globalScore >= 65 ? 'bg-emerald-500' : target.globalScore >= 45 ? 'bg-indigo-500' : target.globalScore >= 25 ? 'bg-amber-500' : 'bg-gray-600'}`}
                            />
                          </div>
                          <span className={`text-lg font-black leading-none tracking-tighter ${target.globalScore >= 65 ? 'text-emerald-400' : target.globalScore >= 45 ? 'text-white' : 'text-gray-400'}`}>
                            {target.globalScore}
                          </span>
                        </div>
                      </div>

                      {/* Priority badge */}
                      <div className="w-full lg:col-span-1 flex items-center justify-between lg:justify-center">
                        <span className="lg:hidden text-[9px] font-black text-gray-600 uppercase tracking-widest">Statut</span>
                        <span
                          className={`px-2 py-0.5 rounded-lg text-[7px] font-black uppercase tracking-wider border ${priority.bg} ${priority.text} ${priority.border}`}
                        >
                          {target.priorityLevel === "Action Prioritaire" ? "Action" : target.priorityLevel === "Veille Passive" ? "Veille" : target.priorityLevel}
                        </span>
                      </div>

                      {/* Arrow */}
                      <div className="absolute right-4 top-1/2 -translate-y-1/2 lg:relative lg:right-0 lg:top-0 lg:translate-y-0 lg:col-span-1 flex justify-end">
                        <div className="w-7 h-7 rounded-lg bg-white/[0.03] flex items-center justify-center text-gray-600 group-hover:text-white group-hover:bg-indigo-600 transition-all border border-white/5 group-hover:border-indigo-400">
                          <ChevronRight size={16} />
                        </div>
                      </div>
                    </motion.div>
                  );
                })}
              </AnimatePresence>

              {filteredAndSortedTargets.length === 0 && !loading && (
                <div className="p-16 sm:p-24 text-center flex flex-col items-center gap-5">
                  <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center">
                    <Target size={32} className="text-gray-700" />
                  </div>
                  <div>
                    <p className="font-black text-lg text-white mb-2 tracking-tighter">Aucun résultat</p>
                    <p className="text-gray-500 text-sm font-medium max-w-xs mx-auto">
                      Ajustez vos filtres ou le seuil de score.
                    </p>
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
