"use client";

import { motion } from "framer-motion";
import { Plus, MessageSquare, Pin, Search, Settings, Sparkles } from "lucide-react";
import type { Conversation } from "@/lib/types/dem";
import { cn } from "@/lib/utils";

interface Props {
  conversations: Conversation[];
  activeId?: string;
  onSelect: (id: string) => void;
  onNew: () => void;
  className?: string;
}

function groupByDate(conversations: Conversation[]) {
  const now = Date.now();
  const today: Conversation[] = [];
  const week: Conversation[] = [];
  const month: Conversation[] = [];
  const older: Conversation[] = [];

  for (const c of conversations) {
    const age = now - c.updated_at;
    if (age < 24 * 3600 * 1000) today.push(c);
    else if (age < 7 * 24 * 3600 * 1000) week.push(c);
    else if (age < 30 * 24 * 3600 * 1000) month.push(c);
    else older.push(c);
  }

  return { today, week, month, older };
}

export function ConversationsSidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  className,
}: Props) {
  const groups = groupByDate(conversations);
  const pinned = conversations.filter((c) => c.pinned);

  const Section = ({ title, items }: { title: string; items: Conversation[] }) => {
    if (!items.length) return null;
    return (
      <div className="space-y-0.5">
        <div className="px-3 pb-1 pt-3 text-[10px] uppercase tracking-wider text-zinc-600">
          {title}
        </div>
        {items.map((c) => (
          <button
            key={c.id}
            onClick={() => onSelect(c.id)}
            className={cn(
              "group flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition-all",
              "hover:bg-white/[0.04]",
              activeId === c.id
                ? "bg-blue-500/10 text-blue-100 ring-1 ring-blue-500/20"
                : "text-zinc-400"
            )}
          >
            {c.pinned ? (
              <Pin className="h-3.5 w-3.5 shrink-0 text-amber-400" />
            ) : (
              <MessageSquare className="h-3.5 w-3.5 shrink-0 text-zinc-500" />
            )}
            <span className="flex-1 truncate text-xs">{c.title}</span>
            {c.messages.length > 0 && (
              <span className="text-[10px] text-zinc-600">{c.messages.length}</span>
            )}
          </button>
        ))}
      </div>
    );
  };

  return (
    <aside
      className={cn(
        "flex w-64 flex-col border-r border-white/[0.04] bg-zinc-950/50 backdrop-blur-xl",
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-white/[0.04] p-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-purple-500 to-blue-500 shadow-[0_0_16px_rgba(168,85,247,0.4)]">
          <Sparkles className="h-4 w-4 text-white" />
        </div>
        <div className="flex-1">
          <div className="text-sm font-semibold text-zinc-100">DEMOEMA</div>
          <div className="text-[10px] uppercase tracking-wider text-zinc-500">
            M&amp;A Copilot
          </div>
        </div>
      </div>

      {/* New conversation */}
      <div className="p-2">
        <motion.button
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.99 }}
          onClick={onNew}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-br from-blue-500/20 to-purple-500/20 px-3 py-2.5 text-sm font-medium text-zinc-100 ring-1 ring-blue-500/20 transition-all hover:from-blue-500/30 hover:to-purple-500/30 hover:ring-blue-400/40"
        >
          <Plus className="h-4 w-4" />
          Nouvelle conversation
          <kbd className="ml-auto rounded border border-white/[0.08] bg-white/[0.04] px-1 py-0 text-[10px] font-mono text-zinc-400">
            ⌘N
          </kbd>
        </motion.button>
      </div>

      {/* Search */}
      <div className="px-2 pb-2">
        <div className="flex items-center gap-2 rounded-lg bg-white/[0.02] px-3 py-1.5 ring-1 ring-white/[0.04] focus-within:ring-blue-500/30">
          <Search className="h-3.5 w-3.5 text-zinc-500" />
          <input
            type="text"
            placeholder="Search..."
            className="w-full bg-transparent text-xs text-zinc-200 placeholder-zinc-600 outline-none"
          />
          <kbd className="rounded border border-white/[0.08] bg-white/[0.02] px-1 py-0 text-[10px] font-mono text-zinc-500">
            ⌘K
          </kbd>
        </div>
      </div>

      {/* Conversations list */}
      <div className="flex-1 overflow-y-auto px-2 pb-2">
        <Section title="Pinned" items={pinned} />
        <Section title="Today" items={groups.today} />
        <Section title="Last 7 days" items={groups.week} />
        <Section title="Last 30 days" items={groups.month} />
        <Section title="Older" items={groups.older} />
      </div>

      {/* Footer */}
      <div className="border-t border-white/[0.04] p-2">
        <button className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs text-zinc-400 transition-all hover:bg-white/[0.04] hover:text-zinc-200">
          <Settings className="h-3.5 w-3.5" />
          Settings
          <span className="ml-auto text-[10px] text-zinc-600">v1.0</span>
        </button>
      </div>
    </aside>
  );
}
