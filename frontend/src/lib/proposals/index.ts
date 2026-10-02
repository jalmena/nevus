import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, errorMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type ProposalOut = components["schemas"]["ProposalOut"];

const proposalsKey = (imageId: string) => ["images", imageId, "proposals"] as const;

async function fetchProposals(imageId: string): Promise<ProposalOut[]> {
  const { data, error } = await api.GET("/api/images/{image_id}/proposals", {
    params: { path: { image_id: imageId } },
  });
  if (!data) throw new Error(errorMessage(error, "The proposals could not be loaded."));
  return data;
}

/** Experimental proposals for one photo (empty unless the person turned the experimental analysis on). */
export function useProposals(imageId: string) {
  return useQuery({
    queryKey: proposalsKey(imageId),
    queryFn: () => fetchProposals(imageId),
    enabled: imageId !== "",
  });
}

/** The proposals of every photo of a visit; checked again a few times while they are being made. */
export function useVisitProposals(imageIds: string[], waiting: boolean) {
  return useQueries({
    queries: imageIds.map((imageId) => ({
      queryKey: proposalsKey(imageId),
      queryFn: () => fetchProposals(imageId),
      refetchInterval: waiting ? 3000 : (false as const),
    })),
  });
}

export function useDecideProposal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, decision }: { id: string; decision: "confirm" | "reject" }) => {
      if (decision === "confirm") {
        const { data, error } = await api.POST("/api/proposals/{proposal_id}/confirm", {
          params: { path: { proposal_id: id } },
          body: {},
        });
        if (!data) throw new Error(errorMessage(error, "The proposal could not be used."));
        return;
      }
      const { data, error } = await api.POST("/api/proposals/{proposal_id}/reject", {
        params: { path: { proposal_id: id } },
      });
      if (!data) throw new Error(errorMessage(error, "The proposal could not be rejected."));
    },
    onSuccess: () => void queryClient.invalidateQueries(),
  });
}

export function confidenceWord(confidence: number | null | undefined): "high" | "medium" | "low" {
  if (confidence === null || confidence === undefined) return "low";
  if (confidence >= 0.75) return "high";
  return confidence >= 0.5 ? "medium" : "low";
}
