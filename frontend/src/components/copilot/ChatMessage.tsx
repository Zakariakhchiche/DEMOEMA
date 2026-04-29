"use client";

import { motion } from "framer-motion";
import { Sparkles, User } from "lucide-react";
import { TargetCard } from "./TargetCard";
import type { ChatMessage as Msg, Cible } from "@/lib/types/dem";
import { cn } from "@/lib/utils";

interface Props {
  message: Msg;
  onCardView?: (siren: string) => void;
  onCardSave?: (siren: string) => void;
  onCardCompare?: (siren: string) => void;
  onQuickReply?: (prompt: string) => void;
}

export function ChatMessage({ message, onCardView, onCardSave, onCardCompare, onQuickReply }: Props) {
  const isUser = message.role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      className={cn("flex gap-3 group", isUser ? "flex-row-reverse" : "flex-row")}
    >
      {/* Avatar */}
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
          isUser
            ? "bg-zinc-800/80 ring-1 ring-zinc-700"
            : "bg-gradient-to-br from-purple-500/30 via-blue-500/30 to-cyan-500/30 ring-1 ring-purple-400/30"
        )}
      >
        {isUser ? (
          <User className="h-4 w-4 text-zinc-300" />
        ) : (
          <Sparkles
            className={cn(
              "h-4 w-4 text-purple-300",
              message.streaming && "animate-pulse"
            )}
          />
        )}
      </div>

      {/* Message content */}
      <div className={cn("flex max-w-[85%] flex-col gap-3", isUser && "items-end")}>
        {/* Text bubble */}
        <div
          className={cn(
            "rounded-2xl px-4 py-2.5 text-[14px] leading-relaxed",
            isUser
              ? "bg-blue-500/10 text-zinc-100 ring-1 ring-blue-500/20"
              : "bg-zinc-900/40 text-zinc-200 backdrop-blur-xl ring-1 ring-white/[0.06]"
          )}
        >
          {message.content}
          {message.streaming && (
            <span className="ml-1 inline-block h-3.5 w-0.5 animate-pulse bg-purple-300" />
          )}
        </div>

        {/* Cards inline (cibles, dirigeants) */}
        {message.cards && message.cards.length > 0 && (
          <div className="flex w-full max-w-2xl flex-col gap-2">
            {message.cards.map((card, idx) =>
              card.type === "cible" ? (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.05 }}
                >
                  <TargetCard
                    target={card.payload as Cible}
                    onView={() => onCardView?.((card.payload as Cible).siren)}
                    onSave={() => onCardSave?.((card.payload as Cible).siren)}
                    onCompare={() => onCardCompare?.((card.payload as Cible).siren)}
                  />
                </motion.div>
              ) : null
            )}
          </div>
        )}

        {/* Sources */}
        {message.sources && message.sources.length > 0 && (
          <div className="flex flex-wrap gap-1.5 pt-1">
            <span className="text-[10px] uppercase tracking-wider text-zinc-500">Sources :</span>
            {message.sources.map((s, i) => (
              <a
                key={i}
                href={s.url}
                className="inline-flex items-center gap-1 rounded-md bg-white/[0.04] px-1.5 py-0.5 font-mono text-[10px] text-zinc-400 hover:bg-white/[0.08] hover:text-zinc-200"
              >
                {s.label}
              </a>
            ))}
          </div>
        )}

        {/* Quick replies */}
        {message.quick_replies && message.quick_replies.length > 0 && (
          <div className="flex flex-wrap gap-1.5 pt-1">
            {message.quick_replies.map((qr, i) => (
              <button
                key={i}
                onClick={() => onQuickReply?.(qr.prompt)}
                className="rounded-full border border-white/[0.08] bg-white/[0.02] px-3 py-1.5 text-xs text-zinc-300 transition-all hover:border-blue-400/40 hover:bg-blue-500/10 hover:text-blue-200"
              >
                {qr.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}
