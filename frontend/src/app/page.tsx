"use client";

import { useState, useEffect } from "react";
import { TopHeader } from "@/components/dem/TopHeader";
import { ChatPanel } from "@/components/dem/ChatPanel";
import { DashboardView } from "@/components/dem/DashboardView";
import { DataExplorerView } from "@/components/dem/DataExplorerView";
import { PipelineView } from "@/components/dem/PipelineView";
import { WatchlistView } from "@/components/dem/WatchlistView";
import { AuditView } from "@/components/dem/AuditView";
import { CompareView } from "@/components/dem/CompareView";
import { NetworkGraphView } from "@/components/dem/NetworkGraphView";
import { TargetSheet } from "@/components/dem/TargetSheet";
import { CmdPalette } from "@/components/dem/CmdPalette";
import { PitchModal } from "@/components/dem/PitchModal";
import type { Mode, Target, Density } from "@/lib/dem/types";

export default function Home() {
  const [mode, setMode] = useState<Mode>("dashboard");
  const [density] = useState<Density>("comfortable");
  const [showSidebar, setShowSidebar] = useState(true);
  const [openTarget, setOpenTarget] = useState<Target | null>(null);
  const [pitchTarget, setPitchTarget] = useState<Target | null>(null);
  const [showCmdK, setShowCmdK] = useState(false);

  // Persist mode in URL hash for shareable links
  useEffect(() => {
    if (typeof window === "undefined") return;
    const fromHash = window.location.hash.replace("#", "") as Mode;
    if (fromHash && ["dashboard", "chat", "pipeline", "watchlist", "explorer", "graph", "compare", "audit"].includes(fromHash)) {
      setMode(fromHash);
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.location.hash !== `#${mode}`) {
      window.history.replaceState(null, "", `#${mode}`);
    }
  }, [mode]);

  // Keyboard shortcuts
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setShowCmdK(true);
      }
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "b") {
        e.preventDefault();
        setShowSidebar((s) => !s);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="dem-shell" style={{
      height: "100vh",
      display: "flex", flexDirection: "column",
      position: "relative", overflow: "hidden",
    }}>
      <div className="aurora-bg" />

      <TopHeader mode={mode} setMode={setMode} onCmdK={() => setShowCmdK(true)} />

      <div style={{ flex: 1, display: "flex", overflow: "hidden", position: "relative", zIndex: 1 }}>
        {mode === "dashboard" && <DashboardView onMode={setMode} onOpenTarget={setOpenTarget} />}
        {mode === "chat" && (
          <ChatPanel
            density={density}
            onOpenTarget={setOpenTarget}
            onPitch={setPitchTarget}
            showSidebar={showSidebar}
          />
        )}
        {mode === "pipeline" && <PipelineView onOpenTarget={setOpenTarget} />}
        {mode === "watchlist" && <WatchlistView onOpenTarget={setOpenTarget} />}
        {mode === "explorer" && <DataExplorerView onOpenTarget={setOpenTarget} />}
        {mode === "graph" && <NetworkGraphView />}
        {mode === "compare" && <CompareView />}
        {mode === "audit" && <AuditView />}
      </div>

      {openTarget && (
        <TargetSheet
          target={openTarget}
          onClose={() => setOpenTarget(null)}
          onPitch={() => setPitchTarget(openTarget)}
        />
      )}
      {pitchTarget && <PitchModal target={pitchTarget} onClose={() => setPitchTarget(null)} />}
      {showCmdK && (
        <CmdPalette
          onClose={() => setShowCmdK(false)}
          onCommand={(t) => {
            setMode("chat");
            setShowCmdK(false);
            // Le ChatPanel auto-submit n'est pas trivial — on laisse l'utilisateur valider
            console.log("[CmdPalette] command:", t);
          }}
        />
      )}
    </div>
  );
}
