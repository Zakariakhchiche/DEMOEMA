"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Lottie from "lottie-react";
import { Zap } from "lucide-react";
import radarPulse from "../../public/lottie/radar-pulse.json";

export default function SplashScreen() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Show once per browser session (version-keyed so new deploys re-show it)
    const KEY = "edrcf-splash-v6";
    if (typeof sessionStorage !== "undefined" && !sessionStorage.getItem(KEY)) {
      sessionStorage.setItem(KEY, "1");
      setVisible(true);
      // Begin fade-out at 2.4s, fully gone at 3s
      const t = setTimeout(() => setVisible(false), 2400);
      return () => clearTimeout(t);
    }
  }, []);

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 1 }}
          exit={{ opacity: 0, scale: 1.04 }}
          transition={{ duration: 0.55, ease: [0.4, 0, 0.2, 1] }}
          className="fixed inset-0 z-[9999] bg-[#050505] flex flex-col items-center justify-center select-none"
          aria-hidden="true"
        >
          {/* Ambient glow */}
          <div className="absolute inset-0 overflow-hidden pointer-events-none">
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] rounded-full bg-indigo-500/[0.08] blur-[140px]" />
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[240px] h-[240px] rounded-full bg-indigo-600/[0.12] blur-[60px]" />
          </div>

          {/* Lottie radar */}
          <div className="w-44 h-44 sm:w-56 sm:h-56 relative z-10">
            <Lottie animationData={radarPulse} loop autoplay />
          </div>

          {/* Brand lockup */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.35, duration: 0.55, ease: [0.0, 0, 0.2, 1] }}
            className="flex flex-col items-center gap-3 relative z-10 -mt-2"
          >
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-[1.2rem] bg-indigo-600 flex items-center justify-center shadow-[0_0_48px_rgba(79,70,229,0.55)] border border-white/10 relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-white/20 to-transparent" />
                <Zap size={24} className="text-white relative z-10" />
              </div>
              <span className="text-white font-black text-3xl tracking-tighter uppercase leading-none">
                Origin
              </span>
            </div>
            <span className="text-[9px] font-black text-indigo-400/80 uppercase tracking-[0.45em] leading-none">
              AI Origination Platform
            </span>
          </motion.div>

          {/* Progress bar */}
          <div className="absolute bottom-12 w-40 h-[2px] bg-white/[0.06] rounded-full overflow-hidden">
            <motion.div
              initial={{ width: "0%" }}
              animate={{ width: "100%" }}
              transition={{ delay: 0.2, duration: 2.0, ease: "easeInOut" }}
              className="h-full bg-indigo-500 rounded-full shadow-[0_0_8px_rgba(99,102,241,0.8)]"
            />
          </div>

          {/* Version tag */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6, duration: 0.4 }}
            className="absolute bottom-6 text-[8px] font-black text-gray-700 uppercase tracking-[0.3em]"
          >
            Origin CF · v6.0
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
