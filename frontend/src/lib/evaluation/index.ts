import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, errorMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type EvaluationPhoto = components["schemas"]["EvaluationPhoto"];
export type Outline = number[][];

export interface Summary {
  analyzer: { name: string; version: string };
  labelled: number;
  outline: { overall: OutlineRow; by_tone: Record<string, OutlineRow> };
  quality: { overall: QualityRow; by_tone: Record<string, QualityRow> };
}
export interface OutlineRow {
  photos: number;
  found: number;
  mean_iou: number | null;
  mean_dice: number | null;
  mean_diameter_error: number | null;
  worst_diameter_error: number | null;
}
export interface QualityRow {
  photos: number;
  agreement: number | null;
  poor_caught: number;
  poor_missed: number;
  good_flagged: number;
  good_clear: number;
}

export function useEvaluationPhotos(only: "all" | "unlabelled" | "labelled") {
  return useQuery({
    queryKey: ["evaluation", "photos", only],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/evaluation/photos", { params: { query: { only } } });
      if (!data) throw new Error(errorMessage(error, "The evaluation photos could not be loaded."));
      return data;
    },
  });
}

export function useEvaluationSummary() {
  return useQuery({
    queryKey: ["evaluation", "summary"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/evaluation/summary");
      if (!data) throw new Error(errorMessage(error, "The summary could not be loaded."));
      return data as unknown as Summary;
    },
  });
}

export function useSaveLabel(imageId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: { outline: Outline | null; quality: "good" | "bad" | null }) => {
      const { data, error } = await api.PUT("/api/evaluation/photos/{image_id}/label", {
        params: { path: { image_id: imageId } },
        body,
      });
      if (!data) throw new Error(errorMessage(error, "The label could not be saved."));
      return data;
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["evaluation"] }),
  });
}

export function useDeleteLabel(imageId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { error, response } = await api.DELETE("/api/evaluation/photos/{image_id}/label", {
        params: { path: { image_id: imageId } },
      });
      if (!response.ok) throw new Error(errorMessage(error, "The label could not be removed."));
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["evaluation"] }),
  });
}
