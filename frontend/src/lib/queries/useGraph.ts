import { useQuery } from "@tanstack/react-query";

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
      const res = await fetch("/api/graph");
      if (!res.ok) throw new Error(`HTTP error: ${res.status}`);
      return res.json();
    },
    staleTime: 10 * 60 * 1000,
  });
}
