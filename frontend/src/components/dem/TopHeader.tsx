"use client";

import { useState, useEffect, useRef } from "react";
import { Icon } from "./Icon";
import type { Mode } from "@/lib/dem/types";

const TABS: { k: Mode; icon: string; label: string }[] = [
  { k: "dashboard", icon: "grid", label: "Home" },
  { k: "chat", icon: "chat", label: "Chat" },
  { k: "pipeline", icon: "kanban", label: "Pipeline" },
  { k: "watchlist", icon: "bookmark", label: "Watchlist" },
  { k: "explorer", icon: "table", label: "Explorer" },
  { k: "graph", icon: "network", label: "Graphe" },
  { k: "compare", icon: "grid", label: "Comparer" },
  { k: "audit", icon: "shield", label: "Audit" },
];

interface Props {
  mode: Mode;
  setMode: (m: Mode) => void;
  onCmdK: () => void;
}

type Notif = { id: string; type: string; label: string; href: string; ts: string };

function formatRelTime(ts: string): string {
  try {
    const d = new Date(ts).getTime();
    const diff = (Date.now() - d) / 1000;
    if (diff < 60) return "à l'instant";
    if (diff < 3600) return `il y a ${Math.floor(diff / 60)} min`;
    if (diff < 86400) return `il y a ${Math.floor(diff / 3600)} h`;
    return `il y a ${Math.floor(diff / 86400)} j`;
  } catch { return ""; }
}

function NotifPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [items, setItems] = useState<Notif[]>([]);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    fetch("/api/datalake/dashboard")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (cancelled || !d) { setLoading(false); return; }
        const out: Notif[] = [];
        // Top targets — 3 dernières
        (d.top_targets || []).slice(0, 3).forEach((t: { siren: string; denomination: string }, i: number) => {
          out.push({ id: `tt-${t.siren}`, type: "cible", label: t.denomination, href: `#chat`, ts: new Date(Date.now() - i * 7200_000).toISOString() });
        });
        // Signaux récents
        (d.signaux_recents || []).slice(0, 5).forEach((s: { siren: string; type?: string; ts?: string; label?: string }) => {
          out.push({ id: `sig-${s.siren}-${s.ts}`, type: s.type || "signal", label: s.label || `Signal ${s.siren}`, href: `#chat`, ts: s.ts || new Date().toISOString() });
        });
        setItems(out);
        setLoading(false);
      })
      .catch(() => setLoading(false));
    return () => { cancelled = true; };
  }, [open]);
  if (!open) return null;
  return (
    <>
      <div onClick={onClose} style={{ position: "fixed", inset: 0, zIndex: 90 }} />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Notifications"
        className="dem-glass-2"
        style={{
          position: "fixed", top: 56, right: 12, width: 360, maxHeight: "70vh", overflowY: "auto",
          zIndex: 100, borderRadius: 12, padding: 14,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
          <Icon name="bell" size={14} color="var(--accent-purple)" />
          <div style={{ fontSize: 13, fontWeight: 700 }}>Notifications</div>
          <button className="dem-btn dem-btn-ghost dem-btn-icon" onClick={onClose} aria-label="Fermer" style={{ marginLeft: "auto" }}>×</button>
        </div>
        {loading && <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Chargement…</div>}
        {!loading && items.length === 0 && <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Aucune notification.</div>}
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {items.map((n) => (
            <a
              key={n.id}
              href={n.href}
              style={{
                padding: "10px 12px", borderRadius: 8,
                border: "1px solid var(--border-subtle)",
                background: "rgba(255,255,255,0.02)",
                fontSize: 12.5, color: "var(--text-secondary)",
                textDecoration: "none", display: "flex", flexDirection: "column", gap: 4,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span className="dem-mono" style={{ fontSize: 10, color: "var(--accent-purple)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600 }}>{n.type}</span>
                <span style={{ marginLeft: "auto", fontSize: 10.5, color: "var(--text-tertiary)" }}>{formatRelTime(n.ts)}</span>
              </div>
              <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>{n.label}</span>
            </a>
          ))}
        </div>
      </div>
    </>
  );
}

export function TopHeader({ mode, setMode, onCmdK }: Props) {
  const [notifOpen, setNotifOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const bellRef = useRef<HTMLButtonElement | null>(null);

  // Bug T rapport QA — responsive : tabs nav cachée < 900px, hamburger à la place
  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 900);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  return (
    // Bug v6/1.7 — landmark <header> + <nav> requis pour axe 'region' /
    // 'landmark-one-main'. Le header global wrappe la nav primaire.
    <header role="banner" style={{
      height: 52,
      borderBottom: "1px solid var(--border-subtle)",
      display: "flex", alignItems: "center",
      padding: "0 16px", gap: 16,
      background: "rgba(10,10,13,0.60)",
      backdropFilter: "blur(20px)",
      position: "relative", zIndex: 10,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div aria-hidden="true" style={{
          width: 24, height: 24, borderRadius: 7,
          background: "conic-gradient(from 90deg, #60a5fa, #a78bfa, #67e8f9, #60a5fa)",
          boxShadow: "0 0 16px -2px rgba(167,139,250,0.5)",
        }} />
        <div style={{ fontWeight: 700, letterSpacing: "-0.02em", fontSize: 15, color: "var(--text-primary)" }}>DEMOEMA</div>
        <span style={{
          fontSize: 10, padding: "2px 6px", borderRadius: 4,
          background: "rgba(167,139,250,0.10)",
          border: "1px solid rgba(167,139,250,0.25)",
          color: "var(--accent-purple)",
          fontWeight: 600, letterSpacing: "0.05em",
        }}>BETA</span>
      </div>

      {!isMobile && (
        <nav aria-label="Navigation principale" style={{
          display: "flex", gap: 2, marginLeft: 16, padding: 3,
          background: "rgba(255,255,255,0.025)", borderRadius: 8,
          border: "1px solid var(--border-subtle)",
        }}>
          {TABS.map((t) => (
            <button
              key={t.k}
              onClick={() => setMode(t.k)}
              style={{
                display: "inline-flex", alignItems: "center", gap: 6,
                padding: "5px 11px", borderRadius: 6, border: "none",
                background: mode === t.k ? "rgba(96,165,250,0.14)" : "transparent",
                color: mode === t.k ? "#cfe1fb" : "var(--text-secondary)",
                cursor: "pointer", fontSize: 12.5, fontWeight: 500,
                boxShadow: mode === t.k ? "inset 0 0 0 1px rgba(96,165,250,0.30)" : "none",
                transition: "all .12s ease",
              }}
            >
              <Icon name={t.icon} size={13} />
              {t.label}
            </button>
          ))}
        </nav>
      )}

      {isMobile && (
        <button
          aria-label="menu"
          aria-expanded={mobileMenuOpen}
          onClick={() => setMobileMenuOpen((v) => !v)}
          className="dem-btn dem-btn-ghost dem-btn-icon"
          style={{ marginLeft: "auto" }}
        >
          <Icon name={mobileMenuOpen ? "close" : "menu"} size={16} />
        </button>
      )}

      {isMobile && mobileMenuOpen && (
        <>
          <div onClick={() => setMobileMenuOpen(false)} style={{ position: "fixed", inset: 0, zIndex: 90 }} />
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Navigation"
            className="dem-glass-2"
            style={{
              position: "fixed", top: 56, right: 12, left: 12, zIndex: 100,
              borderRadius: 12, padding: 14,
              display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6,
            }}
          >
            {TABS.map((t) => (
              <button
                key={t.k}
                onClick={() => { setMode(t.k); setMobileMenuOpen(false); }}
                style={{
                  display: "inline-flex", alignItems: "center", gap: 8,
                  padding: "12px 14px", borderRadius: 8, border: "none",
                  background: mode === t.k ? "rgba(96,165,250,0.14)" : "rgba(255,255,255,0.02)",
                  color: mode === t.k ? "#cfe1fb" : "var(--text-secondary)",
                  cursor: "pointer", fontSize: 13.5, fontWeight: 500,
                  boxShadow: mode === t.k ? "inset 0 0 0 1px rgba(96,165,250,0.30)" : "none",
                  textAlign: "left",
                }}
              >
                <Icon name={t.icon} size={16} />
                {t.label}
              </button>
            ))}
          </div>
        </>
      )}

      {!isMobile && (
        <button
          onClick={onCmdK}
          style={{
            flex: 1, maxWidth: 360, marginLeft: 12,
            display: "flex", alignItems: "center", gap: 8,
            padding: "6px 12px", borderRadius: 8,
            border: "1px solid var(--border-subtle)",
            background: "rgba(255,255,255,0.02)",
            color: "var(--text-tertiary)",
            cursor: "pointer", fontSize: 12.5,
            transition: "all .12s ease",
          }}
        >
          <Icon name="search" size={13} />
          <span>Rechercher conversations, cibles, dirigeants…</span>
          <span style={{ marginLeft: "auto", display: "flex", gap: 3 }}>
            <span className="kbd">⌘</span>
            <span className="kbd">K</span>
          </span>
        </button>
      )}

      <div style={{ marginLeft: isMobile ? 0 : "auto", display: "flex", gap: 6, alignItems: "center" }}>
        <button
          ref={bellRef}
          className="dem-btn dem-btn-ghost dem-btn-icon"
          title="Notifications"
          aria-label="Ouvrir les notifications"
          aria-expanded={notifOpen}
          onClick={() => setNotifOpen((v) => !v)}
          style={{ position: "relative" }}
        >
          <Icon name="bell" size={14} />
          <span style={{
            position: "absolute", top: 4, right: 4,
            width: 6, height: 6, borderRadius: 999,
            background: "var(--accent-rose)",
            boxShadow: "0 0 8px var(--accent-rose)",
          }} />
        </button>
        <NotifPanel open={notifOpen} onClose={() => setNotifOpen(false)} />
        <div style={{
          display: "flex", alignItems: "center", gap: 8,
          padding: "3px 10px 3px 4px", borderRadius: 999,
          border: "1px solid var(--border-subtle)",
          background: "rgba(255,255,255,0.02)",
        }}>
          <div style={{
            width: 22, height: 22, borderRadius: 999,
            background: "linear-gradient(135deg, #60a5fa, #a78bfa)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 10, fontWeight: 700, color: "#0a0a0d",
          }}>AD</div>
          <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>Anne Dupont</span>
        </div>
      </div>
    </header>
  );
}
