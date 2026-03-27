"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Sparkles, Send, X, Minimize2, Maximize2, 
  Terminal, User, Activity, Target, Zap, TrendingUp,
  MessageSquare, Layers
} from "lucide-react";
import { usePathname } from "next/navigation";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
}

export default function GlobalCopilot() {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const pathname = usePathname();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

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

    try {
      const res = await fetch(`/api/copilot/query?q=${encodeURIComponent(query)}`);
      const data = await res.json();

      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.response,
        timestamp: Date.now(),
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      console.error(err);
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
        className="fixed bottom-8 right-8 w-16 h-16 rounded-[2rem] bg-indigo-600 text-white shadow-[0_20px_50px_rgba(79,70,229,0.4)] z-[50] flex items-center justify-center border border-white/20 group"
      >
        {isOpen ? <X size={24} /> : <MessageSquare size={24} className="group-hover:rotate-12 transition-transform" />}
        {!isOpen && (
           <div className="absolute -top-1 -right-1 w-4 h-4 bg-emerald-500 rounded-full border-2 border-[#050505] animate-pulse" />
        )}
      </motion.button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            className={`
              fixed right-8 z-[100] bg-[#0A0A0A]/95 backdrop-blur-3xl border border-white/10 rounded-[3rem] shadow-[0_30px_100px_rgba(0,0,0,0.8)] flex flex-col overflow-hidden
              ${isMinimized ? "bottom-32 w-80 h-20" : "bottom-32 w-[450px] h-[650px]"}
              transition-all duration-500 ease-in-out
            `}
          >
            {/* Header */}
            <div className="p-6 border-b border-white/5 flex items-center justify-between bg-white/[0.02]">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
                  <Sparkles size={20} />
                </div>
                <div>
                   <h3 className="text-sm font-black text-white uppercase tracking-widest leading-none mb-1">EDRCF Copilot</h3>
                   <div className="flex items-center gap-1.5 ">
                      <div className="w-1 h-1 rounded-full bg-emerald-500 animate-pulse" />
                      <span className="text-[8px] font-black text-emerald-500/60 uppercase tracking-widest">Neural Link Active</span>
                   </div>
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
                  className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar"
                >
                  {messages.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center opacity-40 text-center space-y-4 px-10">
                       <Target size={40} className="text-indigo-400 mb-2" />
                       <p className="text-xs font-black text-white uppercase tracking-[0.2em]">EDRCF Intel Protocol</p>
                       <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest leading-relaxed">
                          Monitoring 2,408 entities. Ready for deep-dive analysis or sector mapping.
                       </p>
                    </div>
                  ) : (
                    messages.map((m) => (
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
                            ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/10 rounded-tr-none" 
                            : "bg-white/[0.03] border border-white/10 text-gray-300 shadow-xl rounded-tl-none"}
                        `}>
                          {m.content}
                          <div className={`text-[9px] mt-2 opacity-40 font-bold uppercase tracking-widest ${m.role === "user" ? "text-right" : ""}`}>
                            {new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </div>
                        </div>
                      </motion.div>
                    ))
                  )}
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

                {/* Suggestions Chips - Show when few messages */}
                {messages.length < 3 && (
                   <div className="px-6 py-2 flex gap-2 overflow-x-auto scrollbar-hide">
                      {[
                        "TOP STRATEGIC TARGETS",
                        "TECHFLOW DEEP-DIVE",
                        "INTENSITY MAPPING",
                        "ANALYZE BIOGRID"
                      ].map(s => (
                        <button 
                          key={s}
                          onClick={() => {
                            setInput(s);
                            handleSend(undefined, s);
                          }}
                          className="whitespace-nowrap px-3 py-1.5 rounded-xl bg-white/5 border border-white/10 text-[10px] font-black uppercase text-gray-400 hover:bg-white/10 hover:text-white transition-all active:scale-95"
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
                        <Terminal size={12} /> Context Awareness: Active
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
