"use client";

import { useState, useEffect, useRef } from "react";
import { Icon } from "./Icon";
import { SLASH_COMMANDS } from "@/lib/dem/data";

interface Props {
  onSubmit: (text: string) => void;
  suggestions?: string[] | null;
  isStreaming?: boolean;
}

export function ChatInput({ onSubmit, suggestions, isStreaming }: Props) {
  const [val, setVal] = useState("");
  const [showSlash, setShowSlash] = useState(false);
  const ref = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setShowSlash(val.startsWith("/") && val.length < 20);
  }, [val]);

  const submit = () => {
    if (val.trim() && !isStreaming) {
      onSubmit(val.trim());
      setVal("");
    }
  };

  return (
    <div style={{ position: "relative", margin: "0 auto", maxWidth: 860, width: "100%" }}>
      {showSlash && (
        <div className="dem-glass-2" style={{
          position: "absolute", bottom: "calc(100% + 6px)", left: 0, right: 0,
          borderRadius: 12, padding: 6,
          boxShadow: "0 16px 48px -8px rgba(0,0,0,0.6)", zIndex: 20,
        }}>
          <div style={{
            padding: "6px 10px", fontSize: 10.5,
            color: "var(--text-tertiary)",
            textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 600,
          }}>Commandes</div>
          {SLASH_COMMANDS.map((c) => (
            <div
              key={c.cmd}
              onClick={() => { setVal(c.example + " "); setShowSlash(false); ref.current?.focus(); }}
              style={{
                display: "flex", alignItems: "center", gap: 10,
                padding: "8px 10px", borderRadius: 7,
                cursor: "pointer", fontSize: 12.5,
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.04)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
            >
              <span className="dem-mono" style={{ color: "var(--accent-purple)", fontWeight: 600, minWidth: 80 }}>{c.cmd}</span>
              <span style={{ color: "var(--text-secondary)" }}>{c.desc}</span>
              <span className="dem-mono" style={{ marginLeft: "auto", color: "var(--text-muted)", fontSize: 11 }}>{c.example}</span>
            </div>
          ))}
        </div>
      )}

      {suggestions && suggestions.length > 0 && !val && (
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 10, justifyContent: "center" }}>
          {suggestions.map((s, i) => (
            <button key={i} className="dem-chip" onClick={() => onSubmit(s)}>
              <Icon name="sparkles" size={10} color="var(--accent-purple)" />
              {s}
            </button>
          ))}
        </div>
      )}

      <div className="dem-glass-2" style={{
        borderRadius: 14, padding: "10px 12px 10px 14px",
        display: "flex", alignItems: "center", gap: 10,
        boxShadow: "0 4px 30px -8px rgba(0,0,0,0.40)",
      }}>
        <Icon name="chat" size={14} color="var(--text-tertiary)" />
        <input
          ref={ref}
          value={val}
          onChange={(e) => setVal(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
          placeholder="Pose ta question ou tape / pour les commandes…"
          style={{
            flex: 1, background: "transparent", border: "none", outline: "none",
            color: "var(--text-primary)", fontSize: 14, fontFamily: "inherit",
          }}
        />
        <button className="dem-btn dem-btn-ghost dem-btn-icon" title="Joindre fichier">
          <Icon name="paperclip" size={13} />
        </button>
        <button className="dem-btn dem-btn-ghost" title="Filtres">
          <Icon name="filter" size={12} /> Filtres
        </button>
        <button
          className="dem-btn dem-btn-primary"
          disabled={!val.trim() || isStreaming}
          style={{ opacity: val.trim() && !isStreaming ? 1 : 0.5 }}
          onClick={submit}
        >
          <Icon name="send" size={12} /> Send
          <span className="kbd" style={{ marginLeft: 4 }}>↵</span>
        </button>
      </div>

      <div style={{
        display: "flex", gap: 6, marginTop: 8, fontSize: 11, color: "var(--text-tertiary)",
        justifyContent: "center", alignItems: "center",
      }}>
        <span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
          <Icon name="pin" size={10} color="var(--accent-purple)" />
          <span>Épinglés:</span>
        </span>
        <button className="dem-chip" onClick={() => onSubmit("DD compliance Acme Industries")}>
          <Icon name="shield" size={10} /> DD compliance
        </button>
        <button className="dem-chip" onClick={() => onSubmit("Sourcing IDF chimie >20M€")}>
          <Icon name="search" size={10} /> Sourcing IDF chimie
        </button>
        <button className="dem-chip" onClick={() => onSubmit("Compare Beta et Gamma")}>
          <Icon name="layers" size={10} /> Compare cibles
        </button>
      </div>
    </div>
  );
}
