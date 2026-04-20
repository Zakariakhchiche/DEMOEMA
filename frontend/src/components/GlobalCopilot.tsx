"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles, Send, X, Minimize2, ChevronDown,
  User, Target, Database, Copy, Check, Trash2,
  MessageSquare, Zap, ArrowUpRight,
} from "lucide-react";
import { usePathname, useRouter } from "next/navigation";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  source?: "claude-ai" | "rule-based";
  targets_count?: number;
}

function renderInline(text: string): React.ReactNode {
  const parts: React.ReactNode[] = [];
  const regex = /\*\*(.+?)\*\*/g;
  let lastIndex = 0;
  let match;
  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) parts.push(text.slice(lastIndex, match.index));
    parts.push(<span key={match.index} className="font-black text-white">{match[1]}</span>);
    lastIndex = regex.lastIndex;
  }
  if (lastIndex < text.length) parts.push(text.slice(lastIndex));
  return parts.length > 0 ? <>{parts}</> : text;
}

function renderMarkdown(text: string) {
  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];
  lines.forEach((line, i) => {
    const t = line.trim();
    if (t.startsWith("- ") || t.startsWith("• ") || t.startsWith("* ")) {
      elements.push(
        <div key={i} className="flex gap-2 items-start ml-2 my-0.5">
          <span className="text-indigo-400 mt-0.5 shrink-0 text-xs">›</span>
          <span>{renderInline(t.slice(2))}</span>
        </div>
      );
    } else if (t.startsWith("## ")) {
      elements.push(<div key={i} className="font-black text-indigo-300 text-[11px] uppercase tracking-widest mt-3 mb-1">{renderInline(t.slice(3))}</div>);
    } else if (t.startsWith("# ")) {
      elements.push(<div key={i} className="font-black text-white text-sm uppercase tracking-widest mt-2 mb-1">{renderInline(t.slice(2))}</div>);
    } else if (t === "") {
      elements.push(<div key={i} className="h-1.5" />);
    } else {
      elements.push(<div key={i} className="my-0.5 leading-relaxed">{renderInline(t)}</div>);
    }
  });
  return <>{elements}</>;
}

const SUGGESTIONS: Record<string, { icon: React.ReactNode; text: string }[]> = {
  "/": [
    { icon: <Target size={11} />, text: "Top 20 cibles prioritaires" },
    { icon: <Zap size={11} />, text: "Fondateurs > 60 ans" },
    { icon: <Sparkles size={11} />, text: "Analyse sectorielle" },
    { icon: <Database size={11} />, text: "Signaux récents BODACC" },
  ],
  "/targets": [
    { icon: <Target size={11} />, text: "Cibles score > 65" },
    { icon: <Zap size={11} />, text: "Entreprises familiales" },
    { icon: <Database size={11} />, text: "Rechercher par SIREN" },
    { icon: <ArrowUpRight size={11} />, text: "Export pipeline" },
  ],
  "/pipeline": [
    { icon: <Target size={11} />, text: "Etat du pipeline" },
    { icon: <Zap size={11} />, text: "Cibles en closing" },
    { icon: <Database size={11} />, text: "Taux de conversion" },
    { icon: <Sparkles size={11} />, text: "Prochaines échéances" },
  ],
  "/signals": [
    { icon: <Zap size={11} />, text: "Signaux haute priorité" },
    { icon: <Target size={11} />, text: "Alertes BODACC récentes" },
    { icon: <Database size={11} />, text: "Tendances sectorielles" },
    { icon: <Sparkles size={11} />, text: "Nouveaux signaux" },
  ],
  "/graph": [
    { icon: <Target size={11} />, text: "Chemins d'approche clés" },
    { icon: <Database size={11} />, text: "Connexions dirigeants" },
    { icon: <Zap size={11} />, text: "Mapping réseau investisseurs" },
    { icon: <Sparkles size={11} />, text: "Noeuds les plus influents" },
  ],
};

