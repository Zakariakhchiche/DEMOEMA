"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles, Send, X, Minimize2, Maximize2,
  Terminal, User, Activity, Target, Zap, TrendingUp,
  MessageSquare, Layers, Bot, Database, Copy, Check, Trash2, Keyboard
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

/** Render simple markdown: **bold**, bullet lists, line breaks */
function renderMarkdown(text: string) {
  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];

  lines.forEach((line, i) => {
    const trimmed = line.trim();

    if (trimmed.startsWith("- ") || trimmed.startsWith("• ") || trimmed.startsWith("* ")) {
      const content = trimmed.slice(2);
      elements.push(
        <div key={i} className="flex gap-2 items-start ml-2 my-0.5">
          <span className="text-indigo-400 mt-0.5 shrink-0">&bull;</span>
          <span>{renderInline(content)}</span>
        </div>
      );
    } else if (trimmed.startsWith("# ")) {
      elements.push(
        <div key={i} className="font-black text-white text-sm uppercase tracking-widest mt-2 mb-1">
          {renderInline(trimmed.slice(2))}
        </div>
      );
    } else if (trimmed.startsWith("## ")) {
      elements.push(
        <div key={i} className="font-black text-gray-300 text-xs uppercase tracking-widest mt-2 mb-1">
          {renderInline(trimmed.slice(3))}
        </div>
      );
    } else if (trimmed === "") {
      elements.push(<div key={i} className="h-2" />);
    } else {
      elements.push(
        <div key={i} className="my-0.5">{renderInline(trimmed)}</div>
      );
    }
  });

  return <>{elements}</>;
}

/** Render inline markdown: **bold** */
function renderInline(text: string): React.ReactNode {
  const parts: React.ReactNode[] = [];
  const regex = /\*\*(.+?)\*\*/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    parts.push(
      <span key={match.index} className="font-black text-white">{match[1]}</span>
    );
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length > 0 ? <>{parts}</> : text;
}

