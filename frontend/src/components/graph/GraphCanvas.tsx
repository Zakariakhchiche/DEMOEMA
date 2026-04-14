"use client";

import { useEffect, useRef, useCallback } from "react";
import type { Graph as G6Graph } from "@antv/g6";

interface GraphNode {
  id: string;
  name: string;
  type: string;
  role: string;
  color: string;
  company?: string;
  score?: number;
  signals_count?: number;
  signals?: string[];
  is_holding?: boolean;
}

interface GraphLink {
  source: string;
  target: string;
  label: string;
  value: number;
}

interface GraphCanvasProps {
  nodes: GraphNode[];
  links: GraphLink[];
  onNodeClick?: (node: GraphNode) => void;
  layout: "force" | "dagre" | "radial" | "circular";
  highlightNodeId?: string | null;
  searchTerm?: string;
}

const NODE_COLORS: Record<string, string> = {
  internal: "#6366f1",
  target: "#10b981",
  advisor: "#f59e0b",
  subsidiary: "#8b5cf6",
};

const EDGE_STYLES: Record<string, { stroke: string; lineDash?: number[]; lineWidth?: number }> = {
  Filiale: { stroke: "#8b5cf680", lineDash: [6, 4], lineWidth: 1.5 },
  default: { stroke: "#ffffff15", lineWidth: 1 },
};

