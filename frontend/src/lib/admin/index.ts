import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, errorMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type EmailSettings = components["schemas"]["EmailSettingsOut"];
export type EmailSettingsIn = components["schemas"]["EmailSettingsIn"];

export function useEmailSettings(enabled: boolean) {
  return useQuery({
    queryKey: ["admin", "email"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/admin/email");
      if (!data) throw new Error(errorMessage(error, "The email settings could not be loaded."));
      return data;
    },
    enabled,
  });
}

export function useSaveEmailSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: EmailSettingsIn) => {
      const { data, error } = await api.PUT("/api/admin/email", { body });
      if (!data) throw new Error(errorMessage(error, "The email settings could not be saved."));
      return data;
    },
    onSuccess: (data) => queryClient.setQueryData(["admin", "email"], data),
  });
}

export function useTestEmail() {
  return useMutation({
    mutationFn: async (to: string) => {
      const { error, response } = await api.POST("/api/admin/email/test", { body: { to } });
      if (!response.ok) throw new Error(errorMessage(error, "The test message could not be sent."));
    },
  });
}

export function useInstanceSettings(enabled: boolean) {
  return useQuery({
    queryKey: ["admin", "instance"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/admin/instance");
      if (!data) throw new Error(errorMessage(error, "The instance settings could not be loaded."));
      return data;
    },
    enabled,
  });
}

export function useSaveInstanceSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: components["schemas"]["InstanceOut"]) => {
      const { data, error } = await api.PUT("/api/admin/instance", { body });
      if (!data) throw new Error(errorMessage(error, "The instance settings could not be saved."));
      return data;
    },
    onSuccess: (data) => queryClient.setQueryData(["admin", "instance"], data),
  });
}