export default function GlobalCopilot() {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const pathname = usePathname();
  const router = useRouter();
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const currentSuggestions = SUGGESTIONS[pathname] || SUGGESTIONS["/"];

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  useEffect(() => {
    if (isOpen && !isMinimized) setTimeout(() => inputRef.current?.focus(), 350);
  }, [isOpen, isMinimized]);

  useEffect(() => {
    const handleToggle = () => setIsOpen(prev => !prev);
    window.addEventListener("toggle-copilot", handleToggle);
    return () => window.removeEventListener("toggle-copilot", handleToggle);
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "j") { e.preventDefault(); setIsOpen(prev => !prev); }
      if (e.key === "Escape" && isOpen) setIsOpen(false);
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  const handleCopy = useCallback((content: string, id: string) => {
    navigator.clipboard.writeText(content);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }, []);

  const handleSend = async (e?: React.FormEvent, directValue?: string) => {
    if (e) e.preventDefault();
    const query = directValue || input;
    if (!query.trim() || isLoading) return;

    const userMsg: Message = { id: Date.now().toString(), role: "user", content: query, timestamp: Date.now() };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    const assistantId = (Date.now() + 1).toString();
    setMessages(prev => [...prev, { id: assistantId, role: "assistant", content: "", timestamp: Date.now() }]);

    try {
      const res = await fetch(`/api/copilot/stream?q=${encodeURIComponent(query)}`);
      if (!res.ok || !res.body) throw new Error("Stream unavailable");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let source: string | undefined;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const event = JSON.parse(line.slice(6));
            if (event.chunk) {
              setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, content: m.content + event.chunk } : m));
            }
            if (event.done) {
              source = event.source;
              if (event.targets_updated) {
                window.dispatchEvent(new CustomEvent("targets-updated"));
                if (event.targets_count) {
                  setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, targets_count: event.targets_count } : m));
                }
              }
            }
          } catch { /* ignore malformed */ }
        }
      }
      if (source) {
        setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, source: source as Message["source"] } : m));
      }
    } catch {
      try {
        const res = await fetch(`/api/copilot/query?q=${encodeURIComponent(query)}`);
        const data = await res.json();
        if (data.targets_updated) window.dispatchEvent(new CustomEvent("targets-updated"));
        setMessages(prev => prev.map(m =>
          m.id === assistantId ? { ...m, content: data.response || "Erreur de connexion.", source: data.source } : m
        ));
      } catch {
        setMessages(prev => prev.map(m =>
          m.id === assistantId ? { ...m, content: "ERREUR DE CONNEXION: Impossible de joindre le serveur EDRCF." } : m
        ));
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      {/* Floating Trigger */}
      <motion.button
        whileHover={{ scale: 1.08 }}
        whileTap={{ scale: 0.94 }}
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-5 right-4 sm:bottom-8 sm:right-8 w-14 h-14 sm:w-16 sm:h-16 rounded-2xl bg-gradient-to-br from-indigo-600 to-indigo-700 text-white shadow-[0_20px_60px_rgba(79,70,229,0.5)] z-50 flex items-center justify-center border border-indigo-500/30 group overflow-hidden"
      >
        {/* Shimmer */}
        <div className="absolute inset-0 bg-gradient-to-br from-white/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
        <AnimatePresence mode="wait">
          {isOpen
            ? <motion.div key="x" initial={{ rotate: -90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ rotate: 90, opacity: 0 }} transition={{ duration: 0.15 }}><X size={22} className="relative z-10" /></motion.div>
            : <motion.div key="msg" initial={{ rotate: 90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ rotate: -90, opacity: 0 }} transition={{ duration: 0.15 }}><MessageSquare size={22} className="relative z-10" /></motion.div>
          }
        </AnimatePresence>
        {!isOpen && messages.length > 0 && (
          <div className="absolute -top-2 -right-2 min-w-5 h-5 px-1 bg-emerald-500 rounded-full border-2 border-[#050505] flex items-center justify-center shadow-lg">
            <span className="text-[9px] font-black text-white">{messages.length}</span>
          </div>
        )}
        {!isOpen && messages.length === 0 && (
          <div className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-emerald-400 rounded-full border-2 border-[#050505] animate-pulse shadow-[0_0_8px_rgba(52,211,153,0.6)]" />
        )}
      </motion.button>

      <AnimatePresence>
        {isOpen && (
          <>
            {/* Mobile backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[90] sm:hidden"
              onClick={() => setIsOpen(false)}
            />

            <motion.div
              initial={{ opacity: 0, y: 30, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 30, scale: 0.96 }}
              transition={{ type: "spring", stiffness: 420, damping: 30 }}
              className={`
                fixed z-[100] flex flex-col overflow-hidden
                bg-[#080810]/98 backdrop-blur-3xl border border-white/8
                shadow-[0_40px_120px_rgba(0,0,0,0.9),0_0_0_1px_rgba(99,102,241,0.1)]
                ${isMinimized
                  ? "bottom-24 sm:bottom-32 right-4 sm:right-8 w-64 sm:w-80 h-16 rounded-2xl"
                  : "inset-x-0 bottom-0 top-0 rounded-none sm:inset-x-auto sm:top-auto sm:bottom-28 sm:right-8 sm:w-full sm:max-w-[440px] sm:h-[min(680px,calc(100dvh-9rem))] sm:rounded-3xl"
                }
              `}
            >
              {/* Top gradient bar */}
              <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-indigo-500/50 to-transparent" />

              {/* Header */}
              <div className={`px-4 py-3.5 border-b border-white/5 flex items-center justify-between shrink-0 ${isMinimized ? "" : "sm:py-4"}`}>
                <div className="flex items-center gap-3 min-w-0">
                  <div className="relative w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-600/30 to-indigo-800/30 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0">
                    <Sparkles size={16} />
                    <div className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 bg-emerald-500 rounded-full border-2 border-[#080810] animate-pulse" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-[11px] font-black text-white uppercase tracking-[0.2em] leading-none mb-1">Copilot EdRCF</h3>
                    <div className="flex items-center gap-2">
                      <span className="text-[8px] font-bold text-emerald-400/70 uppercase tracking-widest">Intelligence M&A</span>
                      <span className="text-[8px] text-gray-700">·</span>
                      <span className="text-[8px] font-bold text-gray-600 uppercase tracking-wider">⌘J</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  {messages.length > 0 && !isMinimized && (
                    <button
                      onClick={() => setMessages([])}
                      className="p-2 rounded-xl bg-white/4 text-gray-600 hover:text-rose-400 hover:bg-rose-500/10 transition-all"
                      title="Effacer"
                    >
                      <Trash2 size={13} />
                    </button>
                  )}
                  <button
                    onClick={() => setIsMinimized(!isMinimized)}
                    className="p-2 rounded-xl bg-white/4 text-gray-500 hover:text-white hover:bg-white/8 transition-all"
                  >
                    {isMinimized ? <ArrowUpRight size={13} /> : <ChevronDown size={13} />}
                  </button>
                  <button
                    onClick={() => setIsOpen(false)}
                    className="p-2 rounded-xl bg-white/4 text-gray-500 hover:text-white hover:bg-white/8 transition-all"
                  >
                    <X size={13} />
                  </button>
                </div>
              </div>

              {/* Body */}
              {!isMinimized && (
                <>
                  {/* Messages */}
                  <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-5 custom-scrollbar">
                    {messages.length === 0 ? (
                      <div className="h-full flex flex-col items-center justify-center text-center px-2">
                        <div className="relative w-16 h-16 rounded-3xl bg-gradient-to-br from-indigo-600/20 to-indigo-900/20 border border-indigo-500/20 flex items-center justify-center mb-5">
                          <Target size={30} className="text-indigo-400" />
                          <div className="absolute inset-0 rounded-3xl bg-indigo-500/5 animate-pulse" />
                        </div>
                        <p className="text-[13px] font-black text-white uppercase tracking-[0.15em] mb-2">Intelligence EDRCF</p>
                        <p className="text-[11px] text-gray-500 leading-relaxed mb-6 max-w-[280px]">
                          Interrogez vos 87 000+ cibles M&A, les signaux BODACC, le pipeline ou le réseau d'acteurs.
                        </p>
                        <div className="grid grid-cols-2 gap-2 w-full max-w-[340px]">
                          {currentSuggestions.map((s) => (
                            <button
                              key={s.text}
                              onClick={() => handleSend(undefined, s.text)}
                              className="flex items-center gap-2 px-3 py-2.5 rounded-xl bg-white/[0.03] border border-white/8 text-[10px] font-bold text-gray-400 hover:bg-indigo-500/10 hover:text-indigo-300 hover:border-indigo-500/20 transition-all active:scale-95 text-left leading-tight group"
                            >
                              <span className="text-gray-600 group-hover:text-indigo-400 transition-colors shrink-0">{s.icon}</span>
                              <span>{s.text}</span>
                            </button>
                          ))}
                        </div>
                      </div>
                    ) : (
                      messages.map((m) => (
                        <motion.div
                          initial={{ opacity: 0, y: 8 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ duration: 0.2 }}
                          key={m.id}
                          className={`flex gap-3 ${m.role === "user" ? "flex-row-reverse" : ""}`}
                        >
                          {/* Avatar */}
                          <div className={`w-7 h-7 rounded-xl shrink-0 flex items-center justify-center border
                            ${m.role === "user"
                              ? "bg-indigo-600/20 border-indigo-500/30 text-indigo-400"
                              : "bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border-indigo-500/20 text-indigo-300"}
                          `}>
                            {m.role === "user" ? <User size={13} /> : <Sparkles size={13} />}
                          </div>

                          {/* Bubble */}
                          <div className="flex-1 min-w-0">
                            <div className={`rounded-2xl p-3.5 text-[13px]
                              ${m.role === "user"
                                ? "bg-gradient-to-br from-indigo-600 to-indigo-700 text-white shadow-lg shadow-indigo-500/15 rounded-tr-none ml-10"
                                : "bg-gradient-to-br from-white/[0.04] to-white/[0.02] border border-white/8 text-gray-300 shadow-xl rounded-tl-none mr-6"}
                            `}>
                              {m.role === "assistant" ? renderMarkdown(m.content) : m.content}
                            </div>

                            {m.role === "assistant" && m.targets_count && (
                              <button
                                onClick={() => { setIsOpen(false); router.push("/targets"); }}
                                className="mt-2 mr-6 w-full flex items-center justify-between gap-2 px-3 py-2.5 rounded-xl bg-indigo-600/15 border border-indigo-500/25 text-indigo-300 hover:bg-indigo-600/25 hover:border-indigo-400/40 transition-all active:scale-[0.98] group"
                              >
                                <div className="flex items-center gap-2">
                                  <Database size={12} className="shrink-0 text-indigo-400" />
                                  <span className="text-[11px] font-bold">Voir les {m.targets_count} entreprises</span>
                                </div>
                                <ArrowUpRight size={12} className="text-indigo-400 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
                              </button>
                            )}

                            <div className={`flex items-center gap-2 mt-1.5 px-1 ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                              <span className="text-[8px] opacity-25 font-bold uppercase tracking-widest">
                                {new Date(m.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                              </span>
                              {m.role === "assistant" && m.source && (
                                <span className={`text-[7px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded-md border
                                  ${m.source === "claude-ai"
                                    ? "bg-purple-500/10 text-purple-400 border-purple-500/15"
                                    : "bg-emerald-500/10 text-emerald-400 border-emerald-500/15"}
                                `}>
                                  {m.source === "claude-ai" ? "Claude AI" : "Règle"}
                                </span>
                              )}
                              {m.role === "assistant" && m.content && (
                                <button
                                  onClick={() => handleCopy(m.content, m.id)}
                                  className="text-gray-700 hover:text-gray-300 transition-colors p-0.5"
                                  title="Copier"
                                >
                                  {copiedId === m.id ? <Check size={11} className="text-emerald-400" /> : <Copy size={11} />}
                                </button>
                              )}
                            </div>
                          </div>
                        </motion.div>
                      ))
                    )}

                    {/* Loading dots */}
                    {isLoading && (
                      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-3">
                        <div className="w-7 h-7 rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/20 flex items-center justify-center text-indigo-300 shrink-0">
                          <Sparkles size={13} className="animate-spin" />
                        </div>
                        <div className="bg-white/[0.03] border border-white/8 rounded-2xl rounded-tl-none px-4 py-3.5 flex gap-1.5 items-center">
                          <div className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce [animation-delay:-0.32s]" />
                          <div className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce [animation-delay:-0.16s]" />
                          <div className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" />
                        </div>
                      </motion.div>
                    )}
                  </div>

                  {/* Quick suggestions after messages */}
                  {messages.length > 0 && messages.length < 5 && !isLoading && (
                    <div className="px-4 py-2 flex gap-1.5 flex-wrap border-t border-white/5 bg-white/[0.01]">
                      {currentSuggestions.slice(0, 3).map(s => (
                        <button
                          key={s.text}
                          onClick={() => handleSend(undefined, s.text)}
                          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/4 border border-white/8 text-[9px] font-bold text-gray-500 hover:bg-indigo-500/10 hover:text-indigo-400 hover:border-indigo-500/20 transition-all active:scale-95"
                        >
                          <span className="text-gray-600">{s.icon}</span>
                          {s.text}
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Input */}
                  <div className="p-3 sm:p-4 bg-white/[0.015] border-t border-white/5 shrink-0">
                    <form onSubmit={handleSend} className="relative flex items-end gap-2">
                      <div className="flex-1 relative">
                        <textarea
                          ref={inputRef}
                          value={input}
                          onChange={(e) => {
                            setInput(e.target.value);
                            e.target.style.height = "auto";
                            e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
                          }}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
                          }}
                          placeholder="Posez votre question M&A…"
                          rows={1}
                          className="w-full bg-white/[0.04] border border-white/10 rounded-2xl py-3.5 px-4 text-[13px] text-white placeholder-gray-600 outline-none focus:border-indigo-500/40 focus:bg-white/[0.06] transition-all resize-none leading-relaxed"
                          style={{ minHeight: "48px", maxHeight: "120px" }}
                        />
                      </div>
                      <motion.button
                        whileTap={{ scale: 0.9 }}
                        type="submit"
                        disabled={!input.trim() || isLoading}
                        className={`shrink-0 w-11 h-11 rounded-2xl flex items-center justify-center transition-all shadow-lg
                          ${input.trim() && !isLoading
                            ? "bg-gradient-to-br from-indigo-600 to-indigo-700 text-white shadow-indigo-500/30 hover:from-indigo-500 hover:to-indigo-600"
                            : "bg-white/5 text-gray-600 cursor-not-allowed shadow-none"}
                        `}
                      >
                        <Send size={16} />
                      </motion.button>
                    </form>
                    <p className="text-[8px] text-gray-700 mt-2 text-center font-bold uppercase tracking-widest">
                      Entrée pour envoyer · Maj+Entrée pour saut de ligne
                    </p>
                  </div>
                </>
              )}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
