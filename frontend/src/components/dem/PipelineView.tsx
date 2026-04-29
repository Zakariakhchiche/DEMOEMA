"use client";

import { useState } from "react";
import { Icon } from "./Icon";
import { ScoreBadge } from "./ScoreBadge";
import { PIPELINE_STAGES, PIPELINE_DEALS } from "@/lib/dem/data";
import type { PipelineDeal, Target } from "@/lib/dem/types";
import { fetchTargets } from "@/lib/dem/adapter";

interface Props {
  onOpenTarget: (t: Target) => void;
}

export function PipelineView({ onOpenTarget }: Props) {
  const [deals, setDeals] = useState<PipelineDeal[]>(PIPELINE_DEALS);
  const [dragId, setDragId] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState<string | null>(null);

  const onDrop = (stage: string) => {
    if (!dragId) return;
    setDeals(deals.map((d) => (d.id === dragId ? { ...d, stage } : d)));
    setDragId(null);
    setDragOver(null);
  };

  const sumByStage = (st: string) => {
    const ds = deals.filter((d) => d.stage === st);
    const total = ds.reduce((s, d) => s + parseFloat(d.value), 0);
    return { count: ds.length, total: total.toFixed(0) };
  };

  const openDeal = async (d: PipelineDeal) => {
    const targets = await fetchTargets({ q: d.siren, limit: 1 });
    if (targets[0]) onOpenTarget(targets[0]);
  };

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", position: "relative", zIndex: 1 }}>
      <div style={{ padding: "16px 22px 12px", borderBottom: "1px solid var(--border-subtle)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ fontSize: 16, fontWeight: 700, letterSpacing: "-0.01em" }}>Pipeline M&A</div>
          <span className="dem-mono" style={{ fontSize: 11, color: "var(--text-tertiary)" }}>· {deals.length} deals · 612 M€</span>
          <span style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
            <button className="dem-btn"><Icon name="user" size={11} /> Tous</button>
            <button className="dem-btn dem-btn-primary"><Icon name="plus" size={11} /> Nouveau deal</button>
          </span>
        </div>
        <div style={{ marginTop: 10, fontSize: 12, color: "var(--text-tertiary)" }}>
          <Icon name="sparkles" size={11} color="var(--accent-purple)" /> Drag &amp; drop pour avancer une affaire · les urgences apparaissent en rouge
        </div>
      </div>

      <div style={{ flex: 1, overflowX: "auto", padding: 16 }}>
        <div style={{
          display: "grid",
          gridTemplateColumns: `repeat(${PIPELINE_STAGES.length}, minmax(240px, 1fr))`,
          gap: 12, height: "100%", minWidth: 1200,
        }}>
          {PIPELINE_STAGES.map((stage) => {
            const stageDeals = deals.filter((d) => d.stage === stage.id);
            const sum = sumByStage(stage.id);
            const isOver = dragOver === stage.id;
            return (
              <div
                key={stage.id}
                className="pipe-col"
                style={{
                  borderColor: isOver ? stage.color : undefined,
                  background: isOver ? "rgba(96,165,250,0.04)" : undefined,
                }}
                onDragOver={(e) => { e.preventDefault(); setDragOver(stage.id); }}
                onDragLeave={() => setDragOver(null)}
                onDrop={() => onDrop(stage.id)}
              >
                <div style={{ padding: "12px 14px", borderBottom: "1px solid var(--border-subtle)" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ width: 8, height: 8, borderRadius: 999, background: stage.color }} />
                    <span style={{ fontSize: 12.5, fontWeight: 600 }}>{stage.label}</span>
                    <span className="dem-mono" style={{ marginLeft: "auto", fontSize: 11, color: "var(--text-tertiary)" }}>{sum.count}</span>
                  </div>
                  <div className="dem-mono tab-num" style={{ marginTop: 4, fontSize: 11, color: "var(--text-tertiary)" }}>Σ {sum.total} M€</div>
                </div>
                <div style={{ flex: 1, overflowY: "auto", padding: 10, display: "flex", flexDirection: "column", gap: 8 }}>
                  {stageDeals.map((d) => (
                    <div
                      key={d.id}
                      className={`pipe-card ${d.urgent ? "urgent" : ""}`}
                      draggable
                      onDragStart={() => setDragId(d.id)}
                      onClick={() => openDeal(d)}
                    >
                      <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{d.name}</div>
                          <div className="dem-mono" style={{ fontSize: 10.5, color: "var(--text-tertiary)", marginTop: 2 }}>siren {d.siren}</div>
                        </div>
                        <ScoreBadge value={d.score} size="sm" />
                      </div>
                      <div style={{ marginTop: 10, display: "flex", justifyContent: "space-between", fontSize: 11.5 }}>
                        <span className="dem-mono tab-num" style={{ color: "var(--text-primary)", fontWeight: 600 }}>{d.value}</span>
                        <span className={`dem-chip ${d.side === "sell-side" ? "dem-chip-active" : ""}`} style={{ padding: "1px 7px", fontSize: 10 }}>{d.side}</span>
                      </div>
                      <div style={{
                        marginTop: 8, paddingTop: 8,
                        borderTop: "1px solid var(--border-subtle)",
                        display: "flex", alignItems: "center", gap: 6,
                        fontSize: 11,
                        color: d.urgent ? "var(--accent-rose)" : "var(--text-secondary)",
                      }}>
                        {d.urgent && <Icon name="warning" size={10} />}
                        <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{d.next}</span>
                      </div>
                      <div style={{ marginTop: 6, display: "flex", justifyContent: "space-between", fontSize: 10.5, color: "var(--text-muted)" }}>
                        <span>{d.owner} · {d.days}j</span>
                      </div>
                    </div>
                  ))}
                  {stageDeals.length === 0 && (
                    <div style={{
                      padding: "20px 10px", textAlign: "center",
                      fontSize: 11, color: "var(--text-muted)",
                      border: "1px dashed var(--border-subtle)", borderRadius: 8,
                    }}>
                      Glissez un deal ici
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
