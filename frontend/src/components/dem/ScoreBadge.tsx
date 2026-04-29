"use client";

import { useState, useRef } from "react";

interface Props {
  value: number;
  size?: "sm" | "md" | "lg";
  breakdown?: { label: string; value: number }[];
}

export function ScoreBadge({ value, size = "md", breakdown }: Props) {
  const tone = value >= 70 ? "high" : value >= 50 ? "mid" : "low";
  const dim = size === "lg" ? 56 : size === "sm" ? 26 : 36;
  const fs = size === "lg" ? 22 : size === "sm" ? 12 : 15;
  const [show, setShow] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const dotColor =
    tone === "high" ? "var(--accent-emerald)" :
    tone === "mid" ? "var(--accent-amber)" :
    "var(--accent-rose)";

  return (
    <div
      ref={ref}
      style={{ position: "relative", display: "inline-flex", alignItems: "center", gap: 6 }}
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      <div className={`score-halo ${tone}`} style={{ width: dim, height: dim, fontSize: fs }}>
        {value}
      </div>
      <span style={{ width: 6, height: 6, borderRadius: 999, background: dotColor, boxShadow: `0 0 8px ${dotColor}` }} />
      {show && breakdown && breakdown.length > 0 && (
        <div className="dem-tooltip" style={{ top: dim + 8, left: 0 }}>
          <div style={{ fontWeight: 600, marginBottom: 6, color: "var(--text-primary)", fontSize: 12 }}>
            Score {value} / 100
          </div>
          {breakdown.map((b, i) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "2px 0", color: "var(--text-secondary)" }}>
              <span style={{ opacity: 0.85 }}>{b.label}</span>
              <span
                className="dem-mono"
                style={{
                  color: b.value > 0 ? "var(--accent-emerald)" : "var(--accent-rose)",
                  fontWeight: 600,
                }}
              >
                {b.value > 0 ? "+" : ""}
                {b.value}
              </span>
            </div>
          ))}
          <div style={{ borderTop: "1px solid var(--border-subtle)", marginTop: 6, paddingTop: 6, display: "flex", justifyContent: "space-between" }}>
            <span style={{ color: "var(--text-tertiary)" }}>Total</span>
            <span className="dem-mono" style={{ color: "var(--text-primary)", fontWeight: 700 }}>{value} / 100</span>
          </div>
        </div>
      )}
    </div>
  );
}
