"use client";

import { useState, useRef, useEffect } from "react";
import { motion } from "framer-motion";
import { Sparkles, Paperclip, Filter, ArrowUp } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  onSubmit: (prompt: string) => void;
  suggestions?: string[];
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({
  onSubmit,
  suggestions = [],
  disabled = false,
  placeholder = "Pose ta question ou recherche un SIREN...",
}: Props) {
  const [value, setValue] = useState("");
  const taRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    // Auto-resize
    if (taRef.current) {
      taRef.current.style.height = "auto";
      taRef.current.style.height = Math.min(taRef.current.scrollHeight, 200) + "px";
    }
  }, [value]);

  const submit = () => {
    if (!value.trim() || disabled) return;
    onSubmit(value.trim());
    setValue("");
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="space-y-2">
      {/* Suggestions chips */}
      {suggestions.length > 0 && !value && (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-wrap gap-1.5"
        >
          {suggestions.map((s, i) => (
            <button
              key={i}
              onClick={() => onSubmit(s)}
              className="rounded-full border border-white/[0.08] bg-white/[0.02] px-3 py-1 text-xs text-zinc-400 transition-all hover:border-blue-400/40 hover:bg-blue-500/10 hover:text-blue-200"
            >
              {s}
            </button>
          ))}
        </motion.div>
      )}

      {/* Input area */}
      <div
        className={cn(
          "relative rounded-2xl bg-zinc-950/60 backdrop-blur-2xl",
          "border border-white/[0.08] focus-within:border-blue-400/40",
          "shadow-[0_8px_32px_rgba(0,0,0,0.4)]",
          "transition-all duration-300"
        )}
      >
        <textarea
          ref={taRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKey}
          disabled={disabled}
          placeholder={placeholder}
          rows={1}
          className="w-full resize-none bg-transparent px-4 py-3.5 pr-14 text-sm text-zinc-100 placeholder-zinc-500 outline-none disabled:opacity-50"
        />

        {/* Send button */}
        <button
          onClick={submit}
          disabled={disabled || !value.trim()}
          className={cn(
            "absolute bottom-3 right-3 flex h-8 w-8 items-center justify-center rounded-lg transition-all",
            value.trim() && !disabled
              ? "bg-gradient-to-br from-blue-500 to-purple-500 text-white shadow-[0_0_16px_rgba(96,165,250,0.4)] hover:shadow-[0_0_24px_rgba(96,165,250,0.6)]"
              : "bg-white/[0.04] text-zinc-600"
          )}
        >
          <ArrowUp className="h-4 w-4" />
        </button>

        {/* Bottom actions row */}
        <div className="flex items-center gap-2 border-t border-white/[0.04] px-3 py-2">
          <button
            className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-zinc-500 transition-all hover:bg-white/[0.04] hover:text-zinc-300"
            title="Joindre liste sirens"
          >
            <Paperclip className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Joindre</span>
          </button>
          <button
            className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-zinc-500 transition-all hover:bg-white/[0.04] hover:text-zinc-300"
            title="Filtres"
          >
            <Filter className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Filtres</span>
          </button>
          <div className="ml-auto flex items-center gap-2 text-[10px] text-zinc-500">
            <kbd className="rounded border border-white/[0.08] bg-white/[0.02] px-1.5 py-0.5 font-mono">
              ⌘
            </kbd>
            <kbd className="rounded border border-white/[0.08] bg-white/[0.02] px-1.5 py-0.5 font-mono">
              Enter
            </kbd>
            <span>pour envoyer</span>
          </div>
        </div>
      </div>
    </div>
  );
}
