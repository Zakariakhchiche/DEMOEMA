"use client";

import { useState, useEffect } from "react";
import { Icon } from "./Icon";
import type { Target } from "@/lib/dem/types";

const STEPS = ["Identité + finances", "Compliance check", "Réseau dirigeants", "Génération PDF charte EdRCF"];

export function PitchModal({ target, onClose }: { target: Target; onClose: () => void }) {
  const [progress, setProgress] = useState(0);
  const done = progress >= 100;

  useEffect(() => {
    const id = setInterval(() => setProgress((p) => Math.min(p + 8, 100)), 110);
    return () => clearInterval(id);
  }, []);

  // a11y : ESC ferme la modale
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <>
      <div className="sheet-backdrop" onClick={onClose} />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="pitch-modal-title"
        style={{ position: "fixed", top: "30%", left: "50%", transform: "translateX(-50%)", width: 520, zIndex: 100 }}
      >
        <div className="dem-glass-2" style={{ borderRadius: 14, padding: 24 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Icon name="sparkles" size={18} color="var(--accent-purple)" />
            <div id="pitch-modal-title" style={{ fontSize: 15, fontWeight: 700 }}>Pitch Ready — {target.denomination}</div>
            <button className="dem-btn dem-btn-ghost dem-btn-icon" onClick={onClose} aria-label="Fermer (Esc)" style={{ marginLeft: "auto" }}>×</button>
          </div>
          <div style={{ marginTop: 16, height: 6, borderRadius: 999, background: "rgba(255,255,255,0.06)", overflow: "hidden" }}>
            <div style={{
              width: `${progress}%`, height: "100%",
              background: "linear-gradient(90deg, var(--accent-blue), var(--accent-purple), var(--accent-cyan))",
              transition: "width .15s ease",
            }} />
          </div>
          <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 8 }}>
            {STEPS.map((s, i) => {
              const stepProgress = (i + 1) * 25;
              const status = progress >= stepProgress ? "done" : progress >= stepProgress - 25 ? "active" : "pending";
              return (
                <div key={i} style={{
                  display: "flex", alignItems: "center", gap: 10,
                  fontSize: 12.5, color: status === "pending" ? "var(--text-muted)" : "var(--text-secondary)",
                }}>
                  <div style={{
                    width: 16, height: 16, borderRadius: 999,
                    background:
                      status === "done" ? "var(--accent-emerald)" :
                      status === "active" ? "rgba(167,139,250,0.30)" :
                      "rgba(255,255,255,0.06)",
                    display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                  }}>
                    {status === "done" && <Icon name="check" size={9} color="#0a0a0d" strokeWidth={3} />}
                    {status === "active" && (
                      <span style={{
                        width: 6, height: 6, borderRadius: 999,
                        background: "var(--accent-purple)",
                        animation: "dem-orbe-pulse 1s ease-in-out infinite",
                      }} />
                    )}
                  </div>
                  <span style={{ color: status === "done" ? "var(--text-primary)" : undefined }}>{s}</span>
                  {status === "active" && (
                    <span className="dem-mono" style={{ marginLeft: "auto", fontSize: 10.5, color: "var(--accent-purple)" }}>en cours…</span>
                  )}
                </div>
              );
            })}
          </div>
          {done && (
            <>
              <button
                className="dem-btn dem-btn-primary"
                onClick={() => {
                  // Bug S rapport QA — préfère /pitch-pdf/{siren} qui retourne
                  // un VRAI PDF (WeasyPrint). Si WeasyPrint indispo backend,
                  // l'endpoint fallback en HTML qu'on charge en nouvel onglet.
                  const url = `/api/datalake/pitch-pdf/${target.siren}`;
                  const w = window.open(url, "_blank", "noopener,noreferrer");
                  if (!w) {
                    window.location.href = url;
                  }
                }}
                style={{
                  width: "100%", marginTop: 18,
                  justifyContent: "center", padding: 12, fontSize: 13,
                }}
              >
                <Icon name="download" size={13} /> Imprimer / Save as PDF
              </button>
              <div style={{
                marginTop: 8, fontSize: 10.5, color: "var(--text-tertiary)",
                textAlign: "center",
              }}>
                Le navigateur ouvre le dialog d&apos;impression — choisis « Save as PDF »
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}
