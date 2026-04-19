"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  ShoppingCart,
  AlertTriangle,
  FileText,
  Plus,
  Edit,
} from "lucide-react"

interface TimelineEvent {
  id: string
  date: string
  type: "VENTE" | "PROCOL" | "DEPOT" | "CREATION" | "MODIFICATION"
  title: string
  description?: string
  severity?: "high" | "medium" | "low"
}

interface Props {
  events: TimelineEvent[]
  loading?: boolean
}

const TYPE_CONFIG = {
  VENTE: {
    color: "#f59e0b",
    bg: "#f59e0b22",
    border: "#f59e0b44",
    label: "Vente",
    Icon: ShoppingCart,
  },
  PROCOL: {
    color: "#f43f5e",
    bg: "#f43f5e22",
    border: "#f43f5e44",
    label: "Proc. Collective",
    Icon: AlertTriangle,
  },
  DEPOT: {
    color: "#818cf8",
    bg: "#818cf822",
    border: "#818cf844",
    label: "Dépôt",
    Icon: FileText,
  },
  CREATION: {
    color: "#10b981",
    bg: "#10b98122",
    border: "#10b98144",
    label: "Création",
    Icon: Plus,
  },
  MODIFICATION: {
    color: "#9ca3af",
    bg: "#9ca3af22",
    border: "#9ca3af44",
    label: "Modification",
    Icon: Edit,
  },
} as const

const SEVERITY_BADGE = {
  high: { color: "#f43f5e", bg: "#f43f5e22", label: "Critique" },
  medium: { color: "#f59e0b", bg: "#f59e0b22", label: "Modéré" },
  low: { color: "#10b981", bg: "#10b98122", label: "Faible" },
} as const

function formatDateFr(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString("fr-FR", {
    day: "numeric",
    month: "short",
    year: "numeric",
  })
}

function SkeletonItem({ index }: { index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: index * 0.1 }}
      className="flex gap-4"
    >
      <div className="flex flex-col items-center">
        <div className="h-8 w-8 animate-pulse rounded-full bg-white/10" />
        <div className="mt-2 w-px flex-1 bg-white/5" />
      </div>
      <div className="mb-6 flex-1 space-y-2 pb-1">
        <div className="h-3 w-24 animate-pulse rounded bg-white/10" />
        <div className="h-4 w-48 animate-pulse rounded bg-white/10" />
        <div className="h-3 w-full animate-pulse rounded bg-white/5" />
      </div>
    </motion.div>
  )
}

function EventItem({ event, index }: { event: TimelineEvent; index: number }) {
  const [expanded, setExpanded] = useState(false)
  const config = TYPE_CONFIG[event.type]
  const { Icon } = config
  const severityConfig = event.severity ? SEVERITY_BADGE[event.severity] : null

  return (
    <motion.div
      initial={{ opacity: 0, x: -16 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.08, duration: 0.35, ease: "easeOut" }}
      className="flex gap-4"
    >
      <div className="flex flex-col items-center">
        <motion.div
          whileHover={{ scale: 1.1 }}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full"
          style={{
            background: config.bg,
            border: `1.5px solid ${config.border}`,
            boxShadow: `0 0 10px ${config.color}33`,
          }}
        >
          <Icon size={14} style={{ color: config.color }} />
        </motion.div>
        <div
          className="mt-1 w-px flex-1"
          style={{ background: "linear-gradient(to bottom, #ffffff18, transparent)" }}
        />
      </div>

      <div className="mb-5 flex-1 pb-1">
        <button
          className="w-full cursor-pointer text-left"
          onClick={() => setExpanded((v) => !v)}
        >
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[10px] font-medium text-gray-500">
              {formatDateFr(event.date)}
            </span>
            <span
              className="rounded-full px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
              style={{
                color: config.color,
                background: config.bg,
                border: `1px solid ${config.border}`,
              }}
            >
              {config.label}
            </span>
            {severityConfig && (
              <span
                className="rounded-full px-1.5 py-0.5 text-[10px] font-medium"
                style={{
                  color: severityConfig.color,
                  background: severityConfig.bg,
                }}
              >
                {severityConfig.label}
              </span>
            )}
          </div>

          <p className="mt-1 text-sm font-medium text-[#ededed]">{event.title}</p>
        </button>

        <AnimatePresence>
          {expanded && event.description && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25, ease: "easeInOut" }}
              className="overflow-hidden"
            >
              <p className="mt-2 rounded-lg border border-white/5 bg-white/5 px-3 py-2 text-xs leading-relaxed text-gray-400">
                {event.description}
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}

export default function EventTimeline({ events, loading = false }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="rounded-2xl border border-indigo-500/20 bg-white/5 p-6 backdrop-blur-md"
      style={{ background: "rgba(99,102,241,0.03)" }}
    >
      <div className="mb-5 flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-widest text-indigo-400">
          Historique BODACC
        </span>
        {!loading && (
          <span className="rounded-full border border-indigo-500/30 bg-indigo-500/10 px-2 py-0.5 text-xs text-indigo-300">
            {events.length} événement{events.length !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {loading ? (
        <div>
          {[0, 1, 2].map((i) => (
            <SkeletonItem key={i} index={i} />
          ))}
        </div>
      ) : events.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3 }}
          className="flex flex-col items-center gap-3 py-10 text-center"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-full border border-white/10 bg-white/5">
            <FileText size={20} className="text-gray-600" />
          </div>
          <p className="text-sm text-gray-500">Aucun événement BODACC trouvé</p>
          <p className="text-xs text-gray-600">
            Les événements apparaîtront ici une fois chargés
          </p>
        </motion.div>
      ) : (
        <div>
          {events.map((event, index) => (
            <EventItem key={event.id} event={event} index={index} />
          ))}
        </div>
      )}
    </motion.div>
  )
}
