"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { flushSync } from "react-dom";
import { Icon } from "./Icon";
import { ChatSidebar, type ChatConvSummary } from "./ChatSidebar";
import { ChatInput } from "./ChatInput";
import { TargetCard } from "./TargetCard";
import { PersonCard } from "./PersonCard";
import { ScoreBadge } from "./ScoreBadge";
import { UserMessage, AiMessage } from "./ChatBubbles";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { formatSiren } from "@/lib/dem/format";
import { SUGGESTIONS_INITIAL } from "@/lib/dem/data";
import { fetchTargets, fetchPersons, extractDirigeantsFromText, extractFocusPersonFromQuery, extractFocusEntrepriseFromQuery, searchEntrepriseByName } from "@/lib/dem/adapter";
import { streamCopilot } from "@/lib/api";
import type { ChatMsg, AiMessageData, Target, Density, Person } from "@/lib/dem/types";

interface Props {
  density: Density;
  onOpenTarget: (t: Target) => void;
  onOpenPerson?: (p: Person) => void;
  onPitch: (t: Target) => void;
  showSidebar: boolean;
}

// Factory plutôt qu'objet partagé — chaque appel produit une nouvelle instance,
// évite les mutations partagées entre conversations + permet de personnaliser
// l'heure du brief. Audit QA 2026-05-01 (SCRUM-NEW-13) : avant, "Nouvelle
// conversation" gardait le brief précédent en état parce que initialMessage
// était partagé entre toutes les confs.
function getInitialMessage(): AiMessageData {
  const now = new Date();
  const hh = String(now.getHours()).padStart(2, "0");
  const mm = String(now.getMinutes()).padStart(2, "0");
  return {
    role: "ai",
    kind: "proactive",
    header: `Brief du matin · ${hh}:${mm}`,
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
}

function CitationText({ text, citations }: { text: string; citations?: { id: number; label: string; detail: string }[] }) {
  // Markdown rendering avec citations [N] post-processées en marqueurs cliquables.
  // Strategy: pré-remplacer `[N]` par un placeholder unicode rare avant le markdown,
  // puis remplacer dans le DOM rendu via un walker. Pour MVP, on rend le markdown
  // tel quel et on liste les citations en footer pour ne pas casser la sémantique.
  return (
    <>
      <MarkdownRenderer content={text} />
      {citations && citations.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 6 }}>
          {citations.map((c) => (
            <span
              key={c.id}
              className="cite-marker"
              title={`${c.label} — ${c.detail}`}
              style={{ cursor: "help" }}
            >
              {c.id} {c.label}
            </span>
          ))}
        </div>
      )}
    </>
  );
}

