import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

interface PipelineCard {
  id: string;
  name: string;
  sector: string;
  ebitda: string;
  priority: string;
  score: number;
  window?: string;
  region?: string;
  tags?: string[];
}

interface PipelineStage {
  id: string;
  title: string;
  color: string;
  cards: PipelineCard[];
}

interface PipelineData {
  data: PipelineStage[];
}

export function usePipeline() {
  return useQuery<PipelineData>({
    queryKey: ["pipeline"],
    queryFn: async () => {
      const res = await fetch("/api/pipeline");
      if (!res.ok) throw new Error(`HTTP error: ${res.status}`);
      return res.json();
    },
    staleTime: 2 * 60 * 1000,
  });
}

export function useMoveCard() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ cardId, fromStage, toStage, newIndex }: { cardId: string; fromStage: string; toStage: string; newIndex: number }) => {
      const res = await fetch("/api/pipeline/move", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ card_id: cardId, from_stage: fromStage, to_stage: toStage, new_index: newIndex }),
      });
      if (!res.ok) throw new Error(`HTTP error: ${res.status}`);
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pipeline"] });
    },
  });
}
