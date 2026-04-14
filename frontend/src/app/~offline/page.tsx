"use client";

import { WifiOff } from "lucide-react";

export default function OfflinePage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-6">
      <div className="w-20 h-20 rounded-[2rem] bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mb-8">
        <WifiOff size={36} className="text-amber-500" />
      </div>
      <h1 className="text-3xl font-black text-white tracking-tighter mb-4">
        Mode Hors Ligne
      </h1>
      <p className="text-gray-400 text-base max-w-md mb-8 leading-relaxed">
        Vous êtes actuellement hors ligne. Certaines données en cache restent
        accessibles. Reconnectez-vous pour accéder à toutes les fonctionnalités.
      </p>
      <button
        onClick={() => window.location.reload()}
        className="px-8 py-3.5 rounded-2xl bg-indigo-600 text-white font-black text-xs uppercase tracking-widest hover:bg-indigo-500 transition-all shadow-2xl active:scale-95"
      >
        Réessayer
      </button>
    </div>
  );
}
