"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, AlertTriangle } from "lucide-react";
import { ChatMessage } from "@/components/copilot/ChatMessage";
import { ChatInput } from "@/components/copilot/ChatInput";
import { ConversationsSidebar } from "@/components/copilot/ConversationsSidebar";
import { datalakeApi, streamCopilot } from "@/lib/api";
import type { ChatMessage as Msg, Conversation, Cible } from "@/lib/types/dem";

const STARTER_PROMPTS = [
  "Top cibles M&A chimie spé IDF avec CA > 20M€",
  "Compare Acme Industries et Beta Pharma sur 5 critères",
  "DD compliance complet sur Beta Pharma Holding",
  "Dirigeants 60+ avec holding patrimoniale dans le Var",
  "Sociétés cotées avec OPA récente",
];

/**
 * Heuristique légère pour décider si un prompt mérite des cards cibles M&A.
 * Si oui, on lance en parallèle un fetch /api/datalake/cibles avec extraction
 * naïve dept/score depuis le texte.
 */
function shouldFetchCibles(prompt: string): boolean {
  return /cible|target|m&a|score|dirigeant|opa|holding|patrimoine|société|entreprise|sci/i.test(
    prompt
  );
}

function extractDept(prompt: string): string | undefined {
  const m = prompt.match(/\b(7[5-8]|9[1-5]|13|33|59|69|13|2[ABab]|97[1-8])\b/);
  return m?.[1]?.toUpperCase();
}

function extractMinScore(prompt: string): number | undefined {
  const m = prompt.match(/score\s*[>\s>=]+\s*(\d{1,3})/i);
  if (m) return parseInt(m[1], 10);
  return undefined;
}

