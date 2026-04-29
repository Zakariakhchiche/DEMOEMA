"use client";

import { useState, useEffect } from "react";
import { Icon } from "./Icon";
import { CONVERSATIONS, SLASH_COMMANDS } from "@/lib/dem/data";

interface Item {
  icon: string;
  label: string;
  sub: string;
  action: () => void;
}

interface Props {
  onClose: () => void;
  onCommand: (text: string) => void;
}

export function CmdPalette({ onClose, onCommand }: Props) {
  const [q, setQ] = useState("");
  const items: Item[] = [
    ...SLASH_COMMANDS.map((c) => ({
      icon: "chat",
      label: c.cmd,
      sub: c.desc,
      action: () => onCommand(c.example),
    })),
    ...CONVERSATIONS.slice(0, 4).map((c) => ({
      icon: "history",
      label: c.title,
      sub: c.time,
      action: () => onClose(),
    })),
  ];
  const filtered = q
    ? items.filter((i) => i.label.toLowerCase().includes(q.toLowerCase()) || i.sub.toLowerCase().includes(q.toLowerCase()))
    : items;

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <>
      <div className="sheet-backdrop" onClick={onClose} style={{ background: "rgba(0,0,0,0.5)" }} />
      <div style={{ position: "fixed", top: "20%", left: "50%", transform: "translateX(-50%)", width: 580, zIndex: 100 }}>
        <div className="dem-glass-2" style={{ borderRadius: 14, overflow: "hidden", boxShadow: "0 24px 60px -10px rgba(0,0,0,0.7)" }}>
          <div style={{
            padding: "14px 18px",
            display: "flex", alignItems: "center", gap: 10,
            borderBottom: "1px solid var(--border-subtle)",
          }}>
            <Icon name="search" size={14} color="var(--text-tertiary)" />
            <input
              autoFocus
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Cherche conversations, cibles, dirigeants, commandes…"
              style={{
                flex: 1, background: "transparent", border: "none", outline: "none",
                color: "var(--text-primary)", fontSize: 14, fontFamily: "inherit",
              }}
            />
            <span className="kbd">esc</span>
          </div>
          <div style={{ maxHeight: 400, overflowY: "auto", padding: 6 }}>
            {filtered.map((it, i) => (
              <button
                key={i}
                onClick={() => { it.action(); onClose(); }}
                style={{
                  width: "100%", display: "flex",
                  alignItems: "center", gap: 12,
                  padding: "9px 12px", borderRadius: 8, border: "none",
                  background: i === 0 ? "rgba(96,165,250,0.10)" : "transparent",
                  color: "var(--text-primary)", cursor: "pointer",
                  fontSize: 13, textAlign: "left",
                }}
              >
                <Icon name={it.icon} size={13} color="var(--text-tertiary)" />
                <span style={{ fontWeight: 500 }}>{it.label}</span>
                <span style={{ marginLeft: "auto", fontSize: 11, color: "var(--text-tertiary)" }}>{it.sub}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
