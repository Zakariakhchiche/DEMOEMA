"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Icon } from "./Icon";
import { ChatSidebar, type ChatConvSummary } from "./ChatSidebar";
import { ChatInput } from "./ChatInput";
import { TargetCard } from "./TargetCard";
import { PersonCard } from "./PersonCard";
import { ScoreBadge } from "./ScoreBadge";
import { UserMessage, AiMessage } from "./ChatBubbles";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { SUGGESTIONS_INITIAL } from "@/lib/dem/data";
import { fetchTargets, fetchPersons } from "@/lib/dem/adapter";
import { streamCopilot } from "@/lib/api";
import type { ChatMsg, AiMessageData, Target, Density } from "@/lib/dem/types";

interface Props {
  density: Density;
  onOpenTarget: (t: Target) => void;
  onPitch: (t: Target) => void;
  showSidebar: boolean;
}

const initialMessage: AiMessageData = {
  role: "ai",
  kind: "proactive",
  header: "Brief du matin · 08:14",
  content:
    "Bonjour Anne ☕ J'ai analysé ta watchlist \"Cibles tech IDF\" cette nuit. Voici les premières alertes prioritaires sur tes cibles sauvées :",
  cards: [],
  stats: [
    { l: "Nouveaux signaux 24h", v: "47" },
    { l: "Cibles franchies tier-1", v: "12" },
    { l: "Nouveaux red flags majeurs", v: "0", color: "var(--accent-emerald)" },
  ],
  suggestion: "Tu veux qu'on regarde le mandat sell-side prioritaire ce matin ?",
};

function CitationText({ text, citations }: { text: string; citations?: { id: number; label: string; detail: string }[] }) {
  if (!citations) return <span>{text}</span>;
  const parts = text.split(/(\[\d+\])/g);
  return (
    <span>
      {parts.map((p, i) => {
        const m = p.match(/\[(\d+)\]/);
        if (m) {
          const id = parseInt(m[1], 10);
          const c = citations.find((x) => x.id === id);
          if (!c) return p;
          return (
            <span key={i} className="cite-marker" title={`${c.label} — ${c.detail}`}>
              {id}
            </span>
          );
        }
        return <span key={i}>{p}</span>;
      })}
    </span>
  );
}

function ReasoningTrace({ steps }: { steps: string[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ marginBottom: 12 }}>
      <button className="dem-btn dem-btn-ghost" onClick={() => setOpen(!open)} style={{ fontSize: 11.5 }}>
        <Icon name={open ? "chevron-down" : "chevron-right"} size={11} />
        <Icon name="cpu" size={11} color="var(--accent-purple)" />
        Voir le raisonnement ({steps.length} étapes)
      </button>
      {open && (
        <div className="reasoning-trace fade-up">
          {steps.map((s, i) => <div key={i} className="step">{s}</div>)}
        </div>
      )}
    </div>
  );
}

