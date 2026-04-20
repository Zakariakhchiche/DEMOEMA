"use client";

import { useState, useCallback, useMemo } from "react";
import {
  ComposableMap,
  Geographies,
  Geography,
  ZoomableGroup,
  type Geography as GeoType,
} from "react-simple-maps";

const GEO_URL =
  "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements-version-simplifiee.geojson";

interface DeptData {
  dept: string;
  count: number;
  label?: string;
}

interface Props {
  data: DeptData[];
  onSelect?: (dept: string) => void;
  selectedDept?: string;
}

interface TooltipState {
  visible: boolean;
  x: number;
  y: number;
  name: string;
  code: string;
  count: number;
}

function interpolateColor(t: number): string {
  const dark = [30, 27, 75];
  const light = [99, 102, 241];
  const r = Math.round(dark[0] + (light[0] - dark[0]) * t);
  const g = Math.round(dark[1] + (light[1] - dark[1]) * t);
  const b = Math.round(dark[2] + (light[2] - dark[2]) * t);
  return `rgb(${r},${g},${b})`;
}

export default function FranceMap({ data, onSelect, selectedDept }: Props) {
  const [tooltip, setTooltip] = useState<TooltipState>({
    visible: false,
    x: 0,
    y: 0,
    name: "",
    code: "",
    count: 0,
  });
  const [position, setPosition] = useState<{ coordinates: [number, number]; zoom: number }>({
    coordinates: [2.3, 46.8],
    zoom: 1,
  });

  const dataMap = useMemo(() => {
    const map: Record<string, DeptData> = {};
    for (const d of data) {
      map[d.dept] = d;
    }
    return map;
  }, [data]);

  const maxCount = useMemo(() => {
    return Math.max(1, ...data.map((d) => d.count));
  }, [data]);

  const totalCount = useMemo(() => data.reduce((s, d) => s + d.count, 0), [data]);

  const top10 = useMemo(() => {
    return [...data].sort((a, b) => b.count - a.count).slice(0, 10);
  }, [data]);

  const getFillColor = useCallback(
    (code: string) => {
      const d = dataMap[code];
      if (!d) return "#1e1b4b";
      const t = d.count / maxCount;
      return interpolateColor(t);
    },
    [dataMap, maxCount]
  );

  const handleMouseEnter = useCallback(
    (geo: GeoType, evt: React.MouseEvent) => {
      const { code, nom: name } = geo.properties as { code: string; nom: string };
      const d = dataMap[code];
      const rect = (evt.currentTarget as Element)
        .closest("svg")
        ?.getBoundingClientRect();
      const containerRect = (evt.currentTarget as Element)
        .closest("[data-map-container]")
        ?.getBoundingClientRect();
      const refRect = containerRect ?? rect;
      setTooltip({
        visible: true,
        x: evt.clientX - (refRect?.left ?? 0),
        y: evt.clientY - (refRect?.top ?? 0),
        name,
        code,
        count: d?.count ?? 0,
      });
    },
    [dataMap]
  );

  const handleMouseMove = useCallback((evt: React.MouseEvent) => {
    const containerRect = (evt.currentTarget as Element)
      .closest("[data-map-container]")
      ?.getBoundingClientRect();
    if (containerRect) {
      setTooltip((prev) => ({
        ...prev,
        x: evt.clientX - containerRect.left,
        y: evt.clientY - containerRect.top,
      }));
    }
  }, []);

  const handleMouseLeave = useCallback(() => {
    setTooltip((prev) => ({ ...prev, visible: false }));
  }, []);

  const handleClick = useCallback(
    (code: string) => {
      onSelect?.(code);
    },
    [onSelect]
  );

  return (
    <div
      className="w-full flex flex-col lg:flex-row gap-4"
      style={{ fontFamily: "'Inter', 'Outfit', sans-serif" }}
    >
      <div className="flex-1 flex flex-col gap-3">
        <div
          className="rounded-xl border border-white/5 px-4 py-3 flex items-center gap-3"
          style={{
            background: "rgba(99,102,241,0.08)",
            backdropFilter: "blur(12px)",
          }}
        >
          <div>
            <p className="text-xs uppercase tracking-widest" style={{ color: "#6366f1" }}>
              Total cibles
            </p>
            <p className="text-3xl font-bold tabular-nums" style={{ color: "#ededed" }}>
              {totalCount.toLocaleString("fr-FR")}
            </p>
          </div>
          <div className="ml-auto text-xs" style={{ color: "#6b7280" }}>
            {data.length} département{data.length !== 1 ? "s" : ""}
          </div>
        </div>

        <div
          className="relative rounded-xl border border-white/5 overflow-hidden"
          style={{ background: "#020202" }}
          data-map-container=""
        >
          {tooltip.visible && (
            <div
              className="pointer-events-none absolute z-50 rounded-lg border border-white/10 px-3 py-2 text-sm shadow-xl"
              style={{
                left: tooltip.x + 12,
                top: tooltip.y - 40,
                background: "rgba(2,2,2,0.92)",
                backdropFilter: "blur(16px)",
                color: "#ededed",
                minWidth: 140,
              }}
            >
              <p className="font-semibold">{tooltip.name}</p>
              <p className="text-xs mt-0.5" style={{ color: "#6366f1" }}>
                {tooltip.count} cible{tooltip.count !== 1 ? "s" : ""}
              </p>
            </div>
          )}

          <ComposableMap
            projection="geoMercator"
            projectionConfig={{ center: [2.3, 46.5], scale: 2600 }}
            style={{ width: "100%", height: "auto" }}
            height={500}
          >
            <ZoomableGroup
              zoom={position.zoom}
              center={position.coordinates}
              onMoveEnd={(pos: { zoom: number; coordinates: [number, number] }) =>
                setPosition({ zoom: pos.zoom, coordinates: pos.coordinates })
              }
              minZoom={0.8}
              maxZoom={8}
            >
              <Geographies geography={GEO_URL}>
                {({ geographies }: { geographies: GeoType[] }) =>
                  geographies.map((geo) => {
                    const { code } = geo.properties as { code: string; nom: string };
                    const isSelected = code === selectedDept;
                    return (
                      <Geography
                        key={geo.rsmKey}
                        geography={geo}
                        fill={getFillColor(code)}
                        stroke={isSelected ? "#818cf8" : "#0a0a1a"}
                        strokeWidth={isSelected ? 1.5 : 0.4}
                        style={{
                          default: { outline: "none", cursor: "pointer" },
                          hover: {
                            fill: isSelected ? "#818cf8" : "#4f46e5",
                            outline: "none",
                            cursor: "pointer",
                          },
                          pressed: { outline: "none" },
                        }}
                        onMouseEnter={(evt: React.MouseEvent) => handleMouseEnter(geo, evt)}
                        onMouseMove={handleMouseMove}
                        onMouseLeave={handleMouseLeave}
                        onClick={() => handleClick(code)}
                      />
                    );
                  })
                }
              </Geographies>
            </ZoomableGroup>
          </ComposableMap>

          <div className="absolute bottom-3 left-3 flex items-center gap-1.5">
            <div
              className="h-2 w-24 rounded-full"
              style={{
                background:
                  "linear-gradient(to right, #1e1b4b, #6366f1)",
              }}
            />
            <span className="text-xs" style={{ color: "#6b7280" }}>
              0 → {maxCount}
            </span>
          </div>

          <div className="absolute bottom-3 right-3 flex flex-col gap-1">
            <button
              className="w-7 h-7 rounded-md border border-white/10 text-sm font-bold flex items-center justify-center transition-colors hover:border-indigo-500/50"
              style={{ background: "rgba(2,2,2,0.8)", color: "#ededed" }}
              onClick={() =>
                setPosition((p) => ({ ...p, zoom: Math.min(p.zoom * 1.5, 8) }))
              }
            >
              +
            </button>
            <button
              className="w-7 h-7 rounded-md border border-white/10 text-sm font-bold flex items-center justify-center transition-colors hover:border-indigo-500/50"
              style={{ background: "rgba(2,2,2,0.8)", color: "#ededed" }}
              onClick={() =>
                setPosition((p) => ({ ...p, zoom: Math.max(p.zoom / 1.5, 0.8) }))
              }
            >
              −
            </button>
            <button
              className="w-7 h-7 rounded-md border border-white/10 text-xs flex items-center justify-center transition-colors hover:border-indigo-500/50"
              style={{ background: "rgba(2,2,2,0.8)", color: "#6b7280" }}
              onClick={() =>
                setPosition({ coordinates: [2.3, 46.8], zoom: 1 })
              }
            >
              ↺
            </button>
          </div>
        </div>
      </div>

      <div
        className="lg:w-64 rounded-xl border border-white/5 p-4 flex flex-col gap-2"
        style={{
          background: "rgba(99,102,241,0.04)",
          backdropFilter: "blur(12px)",
        }}
      >
        <p
          className="text-xs uppercase tracking-widest mb-2 font-semibold"
          style={{ color: "#6366f1" }}
        >
          Top 10 départements
        </p>
        {top10.map((d, i) => {
          const pct = maxCount > 0 ? (d.count / maxCount) * 100 : 0;
          const isSelected = d.dept === selectedDept;
          return (
            <button
              key={d.dept}
              className="w-full text-left rounded-lg px-3 py-2 transition-all hover:bg-white/5"
              style={{
                background: isSelected ? "rgba(99,102,241,0.12)" : "transparent",
                border: isSelected ? "1px solid rgba(99,102,241,0.4)" : "1px solid transparent",
              }}
              onClick={() => handleClick(d.dept)}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium flex items-center gap-1.5" style={{ color: "#ededed" }}>
                  <span
                    className="inline-flex w-4 h-4 rounded-sm items-center justify-center text-[10px] font-bold"
                    style={{ background: "rgba(99,102,241,0.2)", color: "#6366f1" }}
                  >
                    {i + 1}
                  </span>
                  {d.label ?? `Dépt. ${d.dept}`}
                </span>
                <span className="text-xs tabular-nums" style={{ color: "#6366f1" }}>
                  {d.count}
                </span>
              </div>
              <div
                className="h-1 rounded-full overflow-hidden"
                style={{ background: "rgba(99,102,241,0.1)" }}
              >
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${pct}%`,
                    background: "linear-gradient(to right, #4f46e5, #818cf8)",
                  }}
                />
              </div>
            </button>
          );
        })}
        {top10.length === 0 && (
          <p className="text-xs text-center py-4" style={{ color: "#374151" }}>
            Aucune donnée
          </p>
        )}
      </div>
    </div>
  );
}
