import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, errorMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type WebhookOut = components["schemas"]["WebhookOut"];
export type WebhookIn = components["schemas"]["WebhookIn"];
export type Preset = NonNullable<WebhookIn["preset"]>;
export const PRESETS: Preset[] = ["home_assistant", "ntfy", "gotify", "n8n", "generic"];

const webhooksKey = ["admin", "webhooks"] as const;

export function useWebhooks() {
  return useQuery({
    queryKey: webhooksKey,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/admin/webhooks");
      if (!data) throw new Error(errorMessage(error, "The webhooks could not be loaded."));
      return data;
    },
  });
}

export function useCreateWebhook() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: WebhookIn) => {
      const { data, error } = await api.POST("/api/admin/webhooks", { body });
      if (!data) throw new Error(errorMessage(error, "The webhook could not be saved."));
      return data;
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: webhooksKey }),
  });
}

export function useUpdateWebhook() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, enabled }: { id: string; enabled: boolean }) => {
      const { data, error } = await api.PATCH("/api/admin/webhooks/{webhook_id}", {
        params: { path: { webhook_id: id } },
        body: { enabled },
      });
      if (!data) throw new Error(errorMessage(error, "The webhook could not be saved."));
      return data;
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: webhooksKey }),
  });
}

export function useDeleteWebhook() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { error, response } = await api.DELETE("/api/admin/webhooks/{webhook_id}", {
        params: { path: { webhook_id: id } },
      });
      if (!response.ok) throw new Error(errorMessage(error, "The webhook could not be deleted."));
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: webhooksKey }),
  });
}

export function useTestWebhook() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data, error } = await api.POST("/api/admin/webhooks/{webhook_id}/test", {
        params: { path: { webhook_id: id } },
      });
      if (!data) throw new Error(errorMessage(error, "The test could not be sent."));
      return { id, ...data };
    },
    onSettled: () => void queryClient.invalidateQueries({ queryKey: webhooksKey }),
  });
}

const calendarKey = (personId: string) => ["persons", personId, "calendar"] as const;

export function useCalendarFeed(personId: string) {
  return useQuery({
    queryKey: calendarKey(personId),
    queryFn: async () => {
      const { data, error } = await api.GET("/api/persons/{person_id}/calendar", {
        params: { path: { person_id: personId } },
      });
      if (!data) throw new Error(errorMessage(error, "The calendar link could not be loaded."));
      return data;
    },
    enabled: personId !== "",
  });
}

export function useNewCalendarFeed(personId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST("/api/persons/{person_id}/calendar", {
        params: { path: { person_id: personId } },
      });
      if (!data) throw new Error(errorMessage(error, "The calendar link could not be made."));
      return data;
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: calendarKey(personId) }),
  });
}

export function useStopCalendarFeed(personId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { error, response } = await api.DELETE("/api/persons/{person_id}/calendar", {
        params: { path: { person_id: personId } },
      });
      if (!response.ok) throw new Error(errorMessage(error, "The calendar link could not be stopped."));
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: calendarKey(personId) }),
  });
}
