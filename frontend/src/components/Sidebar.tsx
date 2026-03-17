"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Target, Network, Layers, Activity, Search, Sparkles, Zap, ShieldCheck, Settings, LogOut, ChevronRight, Fingerprint } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function Sidebar({ isOpen, setIsOpen }: { isOpen: boolean, setIsOpen: (o: boolean) => void }) {
  const pathname = usePathname();
  
  const navItems = [
    { label: "Dashboard", icon: LayoutDashboard, href: "/" },
    { label: "Strategic Targets", icon: Target, href: "/targets" },
    { label: "Relationship Graph", icon: Network, href: "/graph" },
    { label: "Pipeline Command", icon: Layers, href: "/pipeline" },
    { label: "Market Intelligence", icon: Activity, href: "/signals" },
  ];

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
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[90] lg:hidden"
          />
        )}
      </AnimatePresence>

      <aside className={`
        fixed left-0 top-0 h-screen bg-black/40 backdrop-blur-3xl border-r border-white/5 flex flex-col p-6 z-[100] transition-all duration-500 
        ${isOpen ? "translate-x-0 w-72" : "-translate-x-full lg:translate-x-0 w-72"}
        lg:hover:border-white/10
      `}>
        {/* Branding */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4 px-2 py-4 group cursor-pointer">
            <div className="w-10 h-10 rounded-[1.2rem] bg-indigo-600 flex items-center justify-center shadow-[0_0_30px_rgba(79,70,229,0.4)] border border-white/10 group-hover:scale-110 transition-transform duration-500 relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-white/20 to-transparent" />
              <Zap size={20} className="text-white relative z-10" />
            </div>
            <div>
              <span className="text-white font-black text-base tracking-tighter uppercase block leading-none">Aethelgard</span>
              <div className="flex items-center gap-1.5 mt-1">
                 <div className="w-1 h-1 rounded-full bg-indigo-500" />
                 <span className="text-[8px] font-black text-indigo-400 uppercase tracking-[0.2em] leading-none">Transactional Engine</span>
              </div>
            </div>
          </div>
          <button onClick={() => setIsOpen(false)} className="lg:hidden text-gray-400 hover:text-white">
             <ChevronRight className="rotate-180" size={24} />
          </button>
        </div>

      {/* Global Search Trigger */}
      <div className="relative mb-10 group cursor-pointer" onClick={() => {
        const event = new KeyboardEvent('keydown', {
          key: 'k',
          ctrlKey: true,
          bubbles: true
        });
        document.dispatchEvent(event);
      }}>
        <div className="absolute inset-0 bg-indigo-500/5 blur-xl group-hover:bg-indigo-500/10 transition-all opacity-0 group-hover:opacity-100" />
        <div className="relative w-full bg-white/[0.03] border border-white/10 rounded-2xl py-3 pl-12 pr-4 text-xs text-gray-400 flex justify-between items-center group-hover:bg-white/[0.06] group-hover:border-white/20 transition-all font-black uppercase tracking-widest ring-1 ring-transparent group-hover:ring-indigo-500/20">
          <Search size={16} className="absolute left-4 text-gray-600 group-hover:text-indigo-400 transition-colors" />
          <span>Intercept...</span>
          <span className="px-2 py-1 rounded-lg bg-black border border-white/10 text-[9px] font-black text-gray-500 shadow-xl group-hover:text-white transition-colors">⌘K</span>
        </div>
      </div>

      {/* Primary Navigation */}
      <nav className="flex-1 flex flex-col gap-1.5">
        <div className="px-3 py-2 text-[9px] font-black text-gray-600 uppercase tracking-[0.3em] mb-2 flex items-center gap-3">
          <div className="w-4 h-px bg-gray-800" /> Intelligence Modules
        </div>
        
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
          
          return (
            <Link 
              key={item.label} 
              href={item.href}
              className={`flex items-center gap-4 px-4 py-3.5 rounded-2xl text-[13px] font-black uppercase tracking-widest transition-all duration-300 group/nav relative
                ${isActive 
                  ? "text-white bg-white/5 border border-white/10 shadow-[0_10px_30px_rgba(0,0,0,0.3)]" 
                  : "text-gray-500 hover:text-gray-200 hover:bg-white/[0.02]"
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
              
              {!isActive && item.label === "Market Intelligence" && (
                <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20">
                   <span className="text-[9px] font-black text-amber-500">3</span>
                </div>
              )}
            </Link>
          );
        })}

        {/* AI Action */}
        <div className="mt-10">
           <button 
             onClick={() => window.dispatchEvent(new CustomEvent("toggle-copilot"))}
             className="w-full flex items-center gap-4 px-5 py-5 rounded-[2rem] text-[12px] font-black uppercase tracking-[0.2em] transition-all duration-500 bg-white text-black hover:bg-indigo-600 hover:text-white group border border-transparent shadow-2xl shadow-indigo-500/10 hover:shadow-indigo-600/40 active:scale-95"
           >
              <div className="relative">
                <Sparkles size={20} className="text-indigo-600 group-hover:text-white transition-all duration-500 group-hover:rotate-12" />
                <div className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
              </div>
              <span className="flex-1 text-left">Ask Copilot</span>
              <div className="w-6 h-6 rounded-full bg-black/5 flex items-center justify-center group-hover:bg-white/20 transition-colors">
                <ChevronRight size={14} />
              </div>
           </button>
        </div>
      </nav>

      {/* Footer Profile */}
      <div className="mt-auto pt-8">
        <div className="p-5 rounded-[2.5rem] bg-white/[0.02] border border-white/5 group hover:border-indigo-500/30 transition-all cursor-pointer relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
          
          <div className="flex items-center justify-between mb-4 relative z-10">
             <div className="flex items-center gap-2.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[9px] font-black uppercase tracking-[0.2em]">
                <ShieldCheck size={12} /> SECURED
             </div>
             <Settings size={14} className="text-gray-700 hover:text-white transition-colors" />
          </div>

          <div className="flex items-center gap-4 relative z-10">
            <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center font-black text-indigo-400 group-hover:bg-indigo-600 group-hover:text-white transition-all transform duration-500 text-sm">
               JD
            </div>
            <div>
              <div className="flex items-center gap-2">
                 <div className="text-sm text-white font-black tracking-tight">John Doe</div>
                 <Fingerprint size={12} className="text-gray-700" />
              </div>
              <div className="text-[9px] text-gray-500 uppercase tracking-widest font-black mt-0.5 mt-1 border border-white/5 px-2 py-0.5 rounded-lg inline-block">Managing Lead</div>
            </div>
          </div>
        </div>
      </div>
    </aside>
    </>
  );
}


