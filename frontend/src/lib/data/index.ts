import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, errorMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { useSudo, withSudo } from "@/lib/sudo/SudoProvider";

export type TrashItem = components["schemas"]["TrashItem"];
export type ExportOut = components["schemas"]["ExportOut"];
type Kind = TrashItem["kind"];

export function useTrash() {
  return useQuery({
    queryKey: ["trash"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/trash");
      if (!data) throw new Error(errorMessage(error, "The trash could not be loaded."));
      return data;
    },
  });
}

export function useRestore() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ kind, id }: { kind: Kind; id: string }) => {
      const { error, response } = await api.POST("/api/trash/{kind}/{item_id}/restore", {
        params: { path: { kind, item_id: id } },
      });
      if (!response.ok) throw new Error(errorMessage(error, "It could not be restored."));
    },
    onSuccess: () => void queryClient.invalidateQueries(),
  });
}

export function usePurgeNow() {
  const queryClient = useQueryClient();
  const ask = useSudo();
  return useMutation({
    mutationFn: async ({ kind, id }: { kind: Kind; id: string }) => {
      const { error, response } = await withSudo(ask, () =>
        api.DELETE("/api/trash/{kind}/{item_id}", { params: { path: { kind, item_id: id } } }),
      );
      if (!response.ok) throw new Error(errorMessage(error, "It could not be deleted."));
    },
    onSuccess: () => void queryClient.invalidateQueries(),
  });
}

export function usePurgePerson() {
  const queryClient = useQueryClient();
  const ask = useSudo();
  return useMutation({
    mutationFn: async (personId: string) => {
      const { error, response } = await withSudo(ask, () =>
        api.DELETE("/api/persons/{person_id}/purge", { params: { path: { person_id: personId } } }),
      );
      if (!response.ok) throw new Error(errorMessage(error, "The profile could not be deleted."));
    },
    onSuccess: () => void queryClient.invalidateQueries(),
  });
}

export function useUsage(personId: string) {
  return useQuery({
    queryKey: ["persons", personId, "usage"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/persons/{person_id}/usage", {
        params: { path: { person_id: personId } },
      });
      if (!data) throw new Error(errorMessage(error, "The storage use could not be loaded."));
      return data;
    },
    enabled: personId !== "",
  });
}

export function useExports() {
  return useQuery({
    queryKey: ["exports"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/exports");
      if (!data) throw new Error(errorMessage(error, "The exports could not be loaded."));
      return data;
    },
    refetchInterval: (query) =>
      query.state.data?.some((e) => e.status === "queued" || e.status === "building") ? 3000 : false,
  });
}

export function useRequestExport() {
  const queryClient = useQueryClient();
  const ask = useSudo();
  return useMutation({
    mutationFn: async (body: { person_id: string | null; passphrase: string }) => {
      const { data, error, response } = await withSudo(ask, () => api.POST("/api/exports", { body }));
      if (!response.ok || !data) throw new Error(errorMessage(error, "The export could not be started."));
      return data;
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["exports"] }),
  });
}

export function useRemoveExport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { error, response } = await api.DELETE("/api/exports/{export_id}", {
        params: { path: { export_id: id } },
      });
      if (!response.ok) throw new Error(errorMessage(error, "The export could not be removed."));
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["exports"] }),
  });
}

export function formatBytes(bytes: number, locale: string): string {
  const units = ["B", "kB", "MB", "GB", "TB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1000 && unit < units.length - 1) {
    value /= 1000;
    unit += 1;
  }
  return `${new Intl.NumberFormat(locale, { maximumFractionDigits: unit === 0 ? 0 : 1 }).format(value)} ${units[unit]}`;
}
