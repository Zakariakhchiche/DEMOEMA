"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { Icon } from "./Icon";
import { ScoreBadge } from "./ScoreBadge";
import { datalakeApi, type TableInfo } from "@/lib/api";
import type { Target } from "@/lib/dem/types";
import { rowToTarget } from "@/lib/dem/adapter";
import { parseNumericLoose, formatEurCompact, formatCompactNumber } from "@/lib/dem/format";

// Audit QA 2026-05-01 (SCRUM-NEW-14) : la table Explorer affichait des CA en
// notation scientifique illisible (`2.66540E+9`, `9.9000E+8`) car formatCell ne
// gérait pas les strings numériques. Heuristique : nom de colonne CA/EBITDA/
// capital → formatEurCompact (Md€/M€/K€), sinon formatCompactNumber.
const EUR_COL_RE = /^(ca|ebitda|chiffre|resultat|résultat|capital|montant|valeur|prix|actif|passif|dettes?)/i;
const EUR_COL_SUFFIX_RE = /_(ca|eur|euro|amount|price|value)$/i;
function isMonetaryColumn(col: string): boolean {
  return EUR_COL_RE.test(col) || EUR_COL_SUFFIX_RE.test(col);
}

interface Props {
  onOpenTarget: (t: Target) => void;
}

interface TableRows {
  table: string;
  columns: string[];
  rows: Record<string, unknown>[];
  hasMore: boolean;
  offset: number;
}

const PRIORITY_ORDER = [
  "gold.cibles_ma_top",
  "gold.entreprises_master",
  "gold.dirigeants_master",
  "silver.inpi_comptes",
  "silver.inpi_dirigeants",
  "silver.bodacc_annonces",
  "silver.opensanctions",
  "silver.press_mentions_matched",
];

function formatCell(v: unknown, col?: string): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? "✓" : "✗";

  // Strings numériques (Postgres `numeric` remonté en text → notation
  // scientifique `2.66540E+9` côté JSON) sont parsées et formatées comme les
  // numbers natifs.
  if (typeof v === "number" || (typeof v === "string" && parseNumericLoose(v) !== null)) {
    if (col && isMonetaryColumn(col)) {
      return formatEurCompact(v);
    }
    return formatCompactNumber(v);
  }

  if (typeof v === "object") {
    try { return JSON.stringify(v).slice(0, 60); } catch { return "[obj]"; }
  }
  const s = String(v);
  if (/^\d{4}-\d{2}-\d{2}T?/.test(s)) {
    const d = new Date(s);
    if (!isNaN(d.getTime())) return d.toLocaleDateString("fr-FR");
  }
  return s.length > 60 ? s.slice(0, 60) + "…" : s;
}