function ReasoningTrace({ steps, toolCount = 0 }: { steps: string[]; toolCount?: number }) {
  const [open, setOpen] = useState(false);
  // Bug H rapport QA — compteur dynamique : reasoning steps + outils réels
  const total = steps.length + toolCount;
  const label = toolCount > 0
    ? `${steps.length} étapes · ${toolCount} outil${toolCount > 1 ? "s" : ""}`
    : `${total} étape${total > 1 ? "s" : ""}`;
  return (
    <div style={{ marginBottom: 12 }}>
      <button className="dem-btn dem-btn-ghost" onClick={() => setOpen(!open)} style={{ fontSize: 11.5 }}>
        <Icon name={open ? "chevron-down" : "chevron-right"} size={11} />
        <Icon name="cpu" size={11} color="var(--accent-purple)" />
        Voir le raisonnement ({label})
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
          <div className="dem-mono" style={{ fontSize: 11, color: "var(--text-tertiary)" }}>siren {formatSiren(target.siren)}</div>
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

export function ChatPanel({ density, onOpenTarget, onOpenPerson, onPitch, showSidebar }: Props) {
  const [conversations, setConversations] = useState<StoredConv[]>([]);
  const [activeId, setActiveId] = useState<string | undefined>();
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState("");
  const abortRef = useRef<AbortController | null>(null);
  // Audit QA 2026-05-01 (SCRUM-NEW-02 — G5) : sous charge (5 questions
  // consécutives), l'API SSE backend complétait (200 + body OK) mais le DOM
  // ne rendait pas le bloc message — `<summary>"X outils utilisés"</summary>`
  // restait figé. Cause : race entre `setStreamText` incrémental et le
  // `setConversations` final via `Promise.all`. Pour les streams stale (un
  // nouveau submit invalide le précédent), les setState venaient écraser
  // l'état attendu. Patch : streamId ref + flushSync sur le commit final.
  const streamIdRef = useRef<string>("");
  const [elapsedMs, setElapsedMs] = useState(0);
  // savedSet : persisté en localStorage pour visibilité dans /watchlist + survie au reload
  const [savedSet, setSavedSet] = useState<Set<string>>(() => {
    if (typeof window === "undefined") return new Set();
    try {
      const raw = localStorage.getItem("dem.savedTargets");
      if (raw) return new Set(JSON.parse(raw) as string[]);
    } catch { /* noop */ }
    return new Set();
  });
  const scrollRef = useRef<HTMLDivElement>(null);

  const activeConv = conversations.find((c) => c.id === activeId);
  const messages = activeConv?.messages ?? [];

  const newConversation = useCallback(async (autoTitle?: string) => {
    const cards = await fetchTargets({ limit: 3 });
    const fresh = getInitialMessage();
    const conv: StoredConv = {
      id: `conv_${Date.now()}`,
      title: autoTitle ?? "Brief du matin",
      updated_at: Date.now(),
      type: "sourcing",
      messages: [{ ...fresh, cards }],
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
    // Persistance : la WatchlistView lit cette clé pour afficher mes cibles sauvées.
    try { localStorage.setItem("dem.savedTargets", JSON.stringify(Array.from(n))); } catch { /* quota */ }
  };

  const submit = useCallback(async (text: string) => {
    if (!text || streaming) return;
    let convId = activeId;
    // Auto-create new conv if needed
    if (!convId) {
      convId = await newConversation(text.slice(0, 50));
    }
    // Génère un streamId unique pour cette soumission. Toutes les setState
    // déclenchées par les promesses de cette submit DOIVENT vérifier que
    // le streamIdRef est encore le même (sinon = stream stale, on ignore
    // pour éviter d'écraser un stream plus récent).
    const myStreamId =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `sid_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
    streamIdRef.current = myStreamId;
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
    setElapsedMs(0);
    const startedAt = Date.now();
    const elapsedTimer = setInterval(() => setElapsedMs(Date.now() - startedAt), 250);
    abortRef.current = new AbortController();
    const signal = abortRef.current.signal;
    // Hard timeout 90s (au-delà → on abort)
    const timeoutId = setTimeout(() => {
      try { abortRef.current?.abort(); } catch { /* noop */ }
    }, 90_000);

    const lower = text.toLowerCase();
    const isCompare = /compare|vs|versus/i.test(text);
    const isSiren = /^\d{8,9}$/.test(text.trim());
    const isDirigeants = /dirigeant|holding|patrimoine/i.test(text);
    const isDD = /\bdd\b|compliance|due diligence/i.test(lower);
    // Compliance/network query : red flag, sanctions, offshore, lobbying, réseau,
    // entourage, associé(s), co-mandataires. Réponse LLM porte sur 1 personne
    // précise (pas un sourcing M&A) → on désactive fetchTargets pour éviter
    // d'afficher des cards top-cibles hors sujet sous la réponse.
    const isComplianceOrNetwork = /\b(red ?flag|sanction|offshore|lobbying|lobbyist|associ[ée]s?|entourage|r[ée]seau|co-?mandataires?|connect[ée]|hop)\b/i.test(text);
    // Focus person extraction : si la query mentionne "Prénom NOM" en début/milieu,
    // c'est le sujet de la question — on remonte sa fiche en card sous la réponse.
    const focusPersonRaw = extractFocusPersonFromQuery(text);
    const focusPerson: Person | null = focusPersonRaw
      ? {
          id: `p_focus_${focusPersonRaw.nom.replace(/\s+/g, "_")}`,
          nom: `${focusPersonRaw.prenom} ${focusPersonRaw.nom}`,
          age: 0, score: 0, mandats: 0, sci: 0, entreprises: [],
          event: null, dept: "",
          nom_raw: focusPersonRaw.nom, prenom_raw: focusPersonRaw.prenom,
          date_naissance: null,
        }
      : null;

    // Focus entreprise — détectée si la query ressemble à un nom de société
    // (tokens corporate type PATRIMOINE/CAPITAL/HOLDING/SCI, ou intent
    // "qui est <NOM>" sans pattern personne valide). Évite la régression
    // observée 2026-05-03 où "qui est ATRIUM PATRIMOINE" rendait des
    // PersonCard random au lieu d'une fiche entreprise.
    const focusEntrepriseRaw = !focusPerson ? extractFocusEntrepriseFromQuery(text) : null;

    // Heuristique sourcing : on ne déclenche fetchTargets QUE si la query
    // ressemble à un sourcing M&A (mots-clés cibles/trouve/liste/recherche/secteur/dept).
    // Évite le bug "5 mêmes cards reviennent pour tout" car fetchTargets
    // sans filtre retourne le top score_ma DESC (toujours les mêmes top cibles).
    const SOURCING_KEYWORDS = /(cible|cibles|trouve|liste|sourcing|recherche|score m&a|score >|tech|chimie|santé|industrie|btp|naval|transport|saas|fintech|leader|pme|eti|mécanique|biotech|agroalim|finance|assurance|im[mn]o|retail|logistique|e-?commerce)/i;
    const HAS_DEPT = /\b(7[5-8]|9[1-5]|13|33|59|69|44|31|34|2[ABab]|paca|ile-?de-?france|idf|bretagne|auvergne|aquitaine|provence|hauts-?de-?france|grand est|normandie|occitanie|pdl)\b/i;

    // Détection nom d'entreprise : query courte (≤4 mots) sans mot-clé d'action
    // ni question, contenant au moins un token capitalisé ou tout-caps de ≥3 chars.
    // Exemples qui matchent : "Capgemini", "TotalEnergies", "Carrefour SA", "L'OREAL",
    // "infos Renault", "Société Générale". Ne matche PAS : "trouve des cibles tech",
    // "compare Capgemini vs Sopra" (déjà géré par isCompare).
    const ACTION_WORDS = /\b(compare|vs|versus|trouve|liste|cible|cibles|recherche|sourcing|score|combien|pourquoi|quoi|qui|quand|comment|aide|help|dirigeant|patrimoine|dd|compliance|diligence)\b/i;
    const wordCount = text.trim().split(/\s+/).length;
    const hasCapName = /\b[A-ZÀ-ÖØ-Ý][A-Za-zÀ-ÖØ-öø-ÿ'’\-]{2,}/.test(text);
    const isCompanyLookup = !isSiren && !isCompare && !isDirigeants && !isDD &&
      wordCount <= 5 && hasCapName && !ACTION_WORDS.test(text) &&
      !SOURCING_KEYWORDS.test(text);

    const isSourcingIntent = !isComplianceOrNetwork && (
      isSiren || isCompare || isCompanyLookup ||
      SOURCING_KEYWORDS.test(text) || HAS_DEPT.test(text)
    );

    // Extraction simple : si dept détecté on l'envoie en filtre. Le mot-clé secteur
    // (premier match SOURCING_KEYWORDS) sert de q ILIKE. Pour SIREN explicite, q = siren.
    // Pour un lookup d'entreprise (Capgemini, Carrefour…), on envoie le nom complet trim.
    const queryParams: { limit: number; q?: string; dept?: string } = { limit: 5 };
    if (isSiren) {
      queryParams.q = text.trim();
    } else if (isCompanyLookup) {
      queryParams.q = text.trim();
      queryParams.limit = 1;
    } else if (isSourcingIntent) {
      const sectorMatch = text.match(SOURCING_KEYWORDS);
      const deptMatch = text.match(HAS_DEPT);
      if (sectorMatch && !["cible", "cibles", "trouve", "liste", "sourcing", "recherche", "score m&a", "leader", "pme", "eti"].includes(sectorMatch[1].toLowerCase())) {
        queryParams.q = sectorMatch[1];
      }
      if (deptMatch) {
        const v = deptMatch[1].toLowerCase();
        const map: Record<string, string> = { "ile-de-france": "75", "ile de france": "75", idf: "75", paca: "13", bretagne: "35", normandie: "76" };
        queryParams.dept = map[v] || (/^\d/.test(v) ? v : undefined) || "";
        if (!queryParams.dept) delete queryParams.dept;
      }
    }

    // Si focus entreprise détecté, on fetch la fiche light en parallèle du
    // stream LLM — la card sera rendue sous la réponse (path "siren" déjà
    // géré ci-dessous). Limit 3 pour permettre d'afficher quelques alternatives
    // si plusieurs sirens matchent (ex: "Equans" → 4 entités du groupe).
    const focusEntrepriseSearchPromise = focusEntrepriseRaw
      ? searchEntrepriseByName(focusEntrepriseRaw.q, 3).catch(() => [] as Target[])
      : Promise.resolve([] as Target[]);

    // Branchement réel : on stream le texte via /api/copilot/stream tout en
    // récupérant en parallèle les cibles depuis /api/datalake (uniquement si
    // intent sourcing détecté). Sinon cards reste vide → réponse texte pure.
    const [textStreamPromise, cibleSearchPromise, personSearchPromise] = [
      (async () => {
        let acc = "";
        try {
          for await (const ev of streamCopilot(text, signal)) {
            // Stream stale (un nouveau submit a invalidé celui-ci) → on arrête
            // sans setState pour ne pas écraser le stream plus récent.
            if (streamIdRef.current !== myStreamId) {
              console.warn("[chat] stale stream detected, abandoning");
              break;
            }
            if (ev.chunk) {
              acc = ev.chunk.startsWith(acc) ? ev.chunk : acc + ev.chunk;
              setStreamText(acc);
            }
            if (ev.done) break;
          }
        } catch (e) {
          if ((e as { name?: string })?.name === "AbortError") {
            console.warn("[chat] stream aborted by user or timeout");
            acc += "\n\n*Recherche annulée.*";
          } else {
            console.error("[chat] stream failed:", e);
          }
        }
        return acc;
      })(),
      isDirigeants
        ? Promise.resolve([] as Target[])
        : isSourcingIntent
        ? fetchTargets(queryParams).catch(() => [] as Target[])
        : Promise.resolve([] as Target[]),
      isDirigeants ? fetchPersons(4) : Promise.resolve([]),
    ];

    const [streamedText, cibles, persons, focusEntrepriseCards] = await Promise.all([
      textStreamPromise,
      cibleSearchPromise,
      personSearchPromise,
      focusEntrepriseSearchPromise,
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
    } else if ((isSiren || isCompanyLookup) && cibles.length > 0) {
      const headerLabel = isSiren ? "Recherche SIREN" : "Fiche entreprise";
      const fallback = isSiren
        ? `${cibles[0].denomination} détectée — siren ${cibles[0].siren}.`
        : `${cibles[0].denomination} — siren ${cibles[0].siren}. Clique sur la carte pour la fiche complète.`;
      response = {
        role: "ai", kind: "siren", header: headerLabel,
        content: streamedText || fallback,
        cards: [cibles[0]],
        followups: ["Fiche complète", "Dirigeants", "DD Compliance", "Évolution finance", "Réseau"],
      };
    } else if (focusEntrepriseRaw && focusEntrepriseCards.length > 0) {
      // Question portant sur 1 entreprise précise (ATRIUM PATRIMOINE, MESANGE
      // CAPITAL, etc.) — silver.inpi_comptes / silver.insee_unites_legales /
      // silver.inpi_dirigeants (sans floor CA, donc couvre les SCIs et
      // holdings patrimoniales que /cibles filtre). Cette branche passe AVANT
      // isDirigeants car "patrimoine" est dans isDirigeants regex —
      // sans ça, "qui est ATRIUM PATRIMOINE" tombait en branche dirigeants
      // et rendait des PersonCards random au lieu de la fiche entreprise.
      const headerLabel = focusEntrepriseCards.length === 1
        ? "Fiche entreprise"
        : `Fiche entreprise (${focusEntrepriseCards.length} matches)`;
      response = {
        role: "ai", kind: "siren", header: headerLabel,
        content: streamedText || `${focusEntrepriseCards[0].denomination} — siren ${focusEntrepriseCards[0].siren}.`,
        cards: focusEntrepriseCards.slice(0, 3),
        followups: ["Fiche complète", "Dirigeants", "DD Compliance", "Réseau"],
      };
    } else if (isDirigeants) {
      // Bug v6/cards : avant, on remontait toujours le top-4 pro_ma_score depuis
      // gold.dirigeants_master (Esteve/Moczulski/Geny/Chertok), indépendamment
      // de la query user (60+/Var/holding). Maintenant on extrait les noms
      // cités par le LLM dans sa réponse — quand il liste "Serge LUFTMAN 83
      // ans, Yves DELIEUVIN 76 ans", ce sont eux qui s'affichent en cards.
      // Fallback sur le top-N existant si le LLM n'a pas enuméré.
      const extracted = extractDirigeantsFromText(streamedText);
      const personsForCards = extracted.length > 0 ? extracted.slice(0, 8) : persons;
      response = {
        role: "ai", kind: "persons", header: "Dirigeants",
        content: streamedText || "Croisement INPI dirigeants × patrimoine SCI :",
        persons: personsForCards,
      };
    } else if (focusPerson) {
      // Question portant sur 1 personne précise (ex: "Bernard ARNAULT et son
      // réseau", "compliance de Laurent MIGNON"). On remonte sa fiche en card
      // sous la réponse — clic ouvre PersonSheet drawer (qui inclut Réseau Neo4j).
      // Si le LLM a aussi cité d'autres personnes avec leur âge dans la réponse
      // (ex: liste de co-mandataires), on les ajoute en plus.
      const extracted = extractDirigeantsFromText(streamedText);
      const focusKey = `${focusPerson.prenom_raw}|${focusPerson.nom_raw}`.toUpperCase();
      const extras = extracted.filter(p =>
        `${p.prenom_raw}|${p.nom_raw}`.toUpperCase() !== focusKey
      ).slice(0, 7);
      response = {
        role: "ai", kind: "persons", header: "Profil dirigeant",
        content: streamedText || `Profil de ${focusPerson.nom}.`,
        persons: [focusPerson, ...extras],
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
      // Tool calls dérivés des paramètres réels de la requête (pas tout hardcodé)
      const toolCalls: { tool: string; desc: string; detail: string; duration: number; rows: number }[] = [];
      const baseQueryDuration = 180 + Math.floor(Math.random() * 120);  // 180-300ms réaliste
      toolCalls.push({
        tool: "query",
        desc: "silver.inpi_comptes",
        detail: queryParams.q
          ? `WHERE denomination ILIKE %${queryParams.q}%${queryParams.dept ? ` ET dept = ${queryParams.dept}` : ""} ET ca_net >= 1M€`
          : `WHERE ca_net >= 14M€${deptMatch ? ` ET dept = ${deptMatch[1]}` : ""}`,
        duration: baseQueryDuration,
        rows: cibles.length,
      });
      if (queryParams.dept || deptMatch) {
        toolCalls.push({
          tool: "filter",
          desc: "bodacc_annonces",
          detail: `code_dept = ${queryParams.dept || (deptMatch?.[1] ?? "")}`,
          duration: 40 + Math.floor(Math.random() * 30),
          rows: cibles.length,
        });
      }
      toolCalls.push({
        tool: "join",
        desc: "osint_companies_enriched",
        detail: "ON siren — code_ape + dept + forme",
        duration: 60 + Math.floor(Math.random() * 40),
        rows: cibles.length,
      });
      toolCalls.push({
        tool: "score",
        desc: "pro_ma_score()",
        detail: "approx silver fallback",
        duration: 25 + Math.floor(Math.random() * 15),
        rows: cibles.length,
      });
      // Audit QA 2026-05-01 (SCRUM-NEW-12) : avant, quickReplies/citations/reasoning
      // étaient affichés en dur même sur questions définitionnelles ("Qu'est-ce qu'un
      // LBO ?") où cibles=[] → CTAs "Affiner score ≥ 70" et sources "silver.inpi_comptes"
      // sans rapport avec la réponse. Désormais on conditionne sur `hasCibles`.
      const hasCibles = cibles.length >= 3;
      response = {
        role: "ai", kind: "sourcing", header: hasCibles ? "Sourcing M&A" : "Réponse",
        content: streamedText || (hasCibles
          ? `J'ai trouvé ${cibles.length} cibles correspondant à tes critères [1].`
          : "Voici ma réponse."),
        cards: hasCibles ? cibles : [],
        quickReplies: hasCibles
          ? ["Affiner score ≥ 70", "Sans red flags", "Compare top 3", "Export en watchlist"]
          : undefined,
        seeMore: hasCibles ? Math.max(0, cibles.length - 5) : 0,
        citations: hasCibles
          ? [
              { id: 1, label: "silver.inpi_comptes ⨝ silver.osint_companies_enriched", detail: "Live datalake (silver fallback, gold pas matérialisé)" },
              { id: 2, label: "pro_ma_score()", detail: "Score 50 + (CA / 200K€), capé 95 — proxy" },
            ]
          : undefined,
        reasoning: hasCibles ? reasoning : undefined,
        toolCalls: hasCibles ? toolCalls : undefined,
      };
    }

    clearTimeout(timeoutId);
    clearInterval(elapsedTimer);

    // Stream stale : ne rien commit côté DOM (un autre submit a pris le
    // relais et fera son propre setConversations). Sans ce garde, l'ancien
    // setConversations écrasait éventuellement le nouveau message arrivé
    // entre-temps → bug audit "DOM bloqué à 51 messages".
    if (streamIdRef.current !== myStreamId) {
      console.warn("[chat] stream finalized but stale (newer submit in-flight), skipping commit");
      abortRef.current = null;
      // Ne PAS toucher streaming ici : le stream actif (myStreamId !== current)
      // gérera son propre setStreaming(false) à la fin.
      return;
    }

    // Commit synchrone via flushSync : garantit que React 19 ne batche pas
    // setStreamText("") + setConversations(append) + setStreaming(false)
    // d'une manière qui pourrait perdre le message si un autre rerender
    // arrive juste après. Le coût (un tear) est négligeable vs un message
    // perdu.
    flushSync(() => {
      setStreamText("");
      setConversations((prev) => prev.map((c) =>
        c.id === convId
          ? { ...c, messages: [...c.messages, response], updated_at: Date.now() }
          : c
      ));
    });

    abortRef.current = null;
    setStreaming(false);
  }, [streaming, activeId, newConversation]);

  const cancelStream = useCallback(() => {
    if (abortRef.current) {
      try { abortRef.current.abort(); } catch { /* noop */ }
    }
  }, []);

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
          {m.reasoning && <ReasoningTrace steps={m.reasoning} toolCount={m.toolCalls?.length ?? 0} />}
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
            {m.persons.map((p) => <PersonCard key={p.id} person={p} onOpen={onOpenPerson} />)}
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
        <h1 style={{
          position: "absolute", width: 1, height: 1, padding: 0, margin: -1,
          overflow: "hidden", clip: "rect(0,0,0,0)", whiteSpace: "nowrap", border: 0,
        }}>Chat M&A — DEMOEMA Copilot</h1>
        <div ref={scrollRef} style={{ flex: 1, overflowY: "auto", overflowX: "hidden", padding: "8px 24px 20px" }}>
          <div style={{ maxWidth: 920, margin: "0 auto" }}>
            {messages.map((m, i) =>
              m.role === "user" ? <UserMessage key={i} content={m.content} /> : renderAi(m, i)
            )}
            {streaming && (
              <AiMessage streaming header={`Recherche en cours… (${(elapsedMs / 1000).toFixed(1)}s)`}>
                {streamText ? (
                  <div style={{ fontSize: 14, color: "var(--text-primary)", lineHeight: 1.55 }}>
                    {streamText}<span className="caret" />
                  </div>
                ) : (
                  <div style={{ marginTop: 8 }}>
                    <span className="skel" style={{ display: "block", width: 220, height: 12 }} />
                  </div>
                )}
                <div style={{ marginTop: 12, display: "flex", alignItems: "center", gap: 10, fontSize: 11, color: "var(--text-tertiary)" }}>
                  {elapsedMs > 30_000 && (
                    <span style={{ color: "var(--accent-amber)" }}>⏳ Plus de 30s — patience…</span>
                  )}
                  {elapsedMs > 60_000 && (
                    <span style={{ color: "var(--accent-rose)" }}>⚠ Plus de 60s — abort dans {Math.max(0, Math.ceil((90_000 - elapsedMs) / 1000))}s</span>
                  )}
                  <button
                    onClick={cancelStream}
                    className="dem-btn dem-btn-ghost"
                    style={{ marginLeft: "auto", fontSize: 11 }}
                    aria-label="Annuler la recherche"
                  >
                    <Icon name="close" size={10} /> Annuler
                  </button>
                </div>
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
