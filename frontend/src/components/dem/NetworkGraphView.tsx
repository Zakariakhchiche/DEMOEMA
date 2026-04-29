"use client";

import { useState } from "react";
import { NETWORK_NODES, NETWORK_LINKS } from "@/lib/dem/data";
import type { NetworkNode } from "@/lib/dem/types";

const COLORS: Record<string, string> = {
  target: "var(--accent-blue)",
  person: "var(--accent-purple)",
  company: "var(--accent-cyan)",
  sci: "var(--accent-amber)",
};

export function NetworkGraphView() {
  const [hover, setHover] = useState<NetworkNode | null>(null);
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
        <svg width={W} height={H} style={{ position: "relative" }}>
          <defs>
            <radialGradient id="halo">
              <stop offset="0%" stopColor="rgba(96,165,250,0.6)" />
              <stop offset="100%" stopColor="rgba(96,165,250,0)" />
            </radialGradient>
          </defs>
          {NETWORK_LINKS.map((l, i) => {
            const s = NETWORK_NODES.find((n) => n.id === l.source);
            const t = NETWORK_NODES.find((n) => n.id === l.target);
            if (!s || !t) return null;
            return (
              <line
                key={i}
                x1={cx + s.x} y1={cy + s.y}
                x2={cx + t.x} y2={cy + t.y}
                stroke="rgba(255,255,255,0.12)"
                strokeWidth="1"
              />
            );
          })}
          {NETWORK_NODES.map((n) => {
            const isTarget = n.type === "target";
            const r = isTarget ? 18 : n.type === "person" ? 14 : 11;
            return (
              <g
                key={n.id}
                transform={`translate(${cx + n.x}, ${cy + n.y})`}
                style={{ cursor: "pointer" }}
                onMouseEnter={() => setHover(n)}
                onMouseLeave={() => setHover(null)}
              >
                {isTarget && <circle r={r + 8} fill="url(#halo)" />}
                <circle r={r} fill={COLORS[n.type]} fillOpacity="0.18" stroke={COLORS[n.type]} strokeWidth="1.5" />
                <text textAnchor="middle" dy={r + 14} fontSize="11" fill="var(--text-secondary)" fontFamily="Inter">{n.label}</text>
              </g>
            );
          })}
        </svg>
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
        <div className="dem-glass" style={{
          position: "absolute", right: 20, bottom: 20,
          padding: "10px 14px", borderRadius: 10,
          fontSize: 11, color: "var(--text-tertiary)",
        }}>
          <span className="kbd">↑↓←→</span> pan · <span className="kbd">+/-</span> zoom · <span className="kbd">click</span> focus
        </div>
      </div>
      <div style={{ width: 280, borderLeft: "1px solid var(--border-subtle)", padding: 18, background: "rgba(10,10,13,0.40)" }}>
        <div className="section-label" style={{ marginBottom: 8 }}>Focus</div>
        {hover ? (
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", letterSpacing: "-0.01em" }}>{hover.label}</div>
            <div style={{ marginTop: 4, fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.06em" }}>{hover.type}</div>
            <div style={{ marginTop: 14, fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.6 }}>
              {hover.type === "target" && "Cible M&A active. Cliquez pour ouvrir la fiche détaillée."}
              {hover.type === "person" && "Dirigeant — cliquez pour voir ses mandats et SCI rattachées."}
              {hover.type === "company" && "Société liée (filiale, holding, ex-mandat)."}
              {hover.type === "sci" && "Patrimoine immobilier via SCI."}
            </div>
          </div>
        ) : (
          <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Survolez un nœud pour voir le détail.</div>
        )}
        <div style={{ marginTop: 24 }}>
          <div className="section-label" style={{ marginBottom: 8 }}>Stats du graphe</div>
          {[
            ["Nœuds", NETWORK_NODES.length],
            ["Liens", NETWORK_LINKS.length],
            ["Cibles", NETWORK_NODES.filter((n) => n.type === "target").length],
            ["Dirigeants", NETWORK_NODES.filter((n) => n.type === "person").length],
            ["SCI patrimoine", NETWORK_NODES.filter((n) => n.type === "sci").length],
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
      </div>
    </div>
  );
}
