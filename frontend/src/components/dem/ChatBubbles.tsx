"use client";

import type React from "react";

export function UserMessage({ content }: { content: string }) {
  return (
    <div className="fade-up" style={{ display: "flex", justifyContent: "flex-end", margin: "20px 0" }}>
      <div style={{
        maxWidth: "70%",
        maxHeight: 280,
        overflowY: "auto",
        padding: "10px 16px",
        borderRadius: 16,
        borderTopRightRadius: 4,
        background: "linear-gradient(135deg, rgba(96,165,250,0.18), rgba(167,139,250,0.18))",
        border: "1px solid rgba(96,165,250,0.30)",
        color: "var(--text-primary)",
        fontSize: 14,
        lineHeight: 1.5,
        wordBreak: "break-word",
        overflowWrap: "anywhere",
        whiteSpace: "pre-wrap",
      }}>
        {content}
      </div>
    </div>
  );
}

export function AiMessage({ children, streaming, header }: { children: React.ReactNode; streaming?: boolean; header?: string }) {
  return (
    <div className="fade-up" style={{ display: "flex", gap: 12, margin: "20px 0", alignItems: "flex-start" }}>
      <div className={`ai-orbe ${streaming ? "pulse" : ""}`} style={{ marginTop: 2 }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        {header && (
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, fontSize: 11.5, color: "var(--text-tertiary)" }}>
            <span style={{ fontWeight: 600, color: "var(--accent-purple)" }}>DEMOEMA</span>
            <span>·</span>
            <span>{header}</span>
          </div>
        )}
        {children}
      </div>
    </div>
  );
}
