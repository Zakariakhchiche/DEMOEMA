import { useQuery } from "@tanstack/react-query";
import type { Target } from "@/types";

export function useTarget(id: string) {
  return useQuery<Target>({
    queryKey: ["target", id],
    queryFn: async () => {
      const res = await fetch(`/api/targets/${id}`);
      if (!res.ok) throw new Error(`HTTP error: ${res.status}`);
      const json = await res.json();
      return json.data;
    },
    staleTime: 5 * 60 * 1000,
    enabled: !!id,
  });
}
