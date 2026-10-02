import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, errorMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type ReportOut = components["schemas"]["ReportOut"];
export type ReportIn = components["schemas"]["ReportIn"];
export type ReportLanguage = NonNullable<ReportIn["language"]>;
export type Paper = NonNullable<ReportIn["paper"]>;

const reportsKey = (personId: string) => ["persons", personId, "reports"] as const;

const working = (report: ReportOut) => report.status === "queued" || report.status === "rendering";

/** A person's reports, newest first; checked every couple of seconds while one is being made. */
export function useReports(personId: string) {
  return useQuery({
    queryKey: reportsKey(personId),
    queryFn: async () => {
      const { data, error } = await api.GET("/api/persons/{person_id}/reports", {
        params: { path: { person_id: personId } },
      });
      if (!data) throw new Error(errorMessage(error, "The reports could not be loaded."));
      return data;
    },
    enabled: personId !== "",
    refetchInterval: (query) => (query.state.data?.some(working) ? 2000 : false),
  });
}

export function useCreateReport(personId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: ReportIn) => {
      const { data, error } = await api.POST("/api/persons/{person_id}/reports", {
        params: { path: { person_id: personId } },
        body,
      });
      if (!data) throw new Error(errorMessage(error, "The report could not be requested."));
      return data;
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: reportsKey(personId) }),
  });
}

export function useDeleteReport(personId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (reportId: string) => {
      const { error, response } = await api.DELETE("/api/reports/{report_id}", {
        params: { path: { report_id: reportId } },
      });
      if (!response.ok) throw new Error(errorMessage(error, "The report could not be deleted."));
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: reportsKey(personId) }),
  });
}
