import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, errorMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type SessionOut = components["schemas"]["BodySessionOut"];
export type ZoneOut = components["schemas"]["SessionZoneOut"];
export type MarkOut = components["schemas"]["SessionMarkOut"];
export type CaptureZone = components["schemas"]["CaptureZoneOut"];
type MarkIn = components["schemas"]["MarkIn"];
type MarkUpdate = components["schemas"]["MarkUpdate"];

const sessionKey = (id: string) => ["sessions", id] as const;

export function useProtocol() {
  return useQuery({
    queryKey: ["sessions", "protocol"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/sessions/protocol");
      if (!data) throw new Error(errorMessage(error, "The protocol could not be loaded."));
      return data;
    },
    staleTime: Infinity,
  });
}

export function usePersonSessions(personId: string) {
  return useQuery({
    queryKey: ["persons", personId, "sessions"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/persons/{person_id}/sessions", {
        params: { path: { person_id: personId } },
      });
      if (!data) throw new Error(errorMessage(error, "The sessions could not be loaded."));
      return data;
    },
    enabled: personId !== "",
  });
}

/** One session; checked again every few seconds while proposals for a new photo are being made. */
export function useBodySession(id: string) {
  return useQuery({
    queryKey: sessionKey(id),
    queryFn: async () => {
      const { data, error } = await api.GET("/api/sessions/{session_id}", {
        params: { path: { session_id: id } },
      });
      if (!data) throw new Error(errorMessage(error, "The session could not be loaded."));
      return data;
    },
    enabled: id !== "",
    refetchInterval: (query) => (query.state.data?.zones.some((zone) => zone.analysing) ? 3000 : false),
  });
}

function useSessionMutation<T>(run: (input: T) => Promise<SessionOut>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: run,
    onSuccess: (session) => {
      queryClient.setQueryData(sessionKey(session.id), session);
      void queryClient.invalidateQueries({ queryKey: ["persons", session.person_id, "sessions"] });
    },
  });
}

export function useStartSession(personId: string) {
  return useSessionMutation(async (notes: string | null) => {
    const { data, error } = await api.POST("/api/persons/{person_id}/sessions", {
      params: { path: { person_id: personId } },
      body: { notes },
    });
    if (!data) throw new Error(errorMessage(error, "The session could not be started."));
    return data;
  });
}

export function useZonePhoto(sessionId: string) {
  return useSessionMutation(async ({ zone, file }: { zone: string; file: File }) => {
    const body = new FormData();
    body.append("file", file, file.name || "zone.jpg");
    body.append("captured_tz", Intl.DateTimeFormat().resolvedOptions().timeZone);
    const response = await fetch(`${window.location.origin}/api/sessions/${sessionId}/zones/${zone}/photo`, {
      method: "POST",
      body,
      credentials: "same-origin",
    });
    const payload: unknown = await response.json().catch(() => null);
    if (!response.ok) throw new Error(errorMessage(payload, "The photo could not be saved."));
    return payload as SessionOut;
  });
}

export function useSkipZone(sessionId: string) {
  return useSessionMutation(async ({ zone, skip }: { zone: string; skip: boolean }) => {
    const path = { params: { path: { session_id: sessionId, zone } } };
    const { data, error } = skip
      ? await api.POST("/api/sessions/{session_id}/zones/{zone}/skip", path)
      : await api.DELETE("/api/sessions/{session_id}/zones/{zone}/skip", path);
    if (!data) throw new Error(errorMessage(error, "The zone could not be changed."));
    return data;
  });
}

export function useFinishSession(sessionId: string) {
  return useSessionMutation(async () => {
    const { data, error } = await api.POST("/api/sessions/{session_id}/finish", {
      params: { path: { session_id: sessionId } },
    });
    if (!data) throw new Error(errorMessage(error, "The session could not be finished."));
    return data;
  });
}

export function useDeleteSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { error, response } = await api.DELETE("/api/sessions/{session_id}", {
        params: { path: { session_id: id } },
      });
      if (!response.ok) throw new Error(errorMessage(error, "The session could not be deleted."));
    },
    onSuccess: () => void queryClient.invalidateQueries(),
  });
}

export function useAddMark(sessionId: string, zone: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: MarkIn) => {
      const { data, error } = await api.POST("/api/sessions/{session_id}/zones/{zone}/marks", {
        params: { path: { session_id: sessionId, zone } },
        body,
      });
      if (!data) throw new Error(errorMessage(error, "The mark could not be saved."));
      return data;
    },
    onSuccess: () => void queryClient.invalidateQueries(),
  });
}

export function useUpdateMark() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, body }: { id: string; body: MarkUpdate }) => {
      const { data, error } = await api.PATCH("/api/session-marks/{mark_id}", {
        params: { path: { mark_id: id } },
        body,
      });
      if (!data) throw new Error(errorMessage(error, "The mark could not be saved."));
      return data;
    },
    onSuccess: () => void queryClient.invalidateQueries(),
  });
}

export function useDeleteMark() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { error, response } = await api.DELETE("/api/session-marks/{mark_id}", {
        params: { path: { mark_id: id } },
      });
      if (!response.ok) throw new Error(errorMessage(error, "The mark could not be removed."));
    },
    onSuccess: () => void queryClient.invalidateQueries(),
  });
}

export function useSightings(lesionId: string) {
  return useQuery({
    queryKey: ["lesions", lesionId, "sightings"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/lesions/{lesion_id}/sightings", {
        params: { path: { lesion_id: lesionId } },
      });
      if (!data) throw new Error(errorMessage(error, "The sessions could not be loaded."));
      return data;
    },
    enabled: lesionId !== "",
  });
}

export function useSessionPairs(sessionId: string, otherId: string) {
  return useQuery({
    queryKey: ["sessions", sessionId, "compare", otherId],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/sessions/{session_id}/compare/{other_id}", {
        params: { path: { session_id: sessionId, other_id: otherId } },
      });
      if (!data) throw new Error(errorMessage(error, "The sessions could not be compared."));
      return data;
    },
    enabled: sessionId !== "" && otherId !== "",
  });
}
