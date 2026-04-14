"use client";

import { Search, Zap } from "lucide-react";

export default function MobileHeader() {
  const openSearch = () => {
    const event = new KeyboardEvent("keydown", {
      key: "k",
      ctrlKey: true,
      bubbles: true,
    });
    document.dispatchEvent(event);
  };

  return (
    <header className="lg:hidden flex items-center justify-between px-5 py-4 bg-black/60 backdrop-blur-xl border-b border-white/5 sticky top-0 z-[80] print:hidden">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
          <Zap size={16} className="text-white" />
        </div>
        <span className="text-white font-black text-sm tracking-tighter uppercase leading-none">
          EdRCF 6.0
        </span>
      </div>
      <button
        onClick={openSearch}
        className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-gray-400 active:scale-95 transition-transform"
        aria-label="Rechercher"
      >
        <Search size={18} />
      </button>
    </header>
  );
}
