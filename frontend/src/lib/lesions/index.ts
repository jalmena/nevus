import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, errorMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import type { ImageOut, ImageRole } from "@/lib/images";

export type LesionOut = components["schemas"]["LesionOut"];
export type LesionIn = components["schemas"]["LesionIn"];
export type LesionUpdate = components["schemas"]["LesionUpdate"];
export type ObservationOut = components["schemas"]["ObservationOut"];
export type ObservationIn = components["schemas"]["ObservationIn"];
export type ObservationUpdate = components["schemas"]["ObservationUpdate"];
export type Symptom = "itching" | "bleeding" | "pain" | "looks_different";

export const SYMPTOMS: Symptom[] = ["itching", "bleeding", "pain", "looks_different"];
export const INTERVALS = [30, 90, 180, 365] as const;

export const lesionsKey = (personId: string) => ["persons", personId, "lesions"] as const;
export const lesionKey = (lesionId: string) => ["lesions", lesionId] as const;
export const observationsKey = (lesionId: string) => ["lesions", lesionId, "observations"] as const;
export const observationKey = (observationId: string) => ["observations", observationId] as const;

export function useLesions(personId: string) {
  return useQuery({
    queryKey: lesionsKey(personId),
    queryFn: async () => {
      const { data, error } = await api.GET("/api/persons/{person_id}/lesions", {
        params: { path: { person_id: personId } },
      });
      if (!data) throw new Error(errorMessage(error, "The marks could not be loaded."));
      return data;
    },
    enabled: personId !== "",
  });
}

export function useLesion(lesionId: string) {
  return useQuery({
    queryKey: lesionKey(lesionId),
    queryFn: async () => {
      const { data, error } = await api.GET("/api/lesions/{lesion_id}", {
        params: { path: { lesion_id: lesionId } },
      });
      if (!data) throw new Error(errorMessage(error, "This mark could not be loaded."));
      return data;
    },
    enabled: lesionId !== "",
  });
}

export function useCreateLesion(personId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: LesionIn) => {
      const { data, error } = await api.POST("/api/persons/{person_id}/lesions", {
        params: { path: { person_id: personId } },
        body,
      });
      if (!data) throw new Error(errorMessage(error, "The mark could not be created."));
      return data;
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: lesionsKey(personId) }),
  });
}

export function useUpdateLesion(lesionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: LesionUpdate) => {
      const { data, error } = await api.PATCH("/api/lesions/{lesion_id}", {
        params: { path: { lesion_id: lesionId } },
        body,
      });
      if (!data) throw new Error(errorMessage(error, "The change could not be saved."));
      return data;
    },
    onSuccess: (lesion) => {
      queryClient.setQueryData(lesionKey(lesionId), lesion);
      void queryClient.invalidateQueries({ queryKey: lesionsKey(lesion.person_id) });
    },
  });
}

export function useObservations(lesionId: string) {
  return useQuery({
    queryKey: observationsKey(lesionId),
    queryFn: async () => {
      const { data, error } = await api.GET("/api/lesions/{lesion_id}/observations", {
        params: { path: { lesion_id: lesionId } },
      });
      if (!data) throw new Error(errorMessage(error, "The visits could not be loaded."));
      return data;
    },
    enabled: lesionId !== "",
  });
}

export function useObservation(observationId: string) {
  return useQuery({
    queryKey: observationKey(observationId),
    queryFn: async () => {
      const { data, error } = await api.GET("/api/observations/{observation_id}", {
        params: { path: { observation_id: observationId } },
      });
      if (!data) throw new Error(errorMessage(error, "This visit could not be loaded."));
      return data;
    },
    enabled: observationId !== "",
  });
}

/** Everything derived from a lesion changes when a visit does: its list entry, its due date, its thumbnail. */
function invalidateLesion(queryClient: ReturnType<typeof useQueryClient>, lesionId: string) {
  void queryClient.invalidateQueries({ queryKey: observationsKey(lesionId) });
  void queryClient.invalidateQueries({ queryKey: lesionKey(lesionId) });
  void queryClient.invalidateQueries({ queryKey: ["persons"] });
}

export function useCreateObservation(lesionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: ObservationIn) => {
      const { data, error } = await api.POST("/api/lesions/{lesion_id}/observations", {
        params: { path: { lesion_id: lesionId } },
        body,
      });
      if (!data) throw new Error(errorMessage(error, "The visit could not be created."));
      return data;
    },
    onSuccess: () => invalidateLesion(queryClient, lesionId),
  });
}

export function useUpdateObservation(observationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: ObservationUpdate) => {
      const { data, error } = await api.PATCH("/api/observations/{observation_id}", {
        params: { path: { observation_id: observationId } },
        body,
      });
      if (!data) throw new Error(errorMessage(error, "The change could not be saved."));
      return data;
    },
    onSuccess: (observation) => {
      queryClient.setQueryData(observationKey(observationId), observation);
      invalidateLesion(queryClient, observation.lesion_id);
    },
  });
}

export function useDeleteObservation(observationId: string, lesionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { error, response } = await api.DELETE("/api/observations/{observation_id}", {
        params: { path: { observation_id: observationId } },
      });
      if (!response.ok) throw new Error(errorMessage(error, "The visit could not be deleted."));
    },
    onSuccess: () => invalidateLesion(queryClient, lesionId),
  });
}

export function useUploadObservationImage(observationId: string, lesionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ file, role }: { file: File; role: ImageRole }) => {
      const body = new FormData();
      body.append("file", file, file.name);
      body.append("role", role);
      body.append("modality", "camera");
      body.append("captured_tz", Intl.DateTimeFormat().resolvedOptions().timeZone);
      const response = await fetch(`${window.location.origin}/api/observations/${observationId}/images`, {
        method: "POST",
        body,
        credentials: "same-origin",
      });
      const payload: unknown = await response.json().catch(() => null);
      if (!response.ok) throw new Error(errorMessage(payload, "The photo could not be uploaded."));
      return payload as ImageOut;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: observationKey(observationId) });
      invalidateLesion(queryClient, lesionId);
    },
  });
}

/** Days until (negative: since) a calendar date, in the viewer's local time. */
export function daysUntil(isoDate: string): number {
  const [y, m, d] = isoDate.split("-").map(Number);
  const target = new Date(y ?? 0, (m ?? 1) - 1, d ?? 1);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((target.getTime() - today.getTime()) / 86_400_000);
}