export default function GraphCanvas({
  nodes,
  links,
  onNodeClick,
  layout,
  highlightNodeId,
  searchTerm,
}: GraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<G6Graph | null>(null);

  const buildGraphData = useCallback(() => {
    const dimmedIds = new Set<string>();

    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      const matchedIds = new Set(
        nodes
          .filter(
            (n) =>
              n.name.toLowerCase().includes(term) ||
              (n.company || "").toLowerCase().includes(term)
          )
          .map((n) => n.id)
      );
      // Also keep direct neighbors of matched nodes
      const neighborIds = new Set<string>();
      links.forEach((l) => {
        if (matchedIds.has(l.source)) neighborIds.add(l.target);
        if (matchedIds.has(l.target)) neighborIds.add(l.source);
      });

      nodes.forEach((n) => {
        if (!matchedIds.has(n.id) && !neighborIds.has(n.id)) {
          dimmedIds.add(n.id);
        }
      });
    }

    return {
      nodes: nodes.map((n) => {
        const isDimmed = dimmedIds.has(n.id);
        const isHighlighted = highlightNodeId === n.id;
        const isSubsidiary = n.type === "subsidiary";
        const baseSize = isSubsidiary ? 20 : 32;

        return {
          id: n.id,
          data: { ...n },
          style: {
            size: baseSize,
            fill: isDimmed ? n.color + "20" : n.color,
            stroke: isHighlighted ? n.color : n.color + "40",
            lineWidth: isHighlighted ? 3 : n.is_holding ? 2 : 0,
            opacity: isDimmed ? 0.2 : 1,
            labelText: n.name,
            labelFill: isDimmed ? "#ffffff30" : isSubsidiary ? "#ffffff80" : "#ffffffcc",
            labelFontSize: isSubsidiary ? 10 : 12,
            labelFontWeight: (isSubsidiary ? "normal" : "bold") as "normal" | "bold",
            labelOffsetY: baseSize / 2 + 10,
            badges: n.signals_count && n.signals_count > 0
              ? [
                  {
                    text: String(n.signals_count),
                    position: "right-top" as const,
                    fill: "#ef4444",
                    fontSize: 8,
                    fontWeight: "bold" as const,
                    textFill: "#fff",
                    padding: [1, 4, 1, 4] as [number, number, number, number],
                  },
                ]
              : [],
            cursor: "pointer" as const,
          },
        };
      }),
      edges: links.map((l, i) => {
        const edgeStyle = EDGE_STYLES[l.label] || EDGE_STYLES.default;
        const sourceNode = nodes.find((n) => n.id === l.source);
        const targetNode = nodes.find((n) => n.id === l.target);
        const isDimmed =
          dimmedIds.has(l.source) || dimmedIds.has(l.target);

        return {
          id: `edge-${i}`,
          source: l.source,
          target: l.target,
          data: { ...l },
          style: {
            stroke: isDimmed ? "#ffffff08" : edgeStyle.stroke,
            lineWidth: isDimmed ? 0.5 : l.value * (edgeStyle.lineWidth || 1),
            lineDash: edgeStyle.lineDash,
            opacity: isDimmed ? 0.15 : 0.8,
            labelText: l.label !== "Filiale" ? "" : l.label,
            labelFill: "#ffffff40",
            labelFontSize: 9,
            endArrow: l.label === "Filiale",
            endArrowSize: 6,
          },
        };
      }),
    };
  }, [nodes, links, highlightNodeId, searchTerm]);

  const getLayoutConfig = useCallback(() => {
    switch (layout) {
      case "dagre":
        return { type: "dagre" as const, rankdir: "TB", nodesep: 60, ranksep: 80 };
      case "radial":
        return { type: "radial" as const, unitRadius: 120, linkDistance: 150 };
      case "circular":
        return { type: "circular" as const, radius: 250 };
      case "force":
      default:
        return {
          type: "d3-force" as const,
          link: { distance: 120 },
          charge: { strength: -400 },
          collide: { radius: 40 },
          animation: true,
        };
    }
  }, [layout]);

  // Initialize graph
  useEffect(() => {
    if (!containerRef.current || nodes.length === 0) return;

    let graph: G6Graph;

    const initGraph = async () => {
      const { Graph } = await import("@antv/g6");

      if (graphRef.current) {
        graphRef.current.destroy();
      }

      graph = new Graph({
        container: containerRef.current!,
        autoFit: "view",
        padding: [40, 40, 40, 40],
        theme: "dark",
        data: buildGraphData(),
        layout: getLayoutConfig(),
        node: {
          type: "circle",
          style: {
            size: 28,
            fill: "#6366f1",
            labelPlacement: "bottom",
            labelMaxWidth: 100,
          },
          palette: {
            type: "group",
            field: (d: any) => d.data?.type,
            color: ["#6366f1", "#10b981", "#f59e0b", "#8b5cf6"],
          },
        },
        edge: {
          type: "line",
          style: {
            stroke: "#ffffff15",
          },
        },
        behaviors: [
          "drag-canvas",
          "zoom-canvas",
          "drag-element",
          "click-select",
        ],
        plugins: [
          {
            type: "minimap",
            key: "minimap",
            size: [160, 100],
            position: "bottom-left" as any,
          },
          {
            type: "tooltip",
            key: "tooltip",
            getContent: (_: any, items: any[]) => {
              if (!items || items.length === 0) return "";
              const item = items[0];
              const data = item.data || {};
              return `
                <div style="padding:8px 12px;background:#0a0a0a;border:1px solid rgba(255,255,255,0.1);border-radius:12px;font-family:Inter,sans-serif;">
                  <div style="font-weight:900;color:#fff;font-size:13px;margin-bottom:4px;">${data.name || ""}</div>
                  <div style="color:#818cf8;font-size:10px;text-transform:uppercase;letter-spacing:0.1em;font-weight:700;">${data.role || ""}</div>
                  ${data.score ? `<div style="color:#6b7280;font-size:10px;margin-top:4px;">Score: ${data.score}/100</div>` : ""}
                </div>
              `;
            },
          },
        ],
        animation: {
          duration: 500,
        },
      });

      graph.on("node:click", (evt: any) => {
        const nodeData = evt.itemData?.data || evt.target?.data || {};
        if (onNodeClick && nodeData.id) {
          const originalNode = nodes.find((n) => n.id === nodeData.id);
          if (originalNode) onNodeClick(originalNode);
        }
      });

      await graph.render();
      graphRef.current = graph;
    };

    initGraph();

    return () => {
      if (graphRef.current) {
        graphRef.current.destroy();
        graphRef.current = null;
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes.length]);

  // Update data when search/highlight changes
  useEffect(() => {
    if (!graphRef.current || nodes.length === 0) return;
    try {
      graphRef.current.setData(buildGraphData());
      graphRef.current.render();
    } catch {
      // Graph may be transitioning
    }
  }, [searchTerm, highlightNodeId, buildGraphData, nodes.length]);

  // Update layout
  useEffect(() => {
    if (!graphRef.current) return;
    try {
      graphRef.current.setLayout(getLayoutConfig());
      graphRef.current.layout();
    } catch {
      // Layout change may fail during transition
    }
  }, [layout, getLayoutConfig]);

  return (
    <div
      ref={containerRef}
      className="w-full h-full min-h-[300px]"
      style={{ background: "#050505" }}
    />
  );
}
