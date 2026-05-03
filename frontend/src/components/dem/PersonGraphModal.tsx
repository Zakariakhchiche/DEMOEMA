"use client";

import { useEffect, useRef, useState } from "react";
import type { Graph as G6Graph } from "@antv/g6";
import { datalakeApi } from "@/lib/api";
import { Icon } from "./Icon";

type GraphData = Awaited<ReturnType<typeof datalakeApi.personGraph>>;

/** Co-mandataire issu de silver.inpi_dirigeants (reverse-lookup sirens_mandats). */
interface CoMandataireDetail {
  nom?: string | null;
  prenom?: string | null;
  date_naissance?: string | null;
  n_shared?: number | null;
}

interface Props {
  nom: string;
  prenom: string;
  fullName?: string;
  onClose: () => void;
  /** Si renseigné, click sur un co-mandataire bascule la modal vers cette personne. */
  onNavigate?: (target: { nom: string; prenom: string; fullName: string }) => void;
  /** Co-mandataires depuis silver INPI (préféré au Neo4j incomplet par md5
   * mismatch — Vincent LAMOUR : Neo4j renvoie 1 co-mandataire vs silver 4+). */
  coMandatairesDetail?: CoMandataireDetail[];
  /** Total mandats du sujet (silver) pour l'étiquette du node self. */
  selfMandatsActifs?: number | null;
}

interface NodeDatum {
  id: string;
  data: {
    type: "self" | "comand" | "company";
    label: string;
    sub?: string;
    is_sanctioned?: boolean;
    has_offshore?: boolean;
    is_lobbyist?: boolean;
    nom?: string;
    prenom?: string;
    n_shared?: number;
  };
}

interface EdgeDatum {
  source: string;
  target: string;
  data?: { label?: string };
}

/** Couleur par état :
 *  - rose = sanctioned
 *  - amber = offshore
 *  - violet = lobbyist
 *  - teal = self
 *  - bleu neutre sinon
 */
function colorForPerson(p: { is_sanctioned?: boolean; has_offshore?: boolean; is_lobbyist?: boolean; type?: string }): string {
  if (p.type === "self") return "#14b8a6"; // teal
  if (p.is_sanctioned) return "#ef4444"; // rose / red
  if (p.has_offshore) return "#f59e0b"; // amber
  if (p.is_lobbyist) return "#a855f7"; // violet
  return "#6366f1"; // indigo neutral
}

