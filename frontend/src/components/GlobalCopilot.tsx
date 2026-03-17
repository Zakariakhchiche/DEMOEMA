"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Send, Sparkles, MessageSquare, Bot, User, Zap, ChevronRight, Minimize2, Maximize2, Terminal, Info } from "lucide-react";

import { Message } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

export default function GlobalCopilot() {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "assistant",
      content: "Hello! I am your AI M&A Copilot. I have access to your relationship maps, market signals, and pipeline data. How can I assist your origination strategy today?",
      timestamp: new Date().toISOString(),
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  useEffect(() => {
    const handleToggle = () => setIsOpen(true);
    window.addEventListener("toggle-copilot", handleToggle);
    return () => window.removeEventListener("toggle-copilot", handleToggle);
  }, []);

  const handleSend = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/copilot/query?q=${encodeURIComponent(input)}`);
      const data = await response.json();
      
      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.response || "I encountered an error processing that request.",
        timestamp: new Date().toISOString(),
      };
      
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "I'm having trouble connecting to the intelligence engine. Please ensure the backend is running.",
        timestamp: new Date().toISOString(),
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      {/* Trigger Button - Floating or Sidebar integrated */}
      {!isOpen && (
        <motion.button
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          onClick={() => setIsOpen(true)}
          className="fixed bottom-4 right-4 sm:bottom-8 sm:right-8 z-[100] w-12 h-12 sm:w-14 sm:h-14 rounded-xl sm:rounded-2xl bg-indigo-600 text-white shadow-[0_0_30px_rgba(99,102,241,0.5)] flex items-center justify-center hover:bg-indigo-500 transition-all border border-indigo-400 group"
        >
          <Sparkles size={20} className="sm:size-24 group-hover:rotate-12 transition-transform" />
          <div className="absolute -top-1 -right-1 w-3 h-3 sm:w-4 sm:h-4 bg-amber-500 rounded-full border-2 border-[#050505] animate-pulse" />
        </motion.button>
      )}

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ x: "100%", opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: "100%", opacity: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className={`fixed top-0 right-0 sm:top-4 sm:right-4 bottom-0 sm:bottom-4 z-[110] bg-black/80 border-l sm:border border-white/10 backdrop-blur-3xl sm:rounded-[2.5rem] shadow-[0_0_100px_rgba(0,0,0,0.8)] flex flex-col overflow-hidden transition-all duration-300
              ${isMinimized ? "w-20 h-20 overflow-hidden" : "w-full sm:w-96 md:w-[28rem]"}
            `}
          >
            {/* Header */}
            <div className="p-6 border-b border-white/10 flex items-center justify-between bg-white/[0.02]">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                  <Bot size={20} />
                </div>
                <div>
                  <h3 className="text-sm font-black text-white uppercase tracking-widest flex items-center gap-2">
                    Origination Copilot
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  </h3>
                  <p className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Engine: GPT-4o Optimized</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button 
                  onClick={() => setIsMinimized(!isMinimized)}
                  className="p-2 rounded-xl bg-white/5 text-gray-400 hover:text-white transition-colors"
                >
                  {isMinimized ? <Maximize2 size={16} /> : <Minimize2 size={16} />}
                </button>
                <button 
                  onClick={() => setIsOpen(false)}
                  className="p-2 rounded-xl bg-white/5 text-gray-400 hover:text-white transition-colors"
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            {/* Chat Area */}
            {!isMinimized && (
              <>
                <div 
                  ref={scrollRef}
                  className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-hide"
                >
                  {messages.map((m) => (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      key={m.id}
                      className={`flex gap-4 ${m.role === "user" ? "flex-row-reverse" : ""}`}
                    >
                      <div className={`w-8 h-8 rounded-xl shrink-0 flex items-center justify-center border
                        ${m.role === "user" 
                          ? "bg-white/5 border-white/10 text-gray-400" 
                          : "bg-indigo-500/10 border-indigo-500/20 text-indigo-400"}
                      `}>
                        {m.role === "user" ? <User size={16} /> : <Sparkles size={16} />}
                      </div>
                      <div className={`max-w-[80%] rounded-2xl p-4 text-[13px] leading-relaxed
                        ${m.role === "user" 
                          ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/10" 
                          : "bg-white/[0.03] border border-white/10 text-gray-300 shadow-xl"}
                      `}>
                        {m.content}
                        <div className={`text-[9px] mt-2 opacity-40 font-bold uppercase tracking-widest ${m.role === "user" ? "text-right" : ""}`}>
                          {new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </div>
                      </div>
                    </motion.div>
                  ))}
                  {isLoading && (
                    <div className="flex gap-4">
                      <div className="w-8 h-8 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                         <Sparkles size={16} className="animate-spin" />
                      </div>
                      <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-4 flex gap-1 items-center">
                         <div className="w-1 h-1 bg-indigo-500 rounded-full animate-bounce [animation-delay:-0.3s]" />
                         <div className="w-1 h-1 bg-indigo-500 rounded-full animate-bounce [animation-delay:-0.15s]" />
                         <div className="w-1 h-1 bg-indigo-500 rounded-full animate-bounce" />
                      </div>
                    </div>
                  )}
                </div>

                {/* Suggestions */}
                {messages.length < 3 && !isLoading && (
                   <div className="px-6 py-2 flex gap-2 overflow-x-auto scrollbar-hide">
                      {[
                        "Top French targets", 
                        "Industrial signals",
                        "High priority pipeline"
                      ].map(s => (
                        <button 
                          key={s}
                          onClick={() => {
                            setInput(s);
                            // Auto trigger send after a small delay to feel natural
                            setTimeout(() => handleSend(), 100);
                          }}
                          className="whitespace-nowrap px-3 py-1.5 rounded-xl bg-white/5 border border-white/10 text-[10px] font-black uppercase text-gray-400 hover:bg-white/10 hover:text-white transition-all"
                        >
                          {s}
                        </button>
                      ))}
                   </div>
                )}

                {/* Input Area */}
                <div className="p-6 bg-white/[0.02] border-t border-white/10">
                  <form 
                    onSubmit={handleSend}
                    className="relative"
                  >
                    <textarea
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          handleSend();
                        }
                      }}
                      placeholder="Ask the engine anything..."
                      rows={1}
                      className="w-full bg-white/[0.05] border border-white/10 rounded-2xl py-4 pl-4 pr-14 text-sm text-white placeholder-gray-600 outline-none focus:border-indigo-500/50 transition-all resize-none"
                    />
                    <button 
                      type="submit"
                      disabled={!input.trim() || isLoading}
                      className={`absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 rounded-xl flex items-center justify-center transition-all
                        ${input.trim() && !isLoading ? "bg-indigo-600 text-white shadow-lg" : "bg-white/5 text-gray-600"}
                      `}
                    >
                      <Send size={18} />
                    </button>
                  </form>
                  <div className="mt-4 flex items-center justify-between">
                     <div className="flex items-center gap-2 text-[10px] text-gray-600 font-black uppercase tracking-widest">
                        <Terminal size={12} /> Live Path Context: On
                     </div>
                     <div className="flex items-center gap-2 text-[10px] text-gray-600 font-bold">
                        Press ↵ to send
                     </div>
                  </div>
                </div>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
