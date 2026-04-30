import { useQuery } from "@tanstack/react-query";

interface GraphNode {
  id: string;
  name: string;
  type: string;
  role: string;
  color: string;
  company?: string;
  score?: number | null;
  signals_count?: number;
  signals?: string[];
  is_holding?: boolean;
  age?: number;
  age_signal?: boolean;
  multi_mandats?: boolean;
  sector?: string;
  city?: string;
  siren?: string;
  ca?: string;
  ebitda?: string;
  priority?: string;
}

interface GraphLink {
  source: string;
  target: string;
  label: string;
  value: number;
}

interface GraphData {
  data: {
    nodes: GraphNode[];
    links: GraphLink[];
  };
}

export function useGraph() {
  return useQuery<GraphData>({
    queryKey: ["graph"],
    queryFn: async () => {
      // Bug M rapport QA — pointe sur le datalake unifié (mêmes données que
      // /api/datalake/fiche/{siren}.network) pour cohérence Graph ↔ Fiche.
      const res = await fetch("/api/datalake/graph");
      if (!res.ok) throw new Error(`HTTP error: ${res.status}`);
      return res.json();
    },
    staleTime: 10 * 60 * 1000,
  });
}