export function PersonGraphModal({
  nom, prenom, fullName, onClose, onNavigate,
  coMandatairesDetail, selfMandatsActifs,
}: Props) {
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<G6Graph | null>(null);

  // Source-of-truth Postgres : si coMandatairesDetail fourni & non-vide, on
  // l'utilise (fiche silver). Neo4j reste tenté en arrière-plan pour
  // récupérer les flags compliance (sanctions/offshore/lobby) du sujet.
  const hasPostgresSource = (coMandatairesDetail?.length ?? 0) > 0;

  // Fetch Neo4j — pour les flags compliance + fallback si pas de source PG.
  useEffect(() => {
    setLoading(true);
    setError(null);
    datalakeApi
      .personGraph(nom, prenom, 20)
      .then((d) => setData(d))
      .catch((e) => {
        // Si on a la source Postgres on tolère l'échec Neo4j (graph reste
        // affichable sans flags). Sinon : erreur visible.
        if (!hasPostgresSource) setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => setLoading(false));
  }, [nom, prenom, hasPostgresSource]);

  // Render G6
  useEffect(() => {
    if (!containerRef.current) return;
    // Source : silver Postgres si dispo, sinon Neo4j.
    if (!hasPostgresSource && (!data || !data.person)) return;

    // G6 v5 attend les styles INLINES par node (pas un callback `style` au
    // niveau du `node:` config). On suit le pattern de
    // components/graph/GraphCanvas.tsx qui marche en prod.
    const center = data?.person;
    const centerLabel = (center?.full_name || `${prenom} ${nom}`).trim();
    const centerMandats = selfMandatsActifs ?? center?.n_mandats_actifs ?? null;
    const SIZE_SELF = 56;
    const SIZE_COMAND = 36;

    // Liste des co-mandataires : Postgres prioritaire (silver INPI =
    // ground-truth), sinon Neo4j top_co_mandataires (incomplet par md5
    // mismatch lors du bulk import).
    type RenderedCoMand = {
      key: string;
      label: string;
      nom: string;
      prenom: string;
      n_shared: number;
      is_sanctioned?: boolean;
      has_offshore?: boolean;
      is_lobbyist?: boolean;
    };
    const renderedCo: RenderedCoMand[] = hasPostgresSource
      ? (coMandatairesDetail ?? []).map((co) => {
          const cn = (co.nom ?? "").trim();
          const cp = (co.prenom ?? "").trim();
          const lbl = `${cp} ${cn}`.trim() || cn || cp || "—";
          return {
            key: `${cn}|${cp}|${co.date_naissance ?? ""}`,
            label: lbl,
            nom: cn,
            prenom: cp,
            n_shared: Number(co.n_shared ?? 0),
          };
        })
      : (data?.top_co_mandataires ?? []).map((co) => ({
          key: `${co.nom}|${co.prenom}`,
          label: co.full_name,
          nom: co.nom,
          prenom: co.prenom,
          n_shared: Number(co.n_shared ?? 0),
          is_sanctioned: co.other_sanctioned,
          has_offshore: co.other_offshore,
          is_lobbyist: co.other_lobbyist,
        }));

    // Le layout G6 "radial" positionne automatiquement les nodes : focus
    // au centre + leaves sur cercles concentriques selon distance topo.
    const styledNodes = [
      {
        id: "self",
        data: {
          type: "self" as const,
          label: centerLabel,
          sub: centerMandats ? `${centerMandats} mandats` : undefined,
          nom: center?.nom ?? nom,
          prenom: center?.prenom ?? prenom,
          is_sanctioned: center?.is_sanctioned,
          has_offshore: center?.has_offshore,
          is_lobbyist: center?.is_lobbyist,
        },
        style: {
          size: SIZE_SELF,
          fill: colorForPerson({ type: "self" }),
          stroke: "#5eead4",
          lineWidth: 3,
          labelText: centerLabel,
          labelFill: "rgba(255,255,255,0.95)",
          labelFontSize: 13,
          labelFontWeight: "bold" as const,
          labelOffsetY: SIZE_SELF / 2 + 10,
        },
      },
      ...renderedCo.map((co, i) => ({
        id: `co_${i}_${co.nom}_${co.prenom}`,
        data: {
          type: "comand" as const,
          label: co.label,
          sub: `${co.n_shared} société${co.n_shared > 1 ? "s" : ""}`,
          nom: co.nom,
          prenom: co.prenom,
          is_sanctioned: co.is_sanctioned,
          has_offshore: co.has_offshore,
          is_lobbyist: co.is_lobbyist,
          n_shared: co.n_shared,
        },
        style: {
          size: SIZE_COMAND,
          fill: colorForPerson({
            is_sanctioned: co.is_sanctioned,
            has_offshore: co.has_offshore,
            is_lobbyist: co.is_lobbyist,
          }),
          stroke: "rgba(255,255,255,0.2)",
          lineWidth: 1,
          labelText: co.label,
          labelFill: "rgba(255,255,255,0.85)",
          labelFontSize: 11,
          labelOffsetY: SIZE_COMAND / 2 + 8,
        },
      })),
    ];
    const styledEdges = renderedCo.map((co, i) => ({
      source: "self",
      target: `co_${i}_${co.nom}_${co.prenom}`,
      style: {
        stroke: "rgba(255,255,255,0.22)",
        lineWidth: 1.5,
        labelText: String(co.n_shared),
        labelFill: "rgba(255,255,255,0.55)",
        labelFontSize: 10,
        labelBackground: true,
        labelBackgroundFill: "rgba(0,0,0,0.55)",
        labelBackgroundRadius: 4,
        labelPadding: [2, 4],
      },
    }));

    let graph: G6Graph | null = null;
    let cancelled = false;

    (async () => {
      try {
        const { Graph } = await import("@antv/g6");
        if (cancelled || !containerRef.current) return;
        if (graphRef.current) {
          graphRef.current.destroy();
          graphRef.current = null;
        }
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        graph = new Graph({
          container: containerRef.current,
          autoFit: "view",
          padding: [40, 40, 40, 40],
          theme: "dark",
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          data: { nodes: styledNodes as any, edges: styledEdges as any },
          // Layout radial : `self` au centre, associés en cercle autour.
          // G6 v5 "radial" est conçu pour cette topologie star (1 hub).
          // `unitRadius` = distance entre le focus et le 1er anneau.
          layout: {
            type: "radial",
            unitRadius: 220,
            preventOverlap: true,
            nodeSize: 60,
            focusNode: "self",
            linkDistance: 220,
          },
          node: { type: "circle" },
          edge: { type: "line" },
          behaviors: ["drag-canvas", "zoom-canvas", "drag-element"],
          animation: { duration: 400 },
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
        } as any);

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        graph.on("node:click", ((evt: any) => {
          const dd = (evt?.itemData?.data ?? evt?.target?.data) as NodeDatum["data"] | undefined;
          if (!dd || dd.type !== "comand" || !dd.nom || !dd.prenom) return;
          if (onNavigate) {
            onNavigate({ nom: dd.nom, prenom: dd.prenom, fullName: dd.label });
          }
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
        }) as any);

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        await (graph as any).render();
        graphRef.current = graph;
      } catch (e) {
        console.error("[PersonGraphModal] G6 render failed:", e);
      }
    })();

    return () => {
      cancelled = true;
      if (graphRef.current) {
        graphRef.current.destroy();
        graphRef.current = null;
      }
    };
  }, [data, onNavigate, hasPostgresSource, coMandatairesDetail, selfMandatsActifs, nom, prenom]);

  // Esc close
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <>
      <div
        onClick={onClose}
        style={{
          position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)",
          zIndex: 1100, backdropFilter: "blur(4px)",
        }}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Graphe réseau dirigeant"
        style={{
          position: "fixed",
          top: "5vh", left: "5vw", right: "5vw", bottom: "5vh",
          background: "var(--surface-base, #0a0a0a)",
          border: "1px solid var(--border-subtle, rgba(255,255,255,0.08))",
          borderRadius: 16,
          zIndex: 1101,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        <div style={{
          padding: "16px 24px", borderBottom: "1px solid var(--border-subtle)",
          display: "flex", alignItems: "center", justifyContent: "space-between",
        }}>
          <div>
            <div style={{
              fontSize: 11, color: "var(--text-tertiary)",
              textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 600,
            }}>
              Réseau co-mandataires · {hasPostgresSource ? "INPI silver" : "Neo4j"} (1 hop)
            </div>
            <div style={{
              fontSize: 18, fontWeight: 700, color: "var(--text-primary)",
              marginTop: 4,
            }}>
              {fullName || `${prenom} ${nom}`}
              {(() => {
                const n = hasPostgresSource
                  ? (coMandatairesDetail?.length ?? 0)
                  : (data?.top_co_mandataires.length ?? 0);
                return n > 0 ? (
                  <span style={{
                    marginLeft: 12, fontSize: 13, fontWeight: 500,
                    color: "var(--text-tertiary)",
                  }}>
                    {n} associés
                  </span>
                ) : null;
              })()}
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <Legend />
            <button
              className="dem-btn dem-btn-ghost dem-btn-icon"
              onClick={onClose}
              title="Fermer (Esc)"
            >
              <span style={{ fontSize: 18, lineHeight: 1 }}>×</span>
            </button>
          </div>
        </div>

        <div style={{ flex: 1, position: "relative", overflow: "hidden" }}>
          {loading && !hasPostgresSource && (
            <div style={{
              position: "absolute", inset: 0, display: "grid", placeItems: "center",
              color: "var(--text-tertiary)", fontSize: 14,
            }}>
              Chargement du graphe…
            </div>
          )}
          {error && !hasPostgresSource && (
            <div style={{
              position: "absolute", inset: 0, display: "grid", placeItems: "center",
              color: "var(--accent-rose, #fb7185)", fontSize: 13, padding: 24,
              textAlign: "center",
            }}>
              <div>
                <Icon name="warning" size={16} />
                <div style={{ marginTop: 8 }}>Pas de données graphe pour ce dirigeant.</div>
                <div style={{
                  marginTop: 4, fontSize: 11, color: "var(--text-muted)",
                }}>
                  ({error})
                </div>
              </div>
            </div>
          )}
          {!loading && !error && !hasPostgresSource && data && data.top_co_mandataires.length === 0 && (
            <div style={{
              position: "absolute", inset: 0, display: "grid", placeItems: "center",
              color: "var(--text-tertiary)", fontSize: 13, padding: 24, textAlign: "center",
            }}>
              <div>
                Aucun co-mandataire trouvé dans le graphe (CO_MANDATE relations
                construites pour les dirigeants partageant ≥ 1 société active).
              </div>
            </div>
          )}
          <div ref={containerRef} style={{ width: "100%", height: "100%" }} />
        </div>
      </div>
    </>
  );
}

function Legend() {
  const items: { color: string; label: string }[] = [
    { color: "#14b8a6", label: "Sujet" },
    { color: "#6366f1", label: "Associé" },
    { color: "#ef4444", label: "Sanctionné" },
    { color: "#f59e0b", label: "Offshore" },
    { color: "#a855f7", label: "Lobbyiste" },
  ];
  return (
    <div style={{
      display: "flex", gap: 12, fontSize: 11,
      color: "var(--text-tertiary)",
    }}>
      {items.map((it) => (
        <div key={it.label} style={{ display: "flex", alignItems: "center", gap: 5 }}>
          <span style={{
            width: 10, height: 10, borderRadius: "50%", background: it.color,
            display: "inline-block",
          }} />
          {it.label}
        </div>
      ))}
    </div>
  );
}
