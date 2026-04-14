import { useQuery } from "@tanstack/react-query";

interface SignalCatalog {
  data: Array<{
    id: string;
    label: string;
    source: string;
    source_url: string;
    dimension: string;
    points: number;
    severity: string;
    family: string;
    target_id: string;
    target_name: string;
  }>;
  catalog: Array<{
    id: string;
    label: string;
    dimension: string;
    family: string;
    severity: string;
    points: number;
    source: string;
  }>;
}

export function useSignals() {
  return useQuery<SignalCatalog>({
    queryKey: ["signals"],
    queryFn: async () => {
      const res = await fetch("/api/signals");
      if (!res.ok) throw new Error(`HTTP error: ${res.status}`);
      return res.json();
    },
    staleTime: 30 * 1000,
  });
}
