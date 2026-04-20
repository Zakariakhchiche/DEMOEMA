"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Target, Network, Layers, Activity,
  Search, Sparkles, Zap, ShieldCheck, Settings,
  ChevronRight, Fingerprint, Bell, BellOff, Download, Map, BarChart2,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface SidebarProps {
  isOpen: boolean;
  setIsOpen: (o: boolean) => void;
  notifPermission?: NotificationPermission;
  hasInstallPrompt?: boolean;
}

export default function Sidebar({
  isOpen, setIsOpen, notifPermission = "default", hasInstallPrompt = false,
}: SidebarProps) {
  const pathname = usePathname();
  const [signalCount, setSignalCount] = useState(0);

  useEffect(() => {
    fetch(`/api/targets`)
      .then(res => res.json())
      .then(data => {
        const allSignals = (data.data || []).reduce(
          (acc: number, t: { topSignals?: unknown[] }) => acc + (t.topSignals?.length || 0),
          0
        );
        setSignalCount(allSignals);
      })
      .catch(() => {});
  }, []);

  const navItems = [
    { label: "Tableau de Bord", icon: LayoutDashboard, href: "/", badge: null },
    { label: "Intelligence Vault", icon: Target, href: "/targets", badge: null },
    { label: "Graphe Réseau", icon: Network, href: "/graph", badge: null },
    { label: "Pipeline M&A", icon: Layers, href: "/pipeline", badge: null },
    { label: "Signaux Marché", icon: Activity, href: "/signals", badge: signalCount > 0 ? signalCount : null },
    { label: "Carte Opportunités", icon: Map, href: "/map", badge: null },
    { label: "Analytics", icon: BarChart2, href: "/analytics", badge: null },
  ];

  const notifGranted = notifPermission === "granted";
  const notifDenied = notifPermission === "denied";

  return (
    <>
      {/* Mobile Backdrop */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsOpen(false)}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-90 lg:hidden"
          />
        )}
      </AnimatePresence>

      <aside className={`
        fixed left-0 top-0 h-dvh bg-black/40 backdrop-blur-3xl border-r border-white/5 flex flex-col p-4 lg:p-5 z-100 transition-all duration-500
        ${isOpen ? "translate-x-0 w-full max-w-xs sm:max-w-none sm:w-72" : "-translate-x-full lg:translate-x-0 w-72"}
        lg:hover:border-white/10
      `}>
        {/* Branding */}
        <div className="flex items-center justify-between mb-4 shrink-0">
          <div className="flex items-center gap-4 px-2 py-4 group cursor-pointer">
            <div className="w-10 h-10 rounded-[1.2rem] bg-indigo-600 flex items-center justify-center shadow-[0_0_30px_rgba(79,70,229,0.4)] border border-white/10 group-hover:scale-110 transition-transform duration-500 relative overflow-hidden">
              <div className="absolute inset-0 bg-linear-to-br from-white/20 to-transparent" />
              <Zap size={20} className="text-white relative z-10" />
            </div>
            <div>
              <span className="text-white font-black text-base tracking-tighter uppercase block leading-none">EdRCF 6.0</span>
              <div className="flex items-center gap-1.5 mt-1">
                <div className="w-1 h-1 rounded-full bg-indigo-500" />
                <span className="text-[8px] font-black text-indigo-400 uppercase tracking-[0.2em] leading-none">AI Origination Platform</span>
              </div>
            </div>
          </div>
          <button onClick={() => setIsOpen(false)} className="lg:hidden text-gray-400 hover:text-white">
            <ChevronRight className="rotate-180" size={24} />
          </button>
        </div>

        {/* Global Search Trigger */}
        <div className="relative mb-4 shrink-0 group cursor-pointer" onClick={() => {
          document.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true, bubbles: true }));
        }}>
          <div className="absolute inset-0 bg-indigo-500/5 blur-xl group-hover:bg-indigo-500/10 transition-all opacity-0 group-hover:opacity-100" />
          <div className="relative w-full bg-white/3 border border-white/10 rounded-2xl py-3 pl-12 pr-4 text-xs text-gray-400 flex justify-between items-center group-hover:bg-white/6 group-hover:border-white/20 transition-all font-black uppercase tracking-widest ring-1 ring-transparent group-hover:ring-indigo-500/20">
            <Search size={16} className="absolute left-4 text-gray-600 group-hover:text-indigo-400 transition-colors" />
            <span>Rechercher...</span>
            <span className="px-2 py-1 rounded-lg bg-black border border-white/10 text-[9px] font-black text-gray-500 shadow-xl group-hover:text-white transition-colors">⌘K</span>
          </div>
        </div>

        {/* Primary Navigation */}
        <nav className="flex-1 flex flex-col gap-1.5 overflow-y-auto min-h-0 custom-scrollbar">
          <div className="px-3 py-2 text-[9px] font-black text-gray-600 uppercase tracking-[0.3em] mb-2 flex items-center gap-3">
            <div className="w-4 h-px bg-gray-800" /> Modules Intelligence
          </div>

          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));

            return (
              <Link
                key={item.label}
                href={item.href}
                onClick={() => setIsOpen(false)}
                className={`flex items-center gap-4 px-4 py-3.5 rounded-2xl text-[13px] font-black uppercase tracking-widest transition-all duration-300 group/nav relative
                  ${isActive
                    ? "text-white bg-white/5 border border-white/10 shadow-[0_10px_30px_rgba(0,0,0,0.3)]"
                    : "text-gray-500 hover:text-gray-200 hover:bg-white/2"
                  }
                `}
              >
                {isActive && (
                  <motion.div
                    layoutId="active-pill"
                    className="absolute left-0 w-1 h-6 bg-indigo-500 rounded-full"
                  />
                )}
                <Icon size={18} className={`transition-all duration-300 ${isActive ? "text-indigo-500 scale-110" : "text-gray-600 group-hover/nav:text-white group-hover/nav:scale-110"}`} />
                <span className="flex-1">{item.label}</span>

                {isActive && <ChevronRight size={14} className="text-gray-700" />}

                {!isActive && item.badge && (
                  <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20">
                    <span className="text-[9px] font-black text-amber-500">{item.badge}</span>
                  </div>
                )}
              </Link>
            );
          })}

          {/* AI Copilot */}
          <div className="mt-4 lg:mt-6">
            <button
              onClick={() => window.dispatchEvent(new CustomEvent("toggle-copilot"))}
              className="w-full flex items-center gap-3 px-4 py-3.5 rounded-2xl text-[11px] font-black uppercase tracking-[0.2em] transition-all duration-500 bg-white text-black hover:bg-indigo-600 hover:text-white group border border-transparent shadow-2xl shadow-indigo-500/10 hover:shadow-indigo-600/40 active:scale-95"
            >
              <div className="relative">
                <Sparkles size={20} className="text-indigo-600 group-hover:text-white transition-all duration-500 group-hover:rotate-12" />
                <div className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
              </div>
              <span className="flex-1 text-left">Copilot IA</span>
              <div className="w-6 h-6 rounded-full bg-black/5 flex items-center justify-center group-hover:bg-white/20 transition-colors">
                <ChevronRight size={14} />
              </div>
            </button>
          </div>

          {/* ── PWA Actions ──────────────────────────────────────────── */}
          <div className="mt-3 flex flex-col gap-2">
            {/* Notification toggle */}
            {!notifDenied && (
              <button
                onClick={() => window.dispatchEvent(new CustomEvent("edrcf-request-notif"))}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-2xl text-[11px] font-black uppercase tracking-[0.15em] transition-all duration-300 border active:scale-95
                  ${notifGranted
                    ? "bg-emerald-500/8 border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/15"
                    : "bg-white/3 border-white/10 text-gray-500 hover:text-gray-200 hover:bg-white/6"
                  }`}
              >
                {notifGranted
                  ? <Bell size={15} className="text-emerald-400 shrink-0" />
                  : <BellOff size={15} className="text-gray-600 shrink-0" />
                }
                <span className="flex-1 text-left">
                  {notifGranted ? "Notifications actives" : "Activer alertes"}
                </span>
                {notifGranted && (
                  <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shrink-0" />
                )}
              </button>
            )}

            {/* Install PWA — only shown when prompt is available */}
            {hasInstallPrompt && (
              <button
                onClick={() => window.dispatchEvent(new CustomEvent("edrcf-install-app"))}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-2xl text-[11px] font-black uppercase tracking-[0.15em] transition-all duration-300 border bg-indigo-500/8 border-indigo-500/20 text-indigo-400 hover:bg-indigo-500/15 active:scale-95"
              >
                <Download size={15} className="text-indigo-400 shrink-0" />
                <span className="flex-1 text-left">Installer l&apos;app</span>
                <ChevronRight size={13} className="text-indigo-600 shrink-0" />
              </button>
            )}
          </div>
        </nav>

        {/* Footer Profile */}
        <div className="pt-3 shrink-0 border-t border-white/5 mt-3">
          <div className="p-3 rounded-2xl bg-white/[0.02] border border-white/5 group hover:border-indigo-500/30 transition-all cursor-pointer relative overflow-hidden">
            <div className="absolute inset-0 bg-linear-to-br from-indigo-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

            <div className="flex items-center gap-3 relative z-10">
              <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center font-black text-indigo-400 group-hover:bg-indigo-600 group-hover:text-white transition-all duration-500 text-xs shrink-0">
                QM
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <div className="text-sm text-white font-black tracking-tight truncate">Quentin Moreau</div>
                  <Fingerprint size={10} className="text-gray-700 shrink-0" />
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-[8px] text-gray-500 uppercase tracking-widest font-black">Analyste Senior</span>
                  <span className="flex items-center gap-1 text-emerald-400 text-[8px] font-black uppercase">
                    <ShieldCheck size={10} /> OK
                  </span>
                </div>
              </div>
              <Settings size={14} className="text-gray-700 hover:text-white transition-colors shrink-0" />
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
