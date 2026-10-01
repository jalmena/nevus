import { useQuery } from "@tanstack/react-query";
import { api, errorMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type Comparison = components["schemas"]["ComparisonOut"];
export type AbstainReason = NonNullable<Comparison["reason"]>;

/** Align the later photo onto the earlier one. The server keeps the result, so asking again is cheap. */
export function useComparison(imageA: string, imageB: string) {
  return useQuery({
    queryKey: ["comparisons", imageA, imageB],
    queryFn: async () => {
      const { data, error } = await api.POST("/api/comparisons", {
        body: { image_a: imageA, image_b: imageB },
      });
      if (!data) throw new Error(errorMessage(error, "The photos could not be compared."));
      return data;
    },
    enabled: imageA !== "" && imageB !== "" && imageA !== imageB,
    staleTime: Infinity,
  });
}

const BAR_STEPS_MM = [0.5, 1, 2, 5, 10, 20, 50];

/** The longest round length whose bar stays under 160 screen pixels at this zoom. */
export function scaleBarMm(mmPerScreenPx: number): number {
  const fitting = BAR_STEPS_MM.filter((mm) => mm / mmPerScreenPx <= 160);
  return fitting.at(-1) ?? BAR_STEPS_MM[0] ?? 1;
}
