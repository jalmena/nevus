import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, errorMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type DueItem = components["schemas"]["DueOut"];

export function useDue() {
  return useQuery({
    queryKey: ["due"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/due");
      if (!data) throw new Error(errorMessage(error, "The due list could not be loaded."));
      return data;
    },
  });
}

export function useSnooze(lesionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (days: 7 | 30 | null) => {
      const { data, error } =
        days === null
          ? await api.DELETE("/api/lesions/{lesion_id}/snooze", { params: { path: { lesion_id: lesionId } } })
          : await api.POST("/api/lesions/{lesion_id}/snooze", {
              params: { path: { lesion_id: lesionId } },
              body: { days },
            });
      if (!data) throw new Error(errorMessage(error, "The reminder could not be changed."));
      return data;
    },
    onSuccess: () => void queryClient.invalidateQueries(),
  });
}
