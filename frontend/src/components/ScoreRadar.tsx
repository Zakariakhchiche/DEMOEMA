"use client"

import { motion } from "framer-motion"
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
} from "recharts"

interface Props {
  scores: {
    effectif: number
    anciennete: number
    secteur: number
    bodacc: number
    gouvernance: number
    financier: number
  }
  globalScore: number
  size?: number
}

const AXES = [
  { key: "effectif", label: "Effectif" },
  { key: "anciennete", label: "Ancienneté" },
  { key: "secteur", label: "Secteur M&A" },
  { key: "bodacc", label: "Signal BODACC" },
  { key: "gouvernance", label: "Gouvernance" },
  { key: "financier", label: "Financier" },
] as const

function getScoreColor(score: number): string {
  if (score >= 65) return "#22c55e"
  if (score >= 45) return "#818cf8"
  if (score >= 25) return "#f59e0b"
  return "#f43f5e"
}

function getScoreLabel(score: number): string {
  if (score >= 65) return "Fort potentiel"
  if (score >= 45) return "Potentiel modéré"
  if (score >= 25) return "Potentiel faible"
  return "Non qualifié"
}

export default function ScoreRadar({ scores, globalScore, size = 320 }: Props) {
  const data = AXES.map(({ key, label }) => ({
    subject: label,
    value: scores[key],
    fullMark: 100,
  }))

  const scoreColor = getScoreColor(globalScore)
  const scoreLabel = getScoreLabel(globalScore)

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="relative flex flex-col items-center gap-4 rounded-2xl border border-indigo-500/30 bg-white/5 p-6 backdrop-blur-md"
      style={{ background: "rgba(99,102,241,0.04)" }}
    >
      <div className="flex w-full items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-widest text-indigo-400">
          Score M&A
        </span>
        <span
          className="rounded-full px-2 py-0.5 text-xs font-medium"
          style={{
            color: scoreColor,
            background: scoreColor + "22",
            border: `1px solid ${scoreColor}44`,
          }}
        >
          {scoreLabel}
        </span>
      </div>

      <div className="relative" style={{ width: size, height: size }}>
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={data} margin={{ top: 20, right: 30, bottom: 20, left: 30 }}>
            <PolarGrid
              gridType="polygon"
              stroke="#ffffff10"
              strokeWidth={1}
            />
            <PolarAngleAxis
              dataKey="subject"
              tick={{
                fill: "#9ca3af",
                fontSize: 11,
                fontFamily: "Inter, Outfit, sans-serif",
              }}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                background: "#0a0a1a",
                border: "1px solid #6366f144",
                borderRadius: "8px",
                color: "#ededed",
                fontSize: 12,
              }}
              itemStyle={{ color: "#818cf8" }}
              formatter={(value) => [`${value}/100`, "Score"]}
            />
            <Radar
              name="Score"
              dataKey="value"
              stroke="#818cf8"
              strokeWidth={2}
              fill="#6366f1"
              fillOpacity={0.15}
              dot={{ r: 3, fill: "#818cf8", strokeWidth: 0 }}
              activeDot={{ r: 5, fill: "#a5b4fc", strokeWidth: 0 }}
            />
          </RadarChart>
        </ResponsiveContainer>

        <div
          className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center"
          style={{ zIndex: 10 }}
        >
          <motion.span
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.4 }}
            className="text-4xl font-bold tabular-nums"
            style={{ color: scoreColor, textShadow: `0 0 24px ${scoreColor}66` }}
          >
            {globalScore}
          </motion.span>
          <span className="mt-0.5 text-xs text-gray-500">/100</span>
        </div>
      </div>

      <div className="grid w-full grid-cols-3 gap-2">
        {AXES.map(({ key, label }) => (
          <div
            key={key}
            className="flex flex-col items-center rounded-lg border border-white/5 bg-white/5 px-2 py-1.5"
          >
            <span className="text-[10px] text-gray-500">{label}</span>
            <span
              className="text-sm font-semibold tabular-nums"
              style={{ color: getScoreColor(scores[key]) }}
            >
              {scores[key]}
            </span>
          </div>
        ))}
      </div>
    </motion.div>
  )
}
