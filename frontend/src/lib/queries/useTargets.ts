import { useQuery } from "@tanstack/react-query";
import type { TargetsApiResponse } from "@/types";

export function useTargets() {
  return useQuery<TargetsApiResponse>({
    queryKey: ["targets"],
    queryFn: async () => {
      const res = await fetch("/api/targets");
      if (!res.ok) throw new Error(`HTTP error: ${res.status}`);
      return res.json();
    },
    staleTime: 5 * 60 * 1000,
  });
}
