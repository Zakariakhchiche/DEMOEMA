"use client";

import { useState, useEffect, useMemo } from "react";
import { Search, Command, Target as TargetIcon, Zap, Activity, Users, X, Building, ArrowRight } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import { SearchResult, Target } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

export function CommandPalette() {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [targets, setTargets] = useState<SearchResult[]>([]);
  const router = useRouter();

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setIsOpen((open) => !open);
      }
      if (e.key === "Escape") {
        setIsOpen(false);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  // Fetch targets when searching with debounce
  useEffect(() => {
    const timer = setTimeout(() => {
      if (search.length > 1) {
        fetch(`${API_URL}/api/targets?q=${encodeURIComponent(search)}`)
          .then(res => res.json())
          .then(data => {
            const results: SearchResult[] = data.data.map((t: Target) => ({
              id: t.id,
              name: t.name,
              sector: t.sector,
              type: "target",
              path: `/targets/${t.id}`
            }));
            setTargets(results);
          })
          .catch(err => console.error("Search failed:", err));
      } else {
        setTargets([]);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [search]);

  const pages: SearchResult[] = [
    { id: "dashboard", name: "Dashboard", sector: "Overview", type: "page", path: "/" },
    { id: "targets-dir", name: "Targets Directory", sector: "Intelligence", type: "page", path: "/targets" },
    { id: "pipeline", name: "Origination Pipeline", sector: "Deals", type: "page", path: "/pipeline" },
    { id: "signals", name: "Market Signals Feed", sector: "Signals", type: "page", path: "/signals" },
    { id: "graph", name: "Relationship Explorer", sector: "Networking", type: "page", path: "/graph" },
  ];

  const filteredPages = useMemo(() => 
    pages.filter(p => p.name.toLowerCase().includes(search.toLowerCase())),
    [search]
  );

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsOpen(false)}
            className="fixed inset-0 bg-black/80 backdrop-blur-md z-[100]"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="fixed left-0 sm:left-1/2 top-0 sm:top-[12%] sm:-translate-x-1/2 w-full max-w-2xl h-full sm:h-auto bg-[#0a0a0a] border-b sm:border border-white/10 sm:rounded-2xl shadow-[0_0_80px_rgba(0,0,0,0.8)] z-[101] overflow-hidden flex flex-col"
          >
            <div className="flex items-center gap-4 p-4 sm:p-5 border-b border-white/10 shrink-0">
              <Search className="text-indigo-500 shrink-0" size={20} />
              <input
                autoFocus
                placeholder="Search engine..."
                className="flex-1 bg-transparent border-none outline-none text-white text-lg sm:text-xl placeholder-gray-600 font-medium"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <button 
                onClick={() => setIsOpen(false)}
                className="sm:hidden p-2 text-gray-400 hover:text-white"
              >
                <X size={20} />
              </button>
              <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/5 border border-white/10 text-[10px] text-gray-500 font-black tracking-widest uppercase">
                ESC
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
              
              {/* Pages Section */}
              {filteredPages.length > 0 && (
                <div className="mb-6">
                  <div className="px-3 py-2 text-[10px] font-black text-gray-500 uppercase tracking-[0.2em] mb-2">
                    System Navigation
                  </div>
                  <div className="space-y-1">
                    {filteredPages.map((item) => (
                      <button
                        key={item.id}
                        onClick={() => {
                          router.push(item.path);
                          setIsOpen(false);
                          setSearch("");
                        }}
                        className="w-full flex items-center justify-between p-4 rounded-2xl hover:bg-white/5 group transition-all text-left"
                      >
                        <div className="flex items-center gap-4">
                          <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/5 flex items-center justify-center text-gray-500 group-hover:text-indigo-400 group-hover:bg-indigo-500/10 group-hover:border-indigo-500/20 transition-all">
                            {item.id === 'dashboard' && <Command size={18} />}
                            {item.id === 'targets-dir' && <TargetIcon size={18} />}
                            {item.id === 'pipeline' && <Zap size={18} />}
                            {item.id === 'signals' && <Activity size={18} />}
                            {item.id === 'graph' && <Users size={18} />}
                          </div>
                          <div>
                            <span className="text-gray-200 group-hover:text-white font-bold block leading-none mb-1">
                              {item.name}
                            </span>
                            <span className="text-[10px] font-bold text-gray-600 uppercase tracking-widest">{item.sector}</span>
                          </div>
                        </div>
                        <ArrowRight size={16} className="text-gray-700 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Targets Section */}
              {targets.length > 0 && (
                <div>
                  <div className="px-3 py-2 text-[10px] font-black text-gray-500 uppercase tracking-[0.2em] mb-2">
                    Intelligence Entities
                  </div>
                  <div className="space-y-1">
                    {targets.map((item) => (
                      <button
                        key={item.id}
                        onClick={() => {
                          router.push(item.path);
                          setIsOpen(false);
                          setSearch("");
                        }}
                        className="w-full flex items-center justify-between p-4 rounded-2xl hover:bg-white/5 group transition-all text-left"
                      >
                        <div className="flex items-center gap-4">
                          <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/5 flex items-center justify-center text-gray-500 group-hover:text-indigo-400 group-hover:bg-indigo-500/10 group-hover:border-indigo-500/20 transition-all">
                            <Building size={18} />
                          </div>
                          <div>
                            <span className="text-gray-200 group-hover:text-white font-bold block leading-none mb-1">
                              {item.name}
                            </span>
                            <span className="text-[10px] font-bold text-indigo-400/60 uppercase tracking-widest">{item.sector}</span>
                          </div>
                        </div>
                        <div className="flex flex-col items-end opacity-0 group-hover:opacity-100 transition-opacity">
                           <span className="text-[9px] font-black text-white px-2 py-0.5 rounded bg-indigo-600 uppercase tracking-widest">Open Intel</span>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {filteredPages.length === 0 && targets.length === 0 && (
                <div className="p-12 text-center text-gray-500 flex flex-col items-center gap-4">
                  <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center border border-white/10">
                    <Search size={32} className="opacity-20" />
                  </div>
                  <div>
                    <p className="font-bold text-white mb-1">No intelligence matches.</p>
                    <p className="text-sm">Try searching for a company name, sector, or systemic trigger.</p>
                  </div>
                </div>
              )}
            </div>

            <div className="p-4 bg-white/[0.02] border-t border-white/10 flex justify-between items-center text-[10px] font-black text-gray-600 uppercase tracking-widest">
              <div className="flex gap-4">
                <span>↵ Select</span>
                <span>↑↓ Navigate</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,1)]" />
                Aethelgard Core Engine
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

