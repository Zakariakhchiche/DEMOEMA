"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles } from "lucide-react";
import { ChatMessage } from "@/components/copilot/ChatMessage";
import { ChatInput } from "@/components/copilot/ChatInput";
import { ConversationsSidebar } from "@/components/copilot/ConversationsSidebar";
import { mockCibles } from "@/lib/mock/cibles";
import type { ChatMessage as Msg, Conversation, Cible } from "@/lib/types/dem";

const STARTER_PROMPTS = [
  "Top cibles M&A chimie spé IDF avec CA > 20M€",
  "Compare Acme Industries et Beta Pharma sur 5 critères",
  "DD compliance complet sur Beta Pharma Holding",
  "Dirigeants 60+ avec holding patrimoniale dans le Var",
  "Sociétés cotées avec OPA récente",
];

const SUGGESTED_REPLIES = (lastMessage?: Msg): { label: string; prompt: string }[] => {
  if (!lastMessage?.cards?.length) return [];
  return [
    { label: "Affiner: Score >= 70", prompt: "Filtre uniquement Score >= 70" },
    { label: "Sans red flags", prompt: "Exclure les cibles avec red flags compliance" },
    { label: "Top 10 dirigeants", prompt: "Donne-moi les top 10 dirigeants de cette liste" },
    { label: "Compare top 3", prompt: "Compare les 3 premières cibles sur 5 critères" },
    { label: "Export en watchlist", prompt: "Sauve ces résultats dans une nouvelle watchlist" },
  ];
};

/**
 * Mock AI response generator — simule streaming et retourne des cards mock.
 */
function* mockStreamResponse(prompt: string): Generator<{ chunk: string; done: boolean; cards?: Msg["cards"] }> {
  const lower = prompt.toLowerCase();
  let response = "";
  let cards: Msg["cards"] = [];

  if (/^\d{9}$/.test(prompt)) {
    // SIREN direct
    const target = mockCibles.find((c) => c.siren === prompt) ?? mockCibles[0];
    response = `${target.denomination} détecté.\n\nVoici la fiche synthèse :`;
    cards = [{ type: "cible", payload: target }];
  } else if (/compare/i.test(lower)) {
    response = `Comparaison de 2 cibles M&A demandée. Voici les fiches détaillées :`;
    cards = mockCibles.slice(0, 2).map((c) => ({ type: "cible", payload: c }));
  } else if (/dd|compliance|red flag/i.test(lower)) {
    response = `Due diligence compliance lancée. Aucun red flag majeur détecté sur Acme Industries SAS. Liste des sources auditées : OpenSanctions, AMF, ICIJ Offshore, BODACC procédures, gels avoirs.`;
    cards = [{ type: "cible", payload: mockCibles[0] }];
  } else if (/cible|target|m&a/i.test(lower) || /score/i.test(lower)) {
    response = `J'ai trouvé ${mockCibles.length} cibles correspondant à tes critères. Voici les ${Math.min(5, mockCibles.length)} premières par score décroissant :`;
    cards = mockCibles
      .sort((a, b) => b.pro_ma_score - a.pro_ma_score)
      .slice(0, 5)
      .map((c) => ({ type: "cible", payload: c }));
  } else {
    response = `Je peux t'aider à : trouver des cibles M&A, comparer plusieurs entreprises, faire une DD compliance, explorer le réseau dirigeants. Pose-moi une question concrète.`;
  }

  // Stream word-by-word
  const words = response.split(" ");
  let acc = "";
  for (const w of words) {
    acc += (acc ? " " : "") + w;
    yield { chunk: acc, done: false };
  }
  yield { chunk: acc, done: true, cards };
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
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const activeConv = conversations.find((c) => c.id === activeId);

  // Persist conversations
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      localStorage.setItem("demoema_conversations", JSON.stringify(conversations));
    } catch {}
  }, [conversations]);

  // Auto-scroll
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

      // Streaming simulation
      const gen = mockStreamResponse(prompt);
      for await (const _ of [0]) {} // tick
      let lastResult: { chunk: string; done: boolean; cards?: Msg["cards"] } | null = null;
      for (const result of gen) {
        await new Promise((r) => setTimeout(r, 30));
        lastResult = result;
        setConversations((prev) =>
          prev.map((c) =>
            c.id === convId
              ? {
                  ...c,
                  messages: c.messages.map((m) =>
                    m.id === aiMsgId
                      ? {
                          ...m,
                          content: result.chunk,
                          streaming: !result.done,
                          cards: result.done ? result.cards : undefined,
                          quick_replies: result.done
                            ? [
                                { label: "Affiner: Score >= 70", prompt: "Filtre Score >= 70" },
                                { label: "Sans red flags", prompt: "Exclure red flags" },
                                { label: "Compare top 3", prompt: "Compare top 3" },
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
      setStreaming(false);
    },
    [activeId]
  );

  return (
    <div className="flex h-screen overflow-hidden bg-zinc-950 text-zinc-100">
      {/* Aurora background subtle */}
      <div
        className="pointer-events-none fixed inset-0 -z-10"
        style={{
          background:
            "radial-gradient(ellipse at top right, rgba(59,130,246,0.06), transparent 50%), radial-gradient(ellipse at bottom left, rgba(168,85,247,0.04), transparent 50%)",
        }}
      />

      {/* Sidebar */}
      <ConversationsSidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={setActiveId}
        onNew={newConversation}
      />

      {/* Main chat */}
      <main className="flex flex-1 flex-col">
        {/* Header */}
        <header className="flex items-center justify-between border-b border-white/[0.04] bg-zinc-950/40 px-6 py-3 backdrop-blur-xl">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-purple-400" />
            <span className="text-sm font-semibold tracking-tight">
              {activeConv?.title ?? "DEMOEMA Copilot"}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-[11px] text-zinc-500">Anne Dupont · EdRCF</span>
          </div>
        </header>

        {/* Messages */}
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
                    onCardView={(siren) => console.log("View", siren)}
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

        {/* Input */}
        <div className="border-t border-white/[0.04] bg-zinc-950/40 px-6 py-4 backdrop-blur-xl">
          <div className="mx-auto max-w-3xl">
            <ChatInput
              onSubmit={sendMessage}
              suggestions={!activeConv?.messages.length ? STARTER_PROMPTS : []}
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
        Pose une question sur tes cibles M&A. Je query les 27 silvers + 13 golds DEMOEMA
        pour te répondre avec fiches détaillées + sources auditables.
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
