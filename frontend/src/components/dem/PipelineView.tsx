"use client";

import { useEffect, useState } from "react";
import { Icon } from "./Icon";
import { ScoreBadge } from "./ScoreBadge";
import { datalakeApi } from "@/lib/api";
import { fetchTargets } from "@/lib/dem/adapter";
import type { Target } from "@/lib/dem/types";

interface Props {
  onOpenTarget: (t: Target) => void;
}

interface Deal {
  id: string;
  siren: string;
  name: string;
  stage: string;
  value: string;
  value_num: number;
  owner: string;
  days: number;
  score: number;
  side: "buy-side" | "sell-side";
  next: string;
  urgent: boolean;
}

interface Stage {
  id: string;
  label: string;
  color: string;
}

export function PipelineView({ onOpenTarget }: Props) {
  const [stages, setStages] = useState<Stage[]>([]);
  const [deals, setDeals] = useState<Deal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dragId, setDragId] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    datalakeApi
      .pipeline()
      .then((r) => {
        setStages(r.stages);
        setDeals(r.deals);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, []);

  const onDrop = (stage: string) => {
    if (!dragId) return;
    setDeals(deals.map((d) => (d.id === dragId ? { ...d, stage } : d)));
    setDragId(null);
    setDragOver(null);
  };

  const sumByStage = (st: string) => {
    const ds = deals.filter((d) => d.stage === st);
    const total = ds.reduce((s, d) => s + d.value_num, 0);
    return { count: ds.length, total: (total / 1e6).toFixed(0) };
  };

  const totalSum = (deals.reduce((s, d) => s + d.value_num, 0) / 1e6).toFixed(0);

  const openDeal = async (d: Deal) => {
    const targets = await fetchTargets({ q: d.siren, limit: 1 });
    if (targets[0]) onOpenTarget(targets[0]);
  };

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", position: "relative", zIndex: 1 }}>
      <div style={{ padding: "16px 22px 12px", borderBottom: "1px solid var(--border-subtle)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ fontSize: 16, fontWeight: 700, letterSpacing: "-0.01em" }}>Pipeline M&A</div>
          <span className="dem-mono" style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
            · {deals.length} cibles · {totalSum} M€ pipeline · datalake live
          </span>
          <span style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
            <button className="dem-btn"><Icon name="user" size={11} /> Tous</button>
            <button className="dem-btn dem-btn-primary"><Icon name="plus" size={11} /> Nouveau deal</button>
          </span>
        </div>
        <div style={{ marginTop: 10, fontSize: 12, color: "var(--text-tertiary)" }}>
          <Icon name="sparkles" size={11} color="var(--accent-purple)" /> Stages dérivés du CA INPI live · drag &amp; drop pour faire avancer · urgences = compliance red flag
        </div>
        {error && (
          <div style={{
            marginTop: 10, padding: "8px 12px", borderRadius: 8,
            background: "rgba(251,113,133,0.06)", border: "1px solid rgba(251,113,133,0.20)",
            color: "var(--accent-rose)", fontSize: 12,
          }}>
            <Icon name="warning" size={11} /> {error}
          </div>
        )}
      </div>

      <div style={{ flex: 1, overflowX: "auto", padding: 16 }}>
        {loading ? (
          <div style={{ padding: 32, textAlign: "center", color: "var(--text-tertiary)" }}>Chargement live…</div>
        ) : (
          <div style={{
            display: "grid",
            gridTemplateColumns: `repeat(${stages.length}, minmax(240px, 1fr))`,
            gap: 12, height: "100%", minWidth: 1200,
          }}>
            {stages.map((stage) => {
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
                      </div>
                    ))}
                    {stageDeals.length === 0 && (
                      <div style={{
                        padding: "20px 10px", textAlign: "center",
                        fontSize: 11, color: "var(--text-muted)",
                        border: "1px dashed var(--border-subtle)", borderRadius: 8,
                      }}>
                        Aucune cible à ce stage
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