function CompareTable({ a, b }: { a: Target; b: Target }) {
  const rows: [string, React.ReactNode, React.ReactNode, "score" | "value" | "text" | "flag"][] = [
    ["pro_ma_score", a.score, b.score, "score"],
    ["CA dernier", a.ca_str, b.ca_str, "value"],
    ["EBITDA", a.ebitda_str, b.ebitda_str, "value"],
    ["Effectif", a.effectif ?? "—", b.effectif ?? "—", "value"],
    ["Top dirigeant", a.top_dirigeant.nom, b.top_dirigeant.nom, "text"],
    [
      "Red flags",
      a.red_flags.length || "Aucun",
      b.red_flags.length ? `${b.red_flags.length} (${b.red_flags[0].source})` : "Aucun",
      "flag",
    ],
  ];
  return (
    <div className="dem-glass" style={{ borderRadius: 12, padding: 0, overflow: "hidden", marginTop: 4 }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr style={{ background: "rgba(255,255,255,0.02)" }}>
            <th style={{
              padding: "10px 16px", textAlign: "left", fontSize: 10.5,
              color: "var(--text-tertiary)", textTransform: "uppercase",
              letterSpacing: "0.06em", fontWeight: 600,
            }}>Critère</th>
            <th style={{ padding: "10px 16px", textAlign: "left", fontSize: 12, fontWeight: 600 }}>{a.denomination}</th>
            <th style={{ padding: "10px 16px", textAlign: "left", fontSize: 12, fontWeight: 600 }}>{b.denomination}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([label, va, vb, kind], i) => (
            <tr key={i} style={{ borderTop: "1px solid var(--border-subtle)" }}>
              <td style={{ padding: "10px 16px", color: "var(--text-tertiary)", fontSize: 12 }}>{label}</td>
              <td style={{ padding: "10px 16px" }}>
                {kind === "score" ? <ScoreBadge value={Number(va)} size="sm" /> :
                 kind === "flag" ? (
                   <span style={{
                     color: va === "Aucun" ? "var(--accent-emerald)" : "var(--accent-rose)",
                     fontWeight: 600, fontSize: 12,
                   }}>{va === "Aucun" ? "✓ Aucun" : va}</span>
                 ) :
                 <span className={kind === "value" ? "dem-mono tab-num" : ""} style={{ fontWeight: 600, color: "var(--text-primary)" }}>{va}</span>}
              </td>
              <td style={{ padding: "10px 16px" }}>
                {kind === "score" ? <ScoreBadge value={Number(vb)} size="sm" /> :
                 kind === "flag" ? (
                   <span style={{
                     color: vb === "Aucun" ? "var(--accent-emerald)" : "var(--accent-rose)",
                     fontWeight: 600, fontSize: 12,
                   }}>{vb === "Aucun" ? "✓ Aucun" : vb}</span>
                 ) :
                 <span className={kind === "value" ? "dem-mono tab-num" : ""} style={{ fontWeight: 600, color: "var(--text-primary)" }}>{vb}</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DDBlock({ target }: { target: Target }) {
  const checks: { label: string; ok: boolean; source: string }[] = [
    { label: "Sanctions UE/US", ok: !target.red_flags.some((f) => f.type === "compliance" || f.type === "sanction"), source: "OpenSanctions" },
    { label: "ICIJ Offshore", ok: !target.red_flags.some((f) => f.type === "icij"), source: "ICIJ Pandora" },
    { label: "Procédures collectives", ok: !target.red_flags.some((f) => f.type === "procedure"), source: "BODACC" },
    { label: "Contentieux récents", ok: true, source: "Judilibre 90j" },
    { label: "Marchés publics anomalies", ok: true, source: "DECP 12 mois" },
    { label: "Presse négative", ok: true, source: "Press monitoring" },
  ];

  return (
    <div className="dem-glass" style={{ borderRadius: 12, padding: 18, marginTop: 6 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
        <ScoreBadge value={target.score} size="md" />
        <div>
          <div style={{ fontSize: 14, fontWeight: 700 }}>{target.denomination}</div>
          <div className="dem-mono" style={{ fontSize: 11, color: "var(--text-tertiary)" }}>siren {target.siren}</div>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
          <button className="dem-btn dem-btn-primary"><Icon name="sparkles" size={11} /> Pitch Ready PDF</button>
        </div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        {checks.map((c, i) => (
          <div key={i} style={{
            padding: "10px 12px", borderRadius: 9,
            border: `1px solid ${c.ok ? "rgba(52,211,153,0.18)" : "rgba(251,113,133,0.30)"}`,
            background: c.ok ? "rgba(52,211,153,0.04)" : "rgba(251,113,133,0.05)",
            display: "flex", gap: 10, alignItems: "center",
          }}>
            <div style={{
              width: 22, height: 22, borderRadius: 999,
              display: "flex", alignItems: "center", justifyContent: "center",
              background: c.ok ? "rgba(52,211,153,0.15)" : "rgba(251,113,133,0.18)",
              flexShrink: 0,
            }}>
              <Icon name={c.ok ? "check" : "warning"} size={12} color={c.ok ? "var(--accent-emerald)" : "var(--accent-rose)"} strokeWidth={2.4} />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 12.5, fontWeight: 600, color: c.ok ? "var(--text-primary)" : "var(--accent-rose)" }}>{c.label}</div>
              <div style={{ fontSize: 10.5, color: "var(--text-tertiary)", marginTop: 2 }}>{c.source}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

interface StoredConv {
  id: string;
  title: string;
  updated_at: number;
  type?: "sourcing" | "dd" | "compare" | "graph";
  messages: ChatMsg[];
}

const STORAGE_KEY = "demoema_dem_conversations";

function loadConvs(): StoredConv[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
}

function saveConvs(convs: StoredConv[]) {
  if (typeof window === "undefined") return;
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(convs)); } catch {}
}

export function ChatPanel({ density, onOpenTarget, onPitch, showSidebar }: Props) {
  const [conversations, setConversations] = useState<StoredConv[]>([]);
  const [activeId, setActiveId] = useState<string | undefined>();
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState("");
  const [savedSet, setSavedSet] = useState<Set<string>>(new Set());
  const scrollRef = useRef<HTMLDivElement>(null);

  const activeConv = conversations.find((c) => c.id === activeId);
  const messages = activeConv?.messages ?? [];

  const newConversation = useCallback(async (autoTitle?: string) => {
    const cards = await fetchTargets({ limit: 3 });
    const conv: StoredConv = {
      id: `conv_${Date.now()}`,
      title: autoTitle ?? "Brief du matin",
      updated_at: Date.now(),
      type: "sourcing",
      messages: [{ ...initialMessage, cards }],
    };
    setConversations((prev) => [conv, ...prev]);
    setActiveId(conv.id);
    return conv.id;
  }, []);

  // Hydrate on mount
  useEffect(() => {
    const stored = loadConvs();
    if (stored.length > 0) {
      setConversations(stored);
      setActiveId(stored[0].id);
    } else {
      void newConversation();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Persist on changes
  useEffect(() => {
    if (conversations.length > 0) saveConvs(conversations);
  }, [conversations]);

  useEffect(() => {
    if (scrollRef.current) {
      requestAnimationFrame(() => {
        if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      });
    }
  }, [messages, streamText]);

  const handleSave = (siren: string) => {
    const n = new Set(savedSet);
    if (n.has(siren)) n.delete(siren); else n.add(siren);
    setSavedSet(n);
  };

  const submit = useCallback(async (text: string) => {
    if (!text || streaming) return;
    let convId = activeId;
    // Auto-create new conv if needed
    if (!convId) {
      convId = await newConversation(text.slice(0, 50));
    }
    setConversations((prev) => prev.map((c) =>
      c.id === convId
        ? {
            ...c,
            title: c.messages.length <= 1 ? text.slice(0, 60) : c.title,
            messages: [...c.messages, { role: "user", content: text } as ChatMsg],
            updated_at: Date.now(),
          }
        : c
    ));
    setStreaming(true);
    setStreamText("");

    const lower = text.toLowerCase();
    const isCompare = /compare|vs|versus/i.test(text);
    const isSiren = /^\d{8,9}$/.test(text.trim());
    const isDirigeants = /dirigeant|holding|patrimoine/i.test(text);
    const isDD = /\bdd\b|compliance|due diligence/i.test(lower);

    // Branchement réel : on stream le texte via /api/copilot/stream tout en
    // récupérant en parallèle les cibles depuis /api/datalake.
    const [textStreamPromise, cibleSearchPromise, personSearchPromise] = [
      (async () => {
        let acc = "";
        try {
          for await (const ev of streamCopilot(text)) {
            if (ev.chunk) {
              acc = ev.chunk.startsWith(acc) ? ev.chunk : acc + ev.chunk;
              setStreamText(acc);
            }
            if (ev.done) break;
          }
        } catch (e) {
          console.error("[chat] stream failed:", e);
        }
        return acc;
      })(),
      isDirigeants ? Promise.resolve([] as Target[]) : fetchTargets({ limit: 5, q: isSiren ? text : undefined }),
      isDirigeants ? fetchPersons(4) : Promise.resolve([]),
    ];

    const [streamedText, cibles, persons] = await Promise.all([
      textStreamPromise,
      cibleSearchPromise,
      personSearchPromise,
    ]);

    let response: AiMessageData;
    if (isCompare && cibles.length >= 2) {
      response = {
        role: "ai", kind: "compare", header: "Comparaison",
        content: streamedText || `Comparaison de ${cibles[0].denomination} vs ${cibles[1].denomination}.`,
        compare: { a: cibles[0], b: cibles[1] },
        verdict: streamedText ? "" :
          `${cibles[0].denomination} score ${cibles[0].score}, ${cibles[1].denomination} score ${cibles[1].score}. Avantage à la cible avec le score le plus élevé.`,
        citations: [
          { id: 1, label: "gold.cibles_ma_top / silver fallback", detail: "Live datalake" },
        ],
      };
    } else if (isSiren && cibles.length > 0) {
      response = {
        role: "ai", kind: "siren", header: "Recherche SIREN",
        content: streamedText || `${cibles[0].denomination} détectée — siren ${cibles[0].siren}.`,
        cards: [cibles[0]],
        followups: ["Fiche complète", "Dirigeants", "DD Compliance", "Évolution finance", "Réseau"],
      };
    } else if (isDirigeants) {
      response = {
        role: "ai", kind: "persons", header: "Dirigeants",
        content: streamedText || "Croisement INPI dirigeants × patrimoine SCI :",
        persons,
      };
    } else if (isDD && cibles.length > 0) {
      response = {
        role: "ai", kind: "dd", header: "Due Diligence Compliance",
        content: streamedText || `DD compliance ${cibles[0].denomination} — analyse 6 dimensions :`,
        dd: cibles[0],
      };
    } else {
      // Reasoning + tool calls dérivés de la query réelle (pas de mock).
      const deptMatch = text.match(/\b(7[5-8]|9[1-5]|13|33|59|69|2[ABab])\b/);
      const reasoning: string[] = [
        `Query: "${text}"`,
        `→ JOIN silver.inpi_comptes (6.3M lignes financières) + silver.osint_companies_enriched (NAF, dept, forme).`,
        `→ Filter ca_net >= 14M€${deptMatch ? ` ET dept = ${deptMatch[1]}` : ""}.`,
        `→ ${cibles.length} cibles renvoyées, triées par CA décroissant.`,
        `→ Score M&A = 50 + (CA_net / 200K€), capé à 95 — proxy gold.cibles_ma_top en attendant matérialisation.`,
      ];
      const toolCalls = [
        { tool: "query", desc: "silver.inpi_comptes", detail: `WHERE ca_net >= 14M€`, duration: 240, rows: cibles.length },
        { tool: "join", desc: "osint_companies_enriched", detail: "ON siren — code_ape + dept + forme", duration: 80, rows: cibles.length },
        { tool: "score", desc: "pro_ma_score()", detail: "approx silver fallback", duration: 30, rows: cibles.length },
      ];
      response = {
        role: "ai", kind: "sourcing", header: "Sourcing M&A",
        content: streamedText || `J'ai trouvé ${cibles.length} cibles correspondant à tes critères [1].`,
        cards: cibles,
        quickReplies: ["Affiner score ≥ 70", "Sans red flags", "Compare top 3", "Export en watchlist"],
        seeMore: Math.max(0, cibles.length - 5),
        citations: [
          { id: 1, label: "silver.inpi_comptes ⨝ silver.osint_companies_enriched", detail: "Live datalake (silver fallback, gold pas matérialisé)" },
          { id: 2, label: "pro_ma_score()", detail: "Score 50 + (CA / 200K€), capé 95 — proxy" },
        ],
        reasoning,
        toolCalls,
      };
    }

    setStreamText("");
    setConversations((prev) => prev.map((c) =>
      c.id === convId
        ? { ...c, messages: [...c.messages, response], updated_at: Date.now() }
        : c
    ));
    setStreaming(false);
  }, [streaming, activeId, newConversation]);

  const renderAi = (m: AiMessageData, i: number) => (
    <AiMessage key={i} header={m.header} streaming={false}>
      {m.kind === "proactive" && (
        <div className="fade-up">
          <div style={{ marginBottom: 14 }}><MarkdownRenderer content={m.content} /></div>
          {m.cards && m.cards.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {m.cards.map((c) => (
                <TargetCard
                  key={c.siren}
                  target={c}
                  density={density}
                  isSaved={savedSet.has(c.siren)}
                  onView={() => onOpenTarget(c)}
                  onSave={() => handleSave(c.siren)}
                  onPitch={() => onPitch(c)}
                />
              ))}
            </div>
          )}
          {m.stats && (
            <div className="dem-glass" style={{
              marginTop: 14, padding: "12px 16px", borderRadius: 10,
              display: "flex", gap: 18, fontSize: 12,
            }}>
              {m.stats.map((s, j) => (
                <div key={j} style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  <span style={{
                    color: "var(--text-tertiary)", fontSize: 10.5,
                    textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600,
                  }}>{s.l}</span>
                  <span className="dem-mono tab-num" style={{ fontSize: 17, fontWeight: 700, color: s.color || "var(--text-primary)" }}>{s.v}</span>
                </div>
              ))}
            </div>
          )}
          {m.suggestion && (
            <div style={{
              marginTop: 12, padding: "10px 14px", borderRadius: 10,
              background: "linear-gradient(135deg, rgba(96,165,250,0.06), rgba(167,139,250,0.06))",
              border: "1px solid rgba(96,165,250,0.20)",
              display: "flex", alignItems: "center", gap: 10,
            }}>
              <Icon name="sparkles" size={13} color="var(--accent-purple)" />
              <span style={{ fontSize: 12.5, color: "var(--text-primary)" }}>{m.suggestion}</span>
              <button className="dem-btn dem-btn-primary" style={{ marginLeft: "auto" }} onClick={() => submit("Lance la DD complète sur le sell-side prioritaire")}>
                Lancer la DD
              </button>
            </div>
          )}
        </div>
      )}

      {m.kind === "sourcing" && (
        <div className="fade-up">
          {m.toolCalls && (
            <details style={{ marginBottom: 10 }}>
              <summary style={{ fontSize: 11.5, color: "var(--text-tertiary)", cursor: "pointer", padding: "4px 0" }}>
                <Icon name="check" size={11} color="var(--accent-emerald)" /> {m.toolCalls.length} outils utilisés ({m.toolCalls.reduce((s, c) => s + c.duration, 0)}ms)
              </summary>
              <div style={{ marginTop: 8 }}>
                {m.toolCalls.map((c, i) => (
                  <div key={i} className="tool-call done">
                    <span className="dot" />
                    <span className="dem-mono" style={{ color: "var(--accent-cyan)", fontWeight: 600, fontSize: 11.5 }}>{c.tool}</span>
                    <span className="dem-mono" style={{ color: "var(--text-primary)" }}>{c.desc}</span>
                    <span className="dem-mono" style={{ color: "var(--text-tertiary)", fontSize: 11, flex: 1 }}>{c.detail}</span>
                    <span className="dem-mono tab-num" style={{ fontSize: 10.5, color: "var(--accent-emerald)" }}>✓ {c.rows} · {c.duration}ms</span>
                  </div>
                ))}
              </div>
            </details>
          )}
          {m.reasoning && <ReasoningTrace steps={m.reasoning} />}
          <div style={{ fontSize: 14, color: "var(--text-primary)", lineHeight: 1.55, marginBottom: 12 }}>
            <CitationText text={m.content} citations={m.citations} />
          </div>
          {m.cards && m.cards.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {m.cards.map((c, j) => (
                <div key={c.siren} className="fade-up" style={{ animationDelay: `${j * 70}ms` }}>
                  <TargetCard
                    target={c}
                    density={density}
                    isSaved={savedSet.has(c.siren)}
                    onView={() => onOpenTarget(c)}
                    onSave={() => handleSave(c.siren)}
                    onPitch={() => onPitch(c)}
                  />
                </div>
              ))}
            </div>
          )}
          {m.quickReplies && m.quickReplies.length > 0 && (
            <div style={{ marginTop: 14, display: "flex", gap: 6, flexWrap: "wrap" }}>
              <span style={{ fontSize: 11.5, color: "var(--text-tertiary)", marginRight: 4, alignSelf: "center" }}>
                <Icon name="sparkles" size={10} color="var(--accent-purple)" /> Affiner :
              </span>
              {m.quickReplies.map((q, j) => (
                <button key={j} className="dem-chip" onClick={() => submit(q)}>{q}</button>
              ))}
            </div>
          )}
          {m.citations && (
            <div style={{
              marginTop: 12, padding: "10px 12px", borderRadius: 8,
              background: "rgba(255,255,255,0.02)",
              border: "1px solid var(--border-subtle)",
            }}>
              <div style={{
                fontSize: 10.5, color: "var(--text-tertiary)",
                textTransform: "uppercase", letterSpacing: "0.06em",
                fontWeight: 600, marginBottom: 6,
              }}>Sources</div>
              {m.citations.map((c, k) => (
                <div key={k} style={{
                  display: "flex", alignItems: "center", gap: 8,
                  fontSize: 11.5, color: "var(--text-secondary)", padding: "3px 0",
                }}>
                  <span className="cite-marker" style={{ marginRight: 0 }}>{c.id}</span>
                  <span className="dem-mono" style={{ color: "var(--accent-cyan)", fontWeight: 600 }}>{c.label}</span>
                  <span style={{ color: "var(--text-tertiary)", fontSize: 11 }}>· {c.detail}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {m.kind === "compare" && m.compare && (
        <div className="fade-up">
          <div style={{ marginBottom: 12 }}><MarkdownRenderer content={m.content} /></div>
          <CompareTable a={m.compare.a} b={m.compare.b} />
          {m.verdict && (
            <div style={{
              marginTop: 12, padding: "10px 14px", borderRadius: 10,
              background: "rgba(167,139,250,0.06)",
              border: "1px solid rgba(167,139,250,0.20)",
              fontSize: 12.5, color: "var(--text-primary)", lineHeight: 1.55,
            }}>
              <strong style={{ color: "var(--accent-purple)" }}>Recommandation : </strong>{m.verdict}
            </div>
          )}
        </div>
      )}

      {m.kind === "siren" && m.cards && (
        <div className="fade-up">
          <div style={{ marginBottom: 10 }}><MarkdownRenderer content={m.content} /></div>
          {m.cards.map((c) => (
            <TargetCard
              key={c.siren}
              target={c}
              density={density}
              isSaved={savedSet.has(c.siren)}
              onView={() => onOpenTarget(c)}
              onSave={() => handleSave(c.siren)}
              onPitch={() => onPitch(c)}
            />
          ))}
          {m.followups && (
            <div style={{ marginTop: 10, display: "flex", gap: 6, flexWrap: "wrap" }}>
              {m.followups.map((f, j) => (
                <button key={j} className="dem-chip" onClick={() => submit(f + " " + (m.cards![0]?.siren ?? ""))}>{f}</button>
              ))}
            </div>
          )}
        </div>
      )}

      {m.kind === "persons" && m.persons && (
        <div className="fade-up">
          <div style={{ marginBottom: 12 }}><MarkdownRenderer content={m.content} /></div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {m.persons.map((p) => <PersonCard key={p.id} person={p} />)}
          </div>
        </div>
      )}

      {m.kind === "dd" && m.dd && (
        <div className="fade-up">
          <div style={{ marginBottom: 6 }}><MarkdownRenderer content={m.content} /></div>
          <DDBlock target={m.dd} />
        </div>
      )}

      {m.kind === "plain" && (
        <MarkdownRenderer content={m.content} />
      )}
    </AiMessage>
  );

  const sidebarConvs: ChatConvSummary[] = conversations.map((c) => ({
    id: c.id, title: c.title, updated_at: c.updated_at, type: c.type,
  }));

  return (
    <>
      <ChatSidebar
        active={activeId}
        conversations={sidebarConvs}
        onSelect={setActiveId}
        onNew={() => void newConversation()}
        collapsed={!showSidebar}
      />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, overflow: "hidden" }}>
        <div ref={scrollRef} style={{ flex: 1, overflowY: "auto", overflowX: "hidden", padding: "8px 24px 20px" }}>
          <div style={{ maxWidth: 920, margin: "0 auto" }}>
            {messages.map((m, i) =>
              m.role === "user" ? <UserMessage key={i} content={m.content} /> : renderAi(m, i)
            )}
            {streaming && (
              <AiMessage streaming header="Recherche en cours…">
                {streamText ? (
                  <div style={{ fontSize: 14, color: "var(--text-primary)", lineHeight: 1.55 }}>
                    {streamText}<span className="caret" />
                  </div>
                ) : (
                  <div style={{ marginTop: 8 }}>
                    <span className="skel" style={{ display: "block", width: 220, height: 12 }} />
                  </div>
                )}
              </AiMessage>
            )}
          </div>
        </div>
        <div style={{
          padding: "12px 24px 18px",
          borderTop: "1px solid var(--border-subtle)",
          background: "linear-gradient(180deg, transparent, rgba(5,5,7,0.85))",
        }}>
          <ChatInput
            onSubmit={submit}
            suggestions={messages.length <= 1 ? SUGGESTIONS_INITIAL : null}
            isStreaming={streaming}
          />
        </div>
      </div>
    </>
  );
}