export function DataExplorerView({ onOpenTarget }: Props) {
  const [tables, setTables] = useState<TableInfo[]>([]);
  const [active, setActive] = useState<string>("");
  const [data, setData] = useState<TableRows | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());

  // Charger la liste des tables au mount
  useEffect(() => {
    datalakeApi
      .listTables()
      .then((r) => {
        setTables(r.tables);
        if (r.tables.length > 0 && !active) {
          // Préfère gold > silver
          const ordered = [...r.tables].sort((a, b) => {
            const ai = PRIORITY_ORDER.indexOf(a.name);
            const bi = PRIORITY_ORDER.indexOf(b.name);
            return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi);
          });
          setActive(ordered[0].name);
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadTable = useCallback(
    async (name: string, opts: { offset?: number; q?: string } = {}) => {
      const [schema, table] = name.split(".");
      if (!schema || !table) return;
      setLoading(true);
      setError(null);
      try {
        const r = await datalakeApi.queryTable(schema, table, {
          limit: 100,
          offset: opts.offset ?? 0,
          q: opts.q,
        });
        setData({
          table: r.table,
          columns: r.columns,
          rows: r.rows,
          hasMore: r.has_more,
          offset: r.offset,
        });
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
        setData(null);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    if (active) loadTable(active, { q: search });
  }, [active, search, loadTable]);

  const grouped = useMemo(() => {
    const out: Record<string, TableInfo[]> = {};
    tables.forEach((t) => {
      const layer = t.name.startsWith("gold.") ? "gold" : t.name.startsWith("silver.") ? "silver" : "bronze";
      (out[layer] ||= []).push(t);
    });
    return out;
  }, [tables]);

  const toggleSel = (s: string) => {
    const n = new Set(selected);
    if (n.has(s)) n.delete(s);
    else n.add(s);
    setSelected(n);
  };

  const handleRowClick = (row: Record<string, unknown>) => {
    if (typeof row.siren === "string" && row.siren.length === 9) {
      onOpenTarget(rowToTarget(row));
    }
  };

  return (
    <div style={{ display: "flex", flex: 1, overflow: "hidden", position: "relative", zIndex: 1 }}>
      {/* Schema sidebar */}
      <div style={{
        width: 264, borderRight: "1px solid var(--border-subtle)",
        padding: "12px 8px", overflowY: "auto", flexShrink: 0,
        background: "rgba(10,10,13,0.40)",
      }}>
        {(["gold", "silver", "bronze"] as const).map((layer) => {
          const items = grouped[layer] ?? [];
          if (!items.length) return null;
          const tone =
            layer === "gold" ? "var(--accent-amber)" :
            layer === "silver" ? "var(--text-secondary)" :
            "var(--text-tertiary)";
          return (
            <div key={layer} style={{ marginBottom: 12 }}>
              <div className="section-label" style={{ padding: "10px 10px 6px", color: tone }}>
                {layer === "gold" ? "★ Gold" : layer === "silver" ? "Silver" : "Bronze"} · {items.length} tables
              </div>
              {items.map((t) => (
                <button
                  key={t.name}
                  onClick={() => setActive(t.name)}
                  style={{
                    display: "flex", justifyContent: "space-between", width: "100%",
                    padding: "5px 10px", borderRadius: 6, border: "none",
                    background: active === t.name ? `rgba(96,165,250,0.10)` : "transparent",
                    color: active === t.name ? "#cfe1fb" : "var(--text-secondary)",
                    cursor: "pointer", fontSize: 12, textAlign: "left",
                  }}
                >
                  <span className="dem-mono">{layer === "gold" && "★ "}{t.name.split(".")[1] ?? t.name}</span>
                  <span className="dem-mono" style={{ fontSize: 10.5, color: "var(--text-muted)" }}>
                    {t.row_count_approx ? formatCell(t.row_count_approx) : "—"}
                  </span>
                </button>
              ))}
            </div>
          );
        })}
      </div>

      {/* Main table area */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", minWidth: 0 }}>
        <div style={{ padding: "14px 22px 10px", borderBottom: "1px solid var(--border-subtle)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <h1 style={{ margin: 0, fontSize: 16, fontWeight: 700, letterSpacing: "-0.01em" }}>
              {active ? (
                <>
                  <span style={{
                    color: active.startsWith("gold.") ? "var(--accent-amber)" :
                          active.startsWith("silver.") ? "var(--text-secondary)" : "var(--text-tertiary)",
                  }}>
                    {active.split(".")[0]}.
                  </span>
                  {active.split(".")[1]}
                </>
              ) : "Explorer datalake"}
            </h1>
            {data && (
              <span className="dem-mono" style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                · {data.rows.length} rows{data.hasMore ? "+" : ""}
              </span>
            )}
            <span style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
              <button className="dem-btn" onClick={() => loadTable(active, { q: search })} disabled={loading}>
                <Icon name="refresh" size={12} /> {loading ? "…" : "Rafraîchir"}
              </button>
              <button className="dem-btn">
                <Icon name="download" size={12} /> CSV
              </button>
            </span>
          </div>
          <div style={{ marginTop: 10, display: "flex", gap: 8, alignItems: "center" }}>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={`Rechercher dans ${active.split(".")[1] ?? "…"}…`}
              style={{
                flex: 1, padding: "6px 10px",
                background: "rgba(255,255,255,0.02)",
                border: "1px solid var(--border-subtle)",
                borderRadius: 8, fontSize: 12,
                color: "var(--text-primary)", outline: "none",
              }}
            />
            {selected.size > 0 && (
              <span style={{ fontSize: 11.5, color: "var(--accent-blue)", fontWeight: 600 }}>
                {selected.size} sélectionnée{selected.size > 1 ? "s" : ""}
              </span>
            )}
          </div>
        </div>

        {error && (
          <div style={{
            margin: "10px 22px", padding: "8px 12px",
            borderRadius: 8, background: "rgba(251,113,133,0.06)",
            border: "1px solid rgba(251,113,133,0.20)",
            color: "var(--accent-rose)", fontSize: 12,
          }}>
            <Icon name="warning" size={11} /> {error}
          </div>
        )}

        <div style={{ flex: 1, overflow: "auto" }}>
          {!data && loading && (
            <div style={{ padding: 32, textAlign: "center", color: "var(--text-tertiary)", fontSize: 12 }}>
              Chargement de {active}…
            </div>
          )}
          {data && data.rows.length === 0 && (
            <div style={{ padding: 32, textAlign: "center", color: "var(--text-tertiary)", fontSize: 12 }}>
              Aucune ligne pour cette table / recherche.
            </div>
          )}
          {data && data.rows.length > 0 && (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
              <thead>
                <tr style={{
                  position: "sticky", top: 0, zIndex: 5,
                  background: "rgba(10,10,13,0.95)", backdropFilter: "blur(10px)",
                }}>
                  <th style={{ width: 36, padding: "10px 0 10px 22px", textAlign: "left" }}></th>
                  {data.columns.map((c) => (
                    <th
                      key={c}
                      style={{
                        padding: "10px 12px", textAlign: "left", fontSize: 10.5,
                        color: "var(--text-tertiary)", fontWeight: 600,
                        textTransform: "uppercase", letterSpacing: "0.06em",
                        borderBottom: "1px solid var(--border-subtle)",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.rows.map((r, i) => {
                  const id = (r.siren as string) || (r.lei as string) || String(i);
                  return (
                    <tr
                      key={id + i}
                      className={`selectable ${selected.has(id) ? "selected" : ""}`}
                      style={{
                        borderBottom: "1px solid var(--border-subtle)",
                        cursor: "pointer", height: 36,
                      }}
                      onClick={() => handleRowClick(r)}
                    >
                      <td style={{ padding: "0 0 0 22px" }}>
                        <button
                          onClick={(e) => { e.stopPropagation(); toggleSel(id); }}
                          style={{
                            width: 14, height: 14, borderRadius: 3,
                            border: `1.5px solid ${selected.has(id) ? "var(--accent-blue)" : "var(--border-mid)"}`,
                            background: selected.has(id) ? "var(--accent-blue)" : "transparent",
                            cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
                          }}
                        >
                          {selected.has(id) && <Icon name="check" size={9} color="#0a0a0d" strokeWidth={3} />}
                        </button>
                      </td>
                      {data.columns.map((c) => {
                        const v = r[c];
                        const isMono = c === "siren" || c === "lei" || c === "naf" || c === "code_ape" || c === "dept" || c === "ca_net" || c === "resultat_net" || c === "ca_dernier";
                        const isScore = c === "score_ma" || c === "pro_ma_score" || c === "score";
                        return (
                          <td
                            key={c}
                            className={isMono ? "dem-mono tab-num" : ""}
                            style={{
                              padding: "0 12px", color: c === "siren" ? "var(--accent-cyan)" : "var(--text-secondary)",
                              maxWidth: 240, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                            }}
                            title={v != null ? String(v) : ""}
                          >
                            {isScore && typeof v === "number" ? (
                              <ScoreBadge value={v} size="sm" />
                            ) : (
                              formatCell(v, c)
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        <div style={{
          borderTop: "1px solid var(--border-subtle)",
          padding: "10px 22px",
          display: "flex", alignItems: "center", gap: 16,
          fontSize: 12, color: "var(--text-secondary)",
          background: "rgba(10,10,13,0.60)",
        }}>
          {data && (
            <>
              <span>
                <span style={{ color: "var(--text-muted)" }}>Σ</span>{" "}
                <span className="dem-mono tab-num" style={{ color: "var(--text-primary)", fontWeight: 600 }}>
                  {data.rows.length} rows{data.hasMore ? "+" : ""}
                </span>
              </span>
              <button
                className="dem-btn"
                disabled={data.offset === 0 || loading}
                onClick={() => loadTable(active, { offset: Math.max(0, data.offset - 100), q: search })}
                style={{ marginLeft: "auto" }}
              >
                <Icon name="chevronLeft" size={11} /> Précédent
              </button>
              <button
                className="dem-btn"
                disabled={!data.hasMore || loading}
                onClick={() => loadTable(active, { offset: data.offset + 100, q: search })}
              >
                Suivant <Icon name="chevronRight" size={11} />
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
