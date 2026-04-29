"use client";

import { useEffect, useState } from "react";
import { Icon } from "./Icon";
import { datalakeApi } from "@/lib/api";
import { fetchTargets } from "@/lib/dem/adapter";
import type { Target } from "@/lib/dem/types";

interface Node {
  id: string;
  label: string;
  type: "target" | "person" | "company" | "sci";
  x: number;
  y: number;
}

interface Link { source: string; target: string; kind: string }

const COLORS: Record<string, string> = {
  target: "var(--accent-blue)",
  person: "var(--accent-purple)",
  company: "var(--accent-cyan)",
  sci: "var(--accent-amber)",
};

interface Props {
  onOpenTarget?: (t: Target) => void;
}

export function NetworkGraphView({ onOpenTarget }: Props) {
  const [siren, setSiren] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [nodes, setNodes] = useState<Node[]>([]);
  const [links, setLinks] = useState<Link[]>([]);
  const [hover, setHover] = useState<Node | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [topCibles, setTopCibles] = useState<Target[]>([]);

  useEffect(() => {
    fetchTargets({ limit: 6 }).then(setTopCibles);
  }, []);

  const loadNetwork = (s: string) => {
    if (!s.match(/^\d{9}$/)) {
      setError("SIREN invalide (9 chiffres)");
      return;
    }
    setLoading(true);
    setError(null);
    datalakeApi
      .network(s)
      .then((r) => {
        setNodes(r.nodes);
        setLinks(r.links);
        setSiren(s);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  };

  const W = 900, H = 560;
  const cx = W / 2, cy = H / 2;

  return (
    <div style={{ flex: 1, display: "flex", overflow: "hidden", position: "relative", zIndex: 1 }}>
      <div style={{ flex: 1, position: "relative", overflow: "hidden", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{
          position: "absolute", inset: 0,
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }} />

        {/* Search bar */}
        <div style={{
          position: "absolute", top: 20, left: 20, right: 20, zIndex: 5,
          display: "flex", gap: 8, alignItems: "center",
        }}>
          <div className="dem-glass-2" style={{
            display: "flex", alignItems: "center", gap: 8,
            padding: "8px 12px", borderRadius: 10,
          }}>
            <Icon name="search" size={13} color="var(--text-tertiary)" />
            <input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") loadNetwork(searchInput); }}
              placeholder="SIREN (9 chiffres) pour explorer le réseau…"
              className="dem-mono"
              style={{
                background: "transparent", border: "none", outline: "none",
                color: "var(--text-primary)", fontSize: 13, width: 220,
              }}
            />
            <button className="dem-btn dem-btn-primary" onClick={() => loadNetwork(searchInput)}>
              Charger
            </button>
          </div>
          {error && (
            <span style={{ fontSize: 11, color: "var(--accent-rose)" }}>{error}</span>
          )}
          {loading && (
            <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>Chargement…</span>
          )}
        </div>

        {!siren && !loading ? (
          <div style={{ textAlign: "center", color: "var(--text-tertiary)", maxWidth: 480 }}>
            <Icon name="network" size={32} color="var(--text-muted)" />
            <div style={{ marginTop: 12, fontSize: 14, fontWeight: 600, color: "var(--text-secondary)" }}>
              Explore le réseau dirigeants × co-mandats × SCI patrimoine d&apos;une entreprise
            </div>
            <div style={{ marginTop: 6, fontSize: 12 }}>
              Tape un SIREN ou pick une cible :
            </div>
            <div style={{ marginTop: 14, display: "flex", flexWrap: "wrap", gap: 6, justifyContent: "center" }}>
              {topCibles.slice(0, 5).map((t) => (
                <button
                  key={t.siren}
                  className="dem-chip"
                  onClick={() => { setSearchInput(t.siren); loadNetwork(t.siren); }}
                >
                  <span className="dem-mono">{t.siren}</span> · {t.denomination.slice(0, 24)}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <svg width={W} height={H} style={{ position: "relative" }}>
            <defs>
              <radialGradient id="halo">
                <stop offset="0%" stopColor="rgba(96,165,250,0.6)" />
                <stop offset="100%" stopColor="rgba(96,165,250,0)" />
              </radialGradient>
            </defs>
            {links.map((l, i) => {
              const s = nodes.find((n) => n.id === l.source);
              const t = nodes.find((n) => n.id === l.target);
              if (!s || !t) return null;
              return (
                <line
                  key={i}
                  x1={cx + s.x} y1={cy + s.y}
                  x2={cx + t.x} y2={cy + t.y}
                  stroke="rgba(255,255,255,0.12)" strokeWidth="1"
                />
              );
            })}
            {nodes.map((n) => {
              const isTarget = n.type === "target";
              const r = isTarget ? 18 : n.type === "person" ? 14 : 11;
              return (
                <g
                  key={n.id}
                  transform={`translate(${cx + n.x}, ${cy + n.y})`}
                  style={{ cursor: "pointer" }}
                  onMouseEnter={() => setHover(n)}
                  onMouseLeave={() => setHover(null)}
                  onClick={async () => {
                    if (n.type === "company" || n.type === "target") {
                      const sirenMatch = n.id.match(/^c_(\d{9})/);
                      if (sirenMatch && onOpenTarget) {
                        const targets = await fetchTargets({ q: sirenMatch[1], limit: 1 });
                        if (targets[0]) onOpenTarget(targets[0]);
                      }
                    }
                  }}
                >
                  {isTarget && <circle r={r + 8} fill="url(#halo)" />}
                  <circle r={r} fill={COLORS[n.type]} fillOpacity="0.18" stroke={COLORS[n.type]} strokeWidth="1.5" />
                  <text textAnchor="middle" dy={r + 14} fontSize="10.5" fill="var(--text-secondary)" fontFamily="Inter">{n.label}</text>
                </g>
              );
            })}
          </svg>
        )}

        <div className="dem-glass" style={{
          position: "absolute", left: 20, bottom: 20,
          padding: "10px 14px", borderRadius: 10,
          display: "flex", gap: 14, fontSize: 11.5,
        }}>
          {Object.entries(COLORS).map(([k, c]) => (
            <span key={k} style={{ display: "inline-flex", alignItems: "center", gap: 5, color: "var(--text-secondary)" }}>
              <span style={{ width: 8, height: 8, borderRadius: 999, background: c, opacity: 0.7 }} />
              {k}
            </span>
          ))}
        </div>
      </div>

      <div style={{ width: 280, borderLeft: "1px solid var(--border-subtle)", padding: 18, background: "rgba(10,10,13,0.40)" }}>
        <div className="section-label" style={{ marginBottom: 8 }}>Focus</div>
        {hover ? (
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", letterSpacing: "-0.01em" }}>{hover.label}</div>
            <div style={{ marginTop: 4, fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.06em" }}>{hover.type}</div>
            <div style={{ marginTop: 14, fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.6 }}>
              {hover.type === "target" && "Cible centrale du réseau."}
              {hover.type === "person" && "Dirigeant — cliquez pour voir ses mandats."}
              {hover.type === "company" && "Co-mandat — cliquez pour ouvrir la fiche."}
              {hover.type === "sci" && "SCI patrimoine."}
            </div>
          </div>
        ) : (
          <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
            {siren ? "Survole un nœud pour voir le détail." : "Charge un SIREN pour démarrer."}
          </div>
        )}
        {siren && (
          <div style={{ marginTop: 24 }}>
            <div className="section-label" style={{ marginBottom: 8 }}>Stats du graphe</div>
            {[
              ["Nœuds", nodes.length],
              ["Liens", links.length],
              ["Cibles", nodes.filter((n) => n.type === "target").length],
              ["Dirigeants", nodes.filter((n) => n.type === "person").length],
              ["Co-entreprises", nodes.filter((n) => n.type === "company").length],
              ["SCI patrimoine", nodes.filter((n) => n.type === "sci").length],
            ].map(([l, v]) => (
              <div key={l as string} style={{
                display: "flex", justifyContent: "space-between", padding: "4px 0",
                fontSize: 12, color: "var(--text-secondary)",
              }}>
                <span>{l}</span>
                <span className="dem-mono tab-num" style={{ color: "var(--text-primary)", fontWeight: 600 }}>{v}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