// Suggestions contextuelles par page
const SUGGESTIONS: Record<string, string[]> = {
  "/": [
    "Top 5 cibles prioritaires",
    "Fondateurs > 60 ans",
    "Analyse sectorielle",
    "Signaux recents",
  ],
  "/targets": [
    "Cibles score > 65",
    "Entreprises familiales",
    "Rechercher par SIREN",
    "Export pipeline",
  ],
  "/pipeline": [
    "Etat du pipeline",
    "Taux de conversion",
    "Cibles en closing",
    "Prochaines echeances",
  ],
  "/signals": [
    "Signaux haute priorite",
    "Alertes BODACC",
    "Tendances sectorielles",
    "Nouveaux signaux",
  ],
  "/graph": [
    "Chemins d'approche",
    "Connexions cles",
    "Mapping reseau",
    "Noeuds influents",
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

  // Suggestions basees sur la page active
  const currentSuggestions = SUGGESTIONS[pathname] || SUGGESTIONS["/"];

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  // Focus input quand le copilot s'ouvre
  useEffect(() => {
    if (isOpen && !isMinimized) {
      setTimeout(() => inputRef.current?.focus(), 300);
    }
  }, [isOpen, isMinimized]);

  useEffect(() => {
    const handleToggle = () => setIsOpen(prev => !prev);
    window.addEventListener("toggle-copilot", handleToggle);
    return () => window.removeEventListener("toggle-copilot", handleToggle);
  }, []);

  // Raccourci clavier Ctrl+J
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "j") {
        e.preventDefault();
        setIsOpen(prev => !prev);
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleCopy = useCallback((content: string, id: string) => {
    navigator.clipboard.writeText(content);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }, []);

  const handleClear = useCallback(() => {
    setMessages([]);
  }, []);

  const handleSend = async (e?: React.FormEvent, directValue?: string) => {
    if (e) e.preventDefault();
    const query = directValue || input;
    if (!query.trim() || isLoading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: query,
      timestamp: Date.now(),
    };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    const assistantId = (Date.now() + 1).toString();
    // Add empty assistant message immediately for streaming display
    setMessages(prev => [...prev, {
      id: assistantId,
      role: "assistant",
      content: "",
      timestamp: Date.now(),
    }]);

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
              setMessages(prev => prev.map(m =>
                m.id === assistantId
                  ? { ...m, content: m.content + event.chunk }
                  : m
              ));
            }
            if (event.done) {
              source = event.source;
              if (event.targets_updated) {
                window.dispatchEvent(new CustomEvent("targets-updated"));
                if (event.targets_count) {
                  setMessages(prev => prev.map(m =>
                    m.id === assistantId ? { ...m, targets_count: event.targets_count } : m
                  ));
                }
              }
            }
          } catch {
            // ignore malformed SSE line
          }
        }
      }

      // Set final source badge
      if (source) {
        setMessages(prev => prev.map(m =>
          m.id === assistantId ? { ...m, source: source as Message["source"] } : m
        ));
      }
    } catch (err) {
      console.error(err);
      // Fallback: try non-streaming endpoint
      try {
        const res = await fetch(`/api/copilot/query?q=${encodeURIComponent(query)}`);
        const data = await res.json();
        if (data.targets_updated) {
          window.dispatchEvent(new CustomEvent("targets-updated"));
        }
        setMessages(prev => prev.map(m =>
          m.id === assistantId
            ? { ...m, content: data.response || "Erreur de connexion.", source: data.source }
            : m
        ));
      } catch {
        setMessages(prev => prev.map(m =>
          m.id === assistantId
            ? { ...m, content: "ERREUR DE CONNEXION: Impossible de joindre le serveur Origin." }
            : m
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
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-4 sm:bottom-8 sm:right-8 w-14 h-14 sm:w-16 sm:h-16 rounded-2xl sm:rounded-[2rem] bg-indigo-600 text-white shadow-[0_20px_50px_rgba(79,70,229,0.4)] z-[50] flex items-center justify-center border border-white/20 group"
      >
        {isOpen ? <X size={22} /> : <MessageSquare size={22} className="group-hover:rotate-12 transition-transform" />}
        {!isOpen && messages.length > 0 && (
           <div className="absolute -top-2 -right-2 min-w-5 h-5 px-1 bg-emerald-500 rounded-full border-2 border-[#050505] flex items-center justify-center">
             <span className="text-[9px] font-black text-white">{messages.length}</span>
           </div>
        )}
        {!isOpen && messages.length === 0 && (
           <div className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-emerald-500 rounded-full border-2 border-[#050505] animate-pulse" />
        )}
      </motion.button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            className={`
              fixed z-[100] bg-[#0A0A0A]/95 lg:backdrop-blur-3xl border border-white/10 shadow-[0_30px_100px_rgba(0,0,0,0.8)] flex flex-col overflow-hidden
              ${isMinimized
                ? "bottom-32 right-4 sm:right-8 w-72 sm:w-80 h-20 rounded-[2rem] sm:rounded-[3rem]"
                : "bottom-4 right-4 left-4 sm:left-auto sm:bottom-32 sm:right-8 sm:w-[420px] lg:w-[450px] h-[calc(100vh-6rem)] sm:h-[600px] lg:h-[650px] rounded-2xl sm:rounded-[3rem]"
              }
              transition-all duration-500 ease-in-out
            `}
          >
            {/* Header */}
            <div className="px-4 py-3 border-b border-white/5 flex items-center justify-between bg-white/[0.02] shrink-0">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-8 h-8 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0">
                  <Sparkles size={16} />
                </div>
                <div className="min-w-0">
                   <h3 className="text-xs font-black text-white uppercase tracking-widest leading-none mb-0.5 truncate">Copilot Origin</h3>
                   <div className="flex items-center gap-1.5">
                      <div className="w-1 h-1 rounded-full bg-emerald-500 animate-pulse" />
                      <span className="text-[7px] font-black text-emerald-500/60 uppercase tracking-widest">Actif</span>
                      <span className="text-[7px] text-gray-700 mx-0.5">|</span>
                      <span className="text-[7px] font-bold text-gray-600 uppercase tracking-wider">Ctrl+J</span>
                   </div>
                </div>
              </div>
              <div className="flex items-center gap-1">
                {messages.length > 0 && (
                  <button
                    onClick={handleClear}
                    className="p-1.5 rounded-lg bg-white/5 text-gray-500 hover:text-rose-400 transition-colors"
                    title="Effacer la conversation"
                  >
                    <Trash2 size={14} />
                  </button>
                )}
                <button
                  onClick={() => setIsMinimized(!isMinimized)}
                  className="p-1.5 rounded-lg bg-white/5 text-gray-400 hover:text-white transition-colors"
                >
                  {isMinimized ? <Maximize2 size={14} /> : <Minimize2 size={14} />}
                </button>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-1.5 rounded-lg bg-white/5 text-gray-400 hover:text-white transition-colors"
                >
                  <X size={14} />
                </button>
              </div>
            </div>

            {/* Chat Area */}
            {!isMinimized && (
              <>
                <div
                  ref={scrollRef}
                  className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar"
                >
                  {messages.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-center px-4">
                       <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mb-4">
                         <Target size={28} className="text-indigo-400" />
                       </div>
                       <p className="text-xs font-black text-white uppercase tracking-[0.15em] mb-1.5">Intelligence Origin</p>
                       <p className="text-[10px] text-gray-500 leading-relaxed mb-6 max-w-[260px]">
                          Posez une question sur les cibles, les signaux, le pipeline ou le reseau.
                       </p>

                       {/* Suggestions grille -- toujours visibles */}
                       <div className="grid grid-cols-2 gap-2 w-full max-w-[300px]">
                          {currentSuggestions.map(s => (
                            <button
                              key={s}
                              onClick={() => {
                                setInput(s);
                                handleSend(undefined, s);
                              }}
                              className="px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 text-[10px] font-bold text-gray-400 hover:bg-indigo-500/10 hover:text-indigo-400 hover:border-indigo-500/20 transition-all active:scale-95 text-left leading-tight"
                            >
                              {s}
                            </button>
                          ))}
                       </div>
                    </div>
                  ) : (
                    messages.map((m) => (
                      <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        key={m.id}
                        className={`flex gap-3 ${m.role === "user" ? "flex-row-reverse" : ""}`}
                      >
                        <div className={`w-7 h-7 rounded-lg shrink-0 flex items-center justify-center border
                          ${m.role === "user"
                            ? "bg-white/5 border-white/10 text-gray-400"
                            : "bg-indigo-500/10 border-indigo-500/20 text-indigo-400"}
                        `}>
                          {m.role === "user" ? <User size={14} /> : <Sparkles size={14} />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className={`rounded-2xl p-3 text-[13px] leading-relaxed
                            ${m.role === "user"
                              ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/10 rounded-tr-none ml-8"
                              : "bg-white/[0.03] border border-white/10 text-gray-300 shadow-xl rounded-tl-none mr-4"}
                          `}>
                            {m.role === "assistant" ? renderMarkdown(m.content) : m.content}
                          </div>

                          {m.role === "assistant" && m.targets_count && (
                            <button
                              onClick={() => { setIsOpen(false); router.push("/targets"); }}
                              className="mt-2 mr-4 w-full flex items-center justify-between gap-2 px-3 py-2.5 rounded-xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-300 hover:bg-indigo-600/30 hover:border-indigo-400/40 transition-all active:scale-[0.98] group"
                            >
                              <div className="flex items-center gap-2">
                                <Database size={13} className="shrink-0 text-indigo-400" />
                                <span className="text-[11px] font-bold">
                                  Voir les {m.targets_count} entreprises trouvées
                                </span>
                              </div>
                              <span className="text-[10px] text-indigo-400 group-hover:translate-x-0.5 transition-transform">→</span>
                            </button>
                          )}

                          <div className={`flex items-center gap-2 mt-1.5 px-1 ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                            <span className="text-[8px] opacity-30 font-bold uppercase tracking-widest">
                              {new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                            {m.role === "assistant" && m.source && (
                              <span className={`text-[7px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded border
                                ${m.source === "claude-ai"
                                  ? "bg-purple-500/10 text-purple-400 border-purple-500/10"
                                  : "bg-emerald-500/10 text-emerald-400 border-emerald-500/10"}
                              `}>
                                {m.source === "claude-ai" ? "IA" : "Base"}
                              </span>
                            )}
                            {m.role === "assistant" && (
                              <button
                                onClick={() => handleCopy(m.content, m.id)}
                                className="text-gray-600 hover:text-white transition-colors p-0.5"
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
                  {isLoading && (
                    <div className="flex gap-3">
                      <div className="w-7 h-7 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                         <Sparkles size={14} className="animate-spin" />
                      </div>
                      <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-3 flex gap-1 items-center">
                         <div className="w-1 h-1 bg-indigo-500 rounded-full animate-bounce [animation-delay:-0.3s]" />
                         <div className="w-1 h-1 bg-indigo-500 rounded-full animate-bounce [animation-delay:-0.15s]" />
                         <div className="w-1 h-1 bg-indigo-500 rounded-full animate-bounce" />
                      </div>
                    </div>
                  )}
                </div>

                {/* Suggestions inline -- apres premiers messages */}
                {messages.length > 0 && messages.length < 4 && !isLoading && (
                   <div className="px-4 py-2 flex flex-wrap gap-1.5 border-t border-white/5">
                      {currentSuggestions.slice(0, 3).map(s => (
                        <button
                          key={s}
                          onClick={() => {
                            setInput(s);
                            handleSend(undefined, s);
                          }}
                          className="px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-[9px] font-bold text-gray-500 hover:bg-indigo-500/10 hover:text-indigo-400 hover:border-indigo-500/20 transition-all active:scale-95"
                        >
                          {s}
                        </button>
                      ))}
                   </div>
                )}

                {/* Input Area */}
                <div className="p-3 sm:p-4 bg-white/[0.02] border-t border-white/10 shrink-0">
                  <form
                    onSubmit={handleSend}
                    className="relative"
                  >
                    <textarea
                      ref={inputRef}
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          handleSend();
                        }
                      }}
                      placeholder="Posez votre question..."
                      rows={1}
                      className="w-full bg-white/[0.05] border border-white/10 rounded-xl py-3 pl-4 pr-12 text-sm text-white placeholder-gray-600 outline-none focus:border-indigo-500/50 transition-all resize-none"
                    />
                    <button
                      type="submit"
                      disabled={!input.trim() || isLoading}
                      className={`absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-lg flex items-center justify-center transition-all
                        ${input.trim() && !isLoading ? "bg-indigo-600 text-white shadow-lg" : "bg-white/5 text-gray-600"}
                      `}
                    >
                      <Send size={16} />
                    </button>
                  </form>
                </div>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