export default function CopilotPage() {
  const [conversations, setConversations] = useState<Conversation[]>(() => {
    if (typeof window === "undefined") return [];
    try {
      const saved = localStorage.getItem("demoema_conversations");
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [activeId, setActiveId] = useState<string | undefined>(conversations[0]?.id);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const activeConv = conversations.find((c) => c.id === activeId);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      localStorage.setItem("demoema_conversations", JSON.stringify(conversations));
    } catch {}
  }, [conversations]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeConv?.messages.length]);

  const newConversation = useCallback(() => {
    const c: Conversation = {
      id: `conv_${Date.now()}`,
      title: "Nouvelle conversation",
      created_at: Date.now(),
      updated_at: Date.now(),
      messages: [],
    };
    setConversations((prev) => [c, ...prev]);
    setActiveId(c.id);
  }, []);

  const sendMessage = useCallback(
    async (prompt: string) => {
      setError(null);
      let convId = activeId;
      if (!convId) {
        const c: Conversation = {
          id: `conv_${Date.now()}`,
          title: prompt.slice(0, 50),
          created_at: Date.now(),
          updated_at: Date.now(),
          messages: [],
        };
        setConversations((prev) => [c, ...prev]);
        convId = c.id;
        setActiveId(convId);
      }

      const userMsg: Msg = {
        id: `msg_${Date.now()}_user`,
        role: "user",
        content: prompt,
        timestamp: Date.now(),
      };

      const aiMsgId = `msg_${Date.now()}_ai`;
      const aiMsg: Msg = {
        id: aiMsgId,
        role: "ai",
        content: "",
        timestamp: Date.now(),
        streaming: true,
      };

      setConversations((prev) =>
        prev.map((c) =>
          c.id === convId
            ? {
                ...c,
                title: c.messages.length === 0 ? prompt.slice(0, 50) : c.title,
                messages: [...c.messages, userMsg, aiMsg],
                updated_at: Date.now(),
              }
            : c
        )
      );

      setStreaming(true);

      // En parallèle : fetch des cibles M&A pour cards (real DB) ───────────
      const cibleSearchP = shouldFetchCibles(prompt)
        ? datalakeApi
            .searchCibles({
              q: prompt.length < 50 ? undefined : undefined, // on évite de polluer la recherche avec la phrase complète
              dept: extractDept(prompt),
              minScore: extractMinScore(prompt),
              isProMa: /pro\s*m&a|dirigeant.*60|holding/i.test(prompt) ? true : undefined,
              isAssetRich: /patrimo|asset|sci|immobilier/i.test(prompt) ? true : undefined,
              hasRedFlags: /sans\s+red\s+flag|exclure.*red.*flag/i.test(prompt)
                ? false
                : /red\s+flag|sanction|compliance/i.test(prompt)
                ? true
                : undefined,
              limit: 5,
              sort: "score_ma",
            })
            .catch((e) => {
              console.warn("[copilot] cibles search failed:", e);
              return null;
            })
        : Promise.resolve(null);

      // Streaming SSE depuis backend ─────────────────────────────────────
      const ac = new AbortController();
      abortRef.current = ac;
      let acc = "";
      try {
        for await (const ev of streamCopilot(prompt, ac.signal)) {
          if (ev.chunk) {
            acc += ev.chunk;
            setConversations((prev) =>
              prev.map((c) =>
                c.id === convId
                  ? {
                      ...c,
                      messages: c.messages.map((m) =>
                        m.id === aiMsgId
                          ? { ...m, content: acc, streaming: true }
                          : m
                      ),
                    }
                  : c
              )
            );
          }
          if (ev.done) {
            const cibleRes = await cibleSearchP;
            const cards = cibleRes?.cibles?.length
              ? cibleRes.cibles.map((c) => ({
                  type: "cible" as const,
                  payload: c as Cible,
                }))
              : undefined;
            setConversations((prev) =>
              prev.map((c) =>
                c.id === convId
                  ? {
                      ...c,
                      messages: c.messages.map((m) =>
                        m.id === aiMsgId
                          ? {
                              ...m,
                              content: acc,
                              streaming: false,
                              cards,
                              quick_replies: cards
                                ? [
                                    { label: "Affiner: Score ≥ 70", prompt: "Filtre Score >= 70" },
                                    { label: "Sans red flags", prompt: "Exclure red flags compliance" },
                                    { label: "Compare top 3", prompt: "Compare les 3 premières cibles" },
                                  ]
                                : undefined,
                            }
                          : m
                      ),
                    }
                  : c
              )
            );
          }
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        if (!msg.includes("aborted")) {
          setError(msg);
          setConversations((prev) =>
            prev.map((c) =>
              c.id === convId
                ? {
                    ...c,
                    messages: c.messages.map((m) =>
                      m.id === aiMsgId
                        ? {
                            ...m,
                            content:
                              acc ||
                              "Erreur backend. Vérifie que /api/copilot/stream est joignable.",
                            streaming: false,
                          }
                        : m
                    ),
                  }
                : c
            )
          );
        }
      } finally {
        setStreaming(false);
        abortRef.current = null;
      }
    },
    [activeId]
  );

  return (
    <div className="flex h-screen overflow-hidden bg-zinc-950 text-zinc-100">
      <div
        className="pointer-events-none fixed inset-0 -z-10"
        style={{
          background:
            "radial-gradient(ellipse at top right, rgba(59,130,246,0.06), transparent 50%), radial-gradient(ellipse at bottom left, rgba(168,85,247,0.04), transparent 50%)",
        }}
      />

      <ConversationsSidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={setActiveId}
        onNew={newConversation}
      />

      <main className="flex flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-white/[0.04] bg-zinc-950/40 px-6 py-3 backdrop-blur-xl">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-purple-400" />
            <span className="text-sm font-semibold tracking-tight">
              {activeConv?.title ?? "DEMOEMA Copilot"}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <a
              href="/explorer"
              className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-1 text-[11px] font-medium text-zinc-400 transition-all hover:border-blue-400/40 hover:bg-blue-500/10 hover:text-blue-200"
            >
              Data Explorer
            </a>
            <span className="text-[11px] text-zinc-500">Anne Dupont · EdRCF</span>
          </div>
        </header>

        {error && (
          <div className="flex items-start gap-2 border-b border-amber-500/20 bg-amber-500/5 px-6 py-2 text-[12px] text-amber-200">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="flex-1 overflow-y-auto px-6 py-6">
          {!activeConv || activeConv.messages.length === 0 ? (
            <EmptyState onPromptClick={sendMessage} />
          ) : (
            <div className="mx-auto flex max-w-3xl flex-col gap-6">
              <AnimatePresence>
                {activeConv.messages.map((m) => (
                  <ChatMessage
                    key={m.id}
                    message={m}
                    onCardView={(siren) => {
                      window.location.href = `/explorer?siren=${siren}`;
                    }}
                    onCardSave={(siren) => console.log("Save", siren)}
                    onCardCompare={(siren) => console.log("Compare", siren)}
                    onQuickReply={sendMessage}
                  />
                ))}
              </AnimatePresence>
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <div className="border-t border-white/[0.04] bg-zinc-950/40 px-6 py-4 backdrop-blur-xl">
          <div className="mx-auto max-w-3xl">
            <ChatInput
              onSubmit={sendMessage}
              suggestions={
                activeConv?.messages.length && !streaming
                  ? ["Affiner par dept", "Compare top 3", "DD compliance"]
                  : []
              }
              disabled={streaming}
            />
          </div>
        </div>
      </main>
    </div>
  );
}

function EmptyState({ onPromptClick }: { onPromptClick: (p: string) => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto flex h-full max-w-2xl flex-col items-center justify-center text-center"
    >
      <div className="relative mb-6">
        <div className="absolute inset-0 rounded-full bg-gradient-to-br from-purple-500/30 to-blue-500/30 blur-2xl" />
        <div className="relative flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-purple-500 to-blue-500 shadow-[0_0_32px_rgba(168,85,247,0.5)]">
          <Sparkles className="h-8 w-8 text-white" />
        </div>
      </div>

      <h1 className="font-mono text-3xl font-bold tracking-tight text-zinc-100">
        Bonjour Anne ☕
      </h1>
      <p className="mt-2 max-w-md text-sm text-zinc-400">
        Pose une question sur tes cibles M&A. Réponses ancrées sur les 13 tables gold
        + presse temps réel — DeepSeek + datalake DEMOEMA.
      </p>

      <div className="mt-8 grid w-full grid-cols-1 gap-2 sm:grid-cols-2">
        {STARTER_PROMPTS.map((p, i) => (
          <motion.button
            key={i}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 * i }}
            onClick={() => onPromptClick(p)}
            className="rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-3 text-left text-sm text-zinc-300 transition-all hover:border-blue-400/30 hover:bg-blue-500/5 hover:text-zinc-100"
          >
            {p}
          </motion.button>
        ))}
      </div>
    </motion.div>
  );
}
