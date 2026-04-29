"use client";

import { useState, useEffect, useRef } from "react";
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

const VALID_MODES: Mode[] = ["dashboard", "chat", "pipeline", "watchlist", "explorer", "graph", "compare", "audit"];

function readHashMode(): Mode {
  if (typeof window === "undefined") return "dashboard";
  const fromHash = window.location.hash.replace("#", "") as Mode;
  return VALID_MODES.includes(fromHash) ? fromHash : "dashboard";
}

export default function Home() {
  // Lazy init évite d'écraser le hash au premier render. État source-of-truth
  // synchronisé avec window.location.hash dès le mount.
  const [mode, setMode] = useState<Mode>("dashboard");
  const [density] = useState<Density>("comfortable");
  const [showSidebar, setShowSidebar] = useState(true);
  const [openTarget, setOpenTarget] = useState<Target | null>(null);
  const [pitchTarget, setPitchTarget] = useState<Target | null>(null);
  const [showCmdK, setShowCmdK] = useState(false);

  const hashSyncedRef = useRef(false);

  // Sync hash → state au mount (et sur back/forward)
  useEffect(() => {
    setMode(readHashMode());
    hashSyncedRef.current = true;
    const onHash = () => setMode(readHashMode());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  // Sync state → hash UNIQUEMENT après que le hash initial ait été lu —
  // sinon on overwrite le hash avant que setMode du read prenne effet.
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!hashSyncedRef.current) return;
    const target = `#${mode}`;
    if (window.location.hash !== target) {
      window.history.replaceState(null, "", target);
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
