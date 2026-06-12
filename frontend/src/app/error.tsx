"use client";

import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[Origin] Unhandled error:", error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-[#050505] text-white p-8">
      <div className="w-20 h-20 rounded-[2rem] bg-rose-500/10 border border-rose-500/20 flex items-center justify-center mb-6">
        <AlertTriangle size={40} className="text-rose-500" />
      </div>
      <h2 className="text-2xl font-black tracking-tighter mb-3">
        Erreur inattendue
      </h2>
      <p className="text-gray-400 mb-8 max-w-sm text-center text-sm">
        Une erreur est survenue. Veuillez reessayer ou revenir a l&apos;accueil.
      </p>
      <div className="flex gap-4">
        <button
          onClick={reset}
          className="px-8 py-4 bg-indigo-600 text-white rounded-2xl font-black uppercase tracking-widest text-[10px] hover:bg-indigo-500 transition-all"
        >
          Reessayer
        </button>
        <a
          href="/"
          className="px-8 py-4 bg-white/5 border border-white/10 text-white rounded-2xl font-black uppercase tracking-widest text-[10px] hover:bg-white/10 transition-all"
        >
          Accueil
        </a>
      </div>
    </div>
  );
}
